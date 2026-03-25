import os
import re
import imaplib
import email
import logging
import asyncio
from datetime import datetime
from email.policy import default

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session
from backend.models import Supplier

logger = logging.getLogger("bidroute.bounce_handler")

IMAP_HOST = os.getenv("IMAP_HOST", "imap.beget.com")
# Use 993 for SSL IMAP
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("SMTP_USER", "")
IMAP_PASS = os.getenv("SMTP_PASS", "")

def extract_bounced_email(msg: email.message.EmailMessage) -> str | None:
    """Attempt to extract the bouncing email address from a multipart DSN message."""
    # Look for common headers
    # 1. X-Failed-Recipients
    if "X-Failed-Recipients" in msg:
        return msg["X-Failed-Recipients"]

    # 2. Parse delivery-status parts
    bounced_email = None
    for part in msg.walk():
        if part.get_content_type() == 'message/delivery-status':
            payload = part.get_payload()
            if isinstance(payload, list):
                for subpart in payload:
                    for k, v in subpart.items():
                        if k.lower() == 'final-recipient':
                            # Format usually: rfc822; user@domain.com
                            if ';' in v:
                                bounced_email = v.split(';', 1)[1].strip()
                            else:
                                bounced_email = v.strip()
                            return bounced_email
            else:
                lines = str(payload).splitlines()
                for line in lines:
                    if line.lower().startswith('final-recipient:'):
                        parts = line.split(';', 1)
                        if len(parts) > 1:
                            return parts[1].strip()

    # 3. Text fallback
    # Some basic text matching if it's not a standard DSN
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            text = part.get_payload(decode=True).decode(errors='ignore')
            # Look for lines like:
            # <user@domain.com>: host ... said: 550 User unknown
            match = re.search(r'<(.*?)>:\s*host .*? said:\s*550', text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            # Or "Delivery to the following recipient failed permanently:"
            if "failed permanently" in text.lower() or "address rejected" in text.lower():
                emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
                if emails:
                    # heuristic: the first email found is usually the target, 
                    # but we must exclude our own sending address
                    filtered = [e for e in emails if e.lower() != IMAP_USER.lower()]
                    if filtered:
                        return filtered[0]
    return None

async def process_hard_bounce(session: AsyncSession, bounced_email: str):
    """Mark supplier as inactive due to a hard bounce."""
    bounced_email = bounced_email.lower().strip()
    result = await session.execute(
        select(Supplier)
        .where(Supplier.email == bounced_email)
    )
    supplier = result.scalar_one_or_none()

    if supplier:
        if supplier.active:
            supplier.active = False
            supplier.archived_at = datetime.utcnow()
            supplier.description = f"{(supplier.description or '')}\n[AUTO] Archived due to HARD BOUNCE (SMTP 550) on {datetime.utcnow().strftime('%Y-%m-%d')}."
            await session.commit()
            logger.warning(f"BLOCKED SUPPLIER: {bounced_email} (Hard Bounce received)")
        else:
            logger.info(f"Bounce for {bounced_email} ignored - supplier already inactive.")
    else:
        logger.info(f"Bounce for {bounced_email} ignored - not found in database.")

async def run_bounce_check():
    """Connect to IMAP, read unread bounce messages, parse, and process."""
    if not IMAP_USER or not IMAP_PASS:
        logger.warning("Bounce handler skipped: IMAP credentials missing")
        return

    logger.info("Running bounce handler check...")
    try:
        # Run blocking IMAP operations in a thread
        def _imap_operations():
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(IMAP_USER, IMAP_PASS)
            mail.select('inbox')
            
            # Search for unread messages that are likely bounces
            # Often from MAILER-DAEMON or Postmaster
            status, messages = mail.search(None, '(UNSEEN)')
            if status != 'OK' or not messages[0]:
                mail.close()
                mail.logout()
                return []
            
            bounced_emails = []
            msg_ids = messages[0].split()
            
            for msg_id in msg_ids:
                res, msg_data = mail.fetch(msg_id, '(RFC822)')
                if res != 'OK':
                    continue
                    
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1], policy=default)
                        
                        # Verify if it's a bounce/return message
                        sender = msg.get("From", "").lower()
                        subject = msg.get("Subject", "").lower()
                        is_bounce = False
                        if "mailer-daemon" in sender or "postmaster" in sender:
                            is_bounce = True
                        elif "undelivered" in subject or "failure notice" in subject or "returned" in subject:
                            is_bounce = True
                            
                        if is_bounce:
                            bounced_addr = extract_bounced_email(msg)
                            if bounced_addr:
                                bounced_emails.append(bounced_addr)
                            else:
                                logger.info(f"Could not extract bounce addr from msg {msg_id}")
                                
                        # We mark as seen implicitly by reading it. 
                        # Alternatively, store in flag. mail.store(msg_id, '+FLAGS', '\\Seen')
            
            mail.close()
            mail.logout()
            return bounced_emails

        loop = asyncio.get_running_loop()
        bounced_emails = await loop.run_in_executor(None, _imap_operations)
        
        if bounced_emails:
            logger.info(f"Found {len(bounced_emails)} newly bounced emails.")
            for email_addr in bounced_emails:
                try:
                    async with async_session() as session:
                        await process_hard_bounce(session, email_addr)
                except Exception as e:
                    logger.error(f"Error processing bounce for {email_addr}: {e}")
        else:
            logger.info("No unread bounces found.")

    except Exception as e:
        logger.error(f"IMAP connection or parsing error: {e}")

async def bounce_loop():
    """Background loop to periodically check for bounced emails."""
    logger.info("Bounce handler loop started")
    while True:
        try:
            await run_bounce_check()
        except Exception as e:
            logger.error(f"Bounce loop error: {e}")
        
        # Check every 10 minutes
        await asyncio.sleep(600)
