"""
Telegram Multi-Account Mailing Service.
- 1 PARSER account: fetches channel members (needs admin rights)
- N SENDER accounts: send messages with round-robin distribution
"""
import os
import glob
import asyncio
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

from telethon import TelegramClient, errors
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent, InputPeerUser

from sqlalchemy import select, func
from backend.database import async_session
from backend.models import TgCampaign, TgCampaignRecipient, TgCampaignStatus

logger = logging.getLogger("bidroute.telegram")

# ── Hard safety limits ──
TG_MIN_DELAY = 35
TG_DAILY_LIMIT_PER_ACCOUNT = 15

# ── Multi-account globals ──
_parser_client: TelegramClient | None = None  # Only for fetching members
_sender_clients: list[dict] = []               # [{client, session_name, user_info, connected}]
_running_tasks: dict[int, asyncio.Task] = {}

PARSER_SESSION = "223732449_telethon"  # Switched from 223732451 (corrupted AuthKey)


def _parse_proxy() -> dict | None:
    """Parse TG_PROXY env var. Formats:
    socks5://user:pass@host:port
    socks5://host:port
    http://host:port
    """
    proxy_url = os.getenv("TG_PROXY", "").strip()
    if not proxy_url:
        return None

    try:
        parsed = urlparse(proxy_url)
        scheme = (parsed.scheme or "socks5").lower()

        import socks
        proxy_type = socks.SOCKS5 if "socks5" in scheme else (
            socks.SOCKS4 if "socks4" in scheme else socks.HTTP
        )

        proxy = {
            "proxy_type": proxy_type,
            "addr": parsed.hostname,
            "port": parsed.port or 1080,
        }
        if parsed.username:
            proxy["username"] = parsed.username
        if parsed.password:
            proxy["password"] = parsed.password

        logger.info(f"Proxy configured: {scheme}://{parsed.hostname}:{parsed.port}")
        return proxy
    except ImportError:
        logger.error("PySocks not installed! Run: pip install pysocks")
        return None
    except Exception as e:
        logger.error(f"Failed to parse proxy '{proxy_url}': {e}")
        return None


# ═══════════════════════════════════════════════════
#  Session Discovery
# ═══════════════════════════════════════════════════

def _get_base_dir() -> str:
    """Project root directory."""
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _discover_sessions() -> tuple[str, list[str]]:
    """Find all session files. Return (parser_path, [sender_paths])."""
    base = _get_base_dir()
    all_sessions = sorted(glob.glob(os.path.join(base, "*_telethon.session")))

    parser_path = None
    sender_paths = []

    for s in all_sessions:
        name = os.path.splitext(os.path.basename(s))[0]  # e.g. "222597080_telethon"
        if name == PARSER_SESSION:
            parser_path = os.path.join(base, name)
        else:
            sender_paths.append(os.path.join(base, name))

    if not parser_path:
        parser_path = os.path.join(base, PARSER_SESSION)

    return parser_path, sender_paths


# ═══════════════════════════════════════════════════
#  Client Management
# ═══════════════════════════════════════════════════

async def _connect_client(session_path: str) -> tuple[TelegramClient, dict | None]:
    """Connect a single Telethon client. Returns (client, user_info or None)."""
    api_id = int(os.getenv("TG_API_ID", "2040"))
    api_hash = os.getenv("TG_API_HASH", "b18441a1ff607e10a989891a5462e627")

    proxy = _parse_proxy()
    client = TelegramClient(session_path, api_id, api_hash, proxy=proxy)
    await client.connect()

    if not await client.is_user_authorized():
        logger.warning(f"Session NOT authorized: {session_path}")
        return client, None

    me = await client.get_me()
    user_info = {
        "id": me.id,
        "first_name": me.first_name or "",
        "last_name": me.last_name or "",
        "username": me.username or "",
        "phone": me.phone or "",
    }
    return client, user_info


async def connect_all() -> None:
    """Connect parser + all sender accounts on startup."""
    global _parser_client, _sender_clients

    parser_path, sender_paths = _discover_sessions()

    # Connect parser
    try:
        client, info = await _connect_client(parser_path)
        _parser_client = client
        if info:
            logger.info(f"✅ PARSER connected: {info['first_name']} (ID: {info['id']}, phone: {info['phone']})")
        else:
            logger.warning(f"⚠️ PARSER session not authorized: {parser_path}")
    except Exception as e:
        logger.error(f"❌ PARSER connection failed: {e}")

    # Connect senders
    _sender_clients = []
    for sp in sender_paths:
        try:
            client, info = await _connect_client(sp)
            session_name = os.path.basename(sp)
            entry = {
                "client": client,
                "session_name": session_name,
                "user_info": info,
                "connected": info is not None,
            }
            _sender_clients.append(entry)
            if info:
                logger.info(f"✅ SENDER connected: {info['first_name']} (ID: {info['id']}, phone: {info['phone']})")
            else:
                logger.warning(f"⚠️ SENDER not authorized: {sp}")
        except Exception as e:
            logger.error(f"❌ SENDER connection failed ({sp}): {e}")

    total = len(_sender_clients)
    active = sum(1 for s in _sender_clients if s["connected"])
    logger.info(f"Multi-account: {active}/{total} senders active, parser={'OK' if _parser_client else 'FAIL'}")


async def disconnect_all() -> None:
    """Disconnect all clients."""
    global _parser_client, _sender_clients

    if _parser_client and _parser_client.is_connected():
        await _parser_client.disconnect()
    _parser_client = None

    for s in _sender_clients:
        try:
            if s["client"] and s["client"].is_connected():
                await s["client"].disconnect()
        except Exception:
            pass
    _sender_clients = []
    logger.info("All Telegram clients disconnected")


async def rename_account(session_name: str, first_name: str, last_name: str = "") -> dict:
    """Rename a Telegram account's profile (first/last name)."""
    from telethon.tl.functions.account import UpdateProfileRequest

    # Find the right client
    client = None
    entry = None

    if session_name == PARSER_SESSION and _parser_client and _parser_client.is_connected():
        client = _parser_client
    else:
        for s in _sender_clients:
            if s["session_name"] == session_name and s["connected"]:
                client = s["client"]
                entry = s
                break

    if not client:
        raise RuntimeError(f"Аккаунт '{session_name}' не подключен")

    await client(UpdateProfileRequest(first_name=first_name, last_name=last_name))

    # Refresh cached info
    me = await client.get_me()
    new_info = {
        "id": me.id,
        "first_name": me.first_name or "",
        "last_name": me.last_name or "",
        "username": me.username or "",
        "phone": me.phone or "",
    }
    if entry:
        entry["user_info"] = new_info

    logger.info(f"Account {session_name} renamed to: {first_name} {last_name}")
    return {"message": f"Имя изменено: {first_name} {last_name}", "user_info": new_info}


# Legacy compat
async def connect_tg():
    await connect_all()
    return _parser_client

async def disconnect_tg():
    await disconnect_all()


async def get_tg_client() -> TelegramClient | None:
    """Get parser client (for fetching members)."""
    if _parser_client and _parser_client.is_connected():
        return _parser_client
    return None


def _get_active_senders() -> list[dict]:
    """Get list of connected sender clients."""
    return [s for s in _sender_clients if s["connected"] and s["client"].is_connected()]


# ═══════════════════════════════════════════════════
#  Status
# ═══════════════════════════════════════════════════

async def get_tg_status() -> dict:
    """Return status of parser + all senders."""
    parser_info = None
    if _parser_client and _parser_client.is_connected():
        try:
            me = await _parser_client.get_me()
            parser_info = {
                "id": me.id,
                "first_name": me.first_name or "",
                "last_name": me.last_name or "",
                "username": me.username or "",
                "phone": me.phone or "",
            }
        except Exception:
            pass

    senders = []
    for s in _sender_clients:
        info = s.get("user_info")
        senders.append({
            "session_name": s["session_name"],
            "connected": s["connected"],
            "user_info": info,
        })

    active_senders = sum(1 for s in senders if s["connected"])

    return {
        "connected": parser_info is not None,
        "user": parser_info,  # backward compat
        "parser": {
            "connected": parser_info is not None,
            "user": parser_info,
            "role": "parser",
            "session_name": PARSER_SESSION,
        },
        "senders": senders,
        "total_senders": len(senders),
        "active_senders": active_senders,
        "daily_capacity": active_senders * TG_DAILY_LIMIT_PER_ACCOUNT,
    }


# ═══════════════════════════════════════════════════
#  Channel Members (uses PARSER only)
# ═══════════════════════════════════════════════════

async def fetch_channel_members(channel_identifier: str) -> list[dict]:
    """Fetch members using the PARSER account (must be admin)."""
    client = await get_tg_client()
    if not client:
        raise RuntimeError("Парсер-аккаунт не подключен")

    if channel_identifier.lstrip("-").isdigit():
        entity = int(channel_identifier)
    else:
        entity = channel_identifier

    try:
        channel = await client.get_entity(entity)
    except Exception as e:
        raise RuntimeError(f"Не удалось найти канал '{channel_identifier}': {e}")

    members = []
    seen_ids = set()
    offset = 0
    limit = 200

    # METHOD 1: Try get_participants (works if we are admin, or in some public groups)
    try:
        while True:
            participants = await client(GetParticipantsRequest(
                channel=channel,
                filter=ChannelParticipantsRecent(),
                offset=offset,
                limit=limit,
                hash=0,
            ))
            if not participants.users:
                break

            for user in participants.users:
                if getattr(user, 'bot', False) or user.id in seen_ids:
                    continue
                seen_ids.add(user.id)
                members.append({
                    "tg_user_id": user.id,
                    "access_hash": str(user.access_hash) if getattr(user, 'access_hash', None) else "",
                    "username": getattr(user, 'username', '') or "",
                    "first_name": getattr(user, 'first_name', '') or "",
                })

            offset += len(participants.users)
            if offset >= participants.count:
                break

            await asyncio.sleep(1)
        logger.info(f"Fetched {len(members)} members via GetParticipantsRequest")
    except errors.ChatAdminRequiredError:
        logger.warning(f"Admin required for iter_participants in '{channel_identifier}'. Falling back to reading messages.")
    except Exception as e:
        logger.warning(f"GetParticipantsRequest Failed: {e}")

    # METHOD 2: Parse messages for authors and other traces (fallback if members hidden or not admin)
    if len(members) < 5000:
        logger.info(f"Only {len(members)} participants found directly. Scraping deep message history to find ALL active users...")
        try:
            msg_count = 0
            # Read up to 100,000 messages for maximum coverage
            async for msg in client.iter_messages(channel, limit=100000):
                msg_count += 1
                
                # 1. Author of the message
                if msg.sender_id and msg.sender_id not in seen_ids:
                    sender = msg.sender
                    if sender and getattr(sender, 'bot', False) is False and type(sender).__name__ == 'User':
                        seen_ids.add(sender.id)
                        members.append({
                            "tg_user_id": sender.id,
                            "access_hash": str(sender.access_hash) if getattr(sender, 'access_hash', None) else "",
                            "username": getattr(sender, 'username', '') or "",
                            "first_name": getattr(sender, 'first_name', '') or "",
                        })

                # 2. Author of a forwarded message (Forward origin)
                if getattr(msg, 'fwd_from', None) and getattr(msg.fwd_from, 'from_id', None):
                    fwd = msg.fwd_from
                    if hasattr(fwd.from_id, 'user_id'):
                        f_id = fwd.from_id.user_id
                        if f_id not in seen_ids:
                            # We can't immediately get full User object from just ID without an API call if not cached,
                            # but we can try to fetch the entity if telethon cached it locally
                            try:
                                f_user = await client.get_entity(f_id)
                                if f_user and getattr(f_user, 'bot', False) is False and type(f_user).__name__ == 'User':
                                    seen_ids.add(f_user.id)
                                    members.append({
                                        "tg_user_id": f_user.id,
                                        "access_hash": str(f_user.access_hash) if getattr(f_user, 'access_hash', None) else "",
                                        "username": getattr(f_user, 'username', '') or "",
                                        "first_name": getattr(f_user, 'first_name', '') or "",
                                    })
                            except:
                                pass # Ignore if entity not cached

                # 3. System actions: Users who joined the chat but never wrote anything
                if getattr(msg, 'action', None):
                    from telethon.tl.types import MessageActionChatAddUser, MessageActionChatJoinedByLink
                    action = msg.action
                    users_to_check = []
                    
                    if type(action) == MessageActionChatAddUser:
                        users_to_check.extend(action.users)
                    elif type(action) == MessageActionChatJoinedByLink:
                        if msg.sender_id:
                            users_to_check.append(msg.sender_id)
                            
                    for u_id in users_to_check:
                        if u_id not in seen_ids:
                            try:
                                a_user = await client.get_entity(u_id)
                                if a_user and getattr(a_user, 'bot', False) is False and type(a_user).__name__ == 'User':
                                    seen_ids.add(a_user.id)
                                    members.append({
                                        "tg_user_id": a_user.id,
                                        "access_hash": str(a_user.access_hash) if getattr(a_user, 'access_hash', None) else "",
                                        "username": getattr(a_user, 'username', '') or "",
                                        "first_name": getattr(a_user, 'first_name', '') or "",
                                    })
                            except:
                                pass

                # 4. Users who left recent reactions
                if getattr(msg, 'reactions', None) and getattr(msg.reactions, 'recent_reactions', None):
                    for reaction in msg.reactions.recent_reactions:
                        if getattr(reaction.peer_id, 'user_id', None):
                            r_id = reaction.peer_id.user_id
                            if r_id not in seen_ids:
                                try:
                                    r_user = await client.get_entity(r_id)
                                    if r_user and getattr(r_user, 'bot', False) is False and type(r_user).__name__ == 'User':
                                        seen_ids.add(r_user.id)
                                        members.append({
                                            "tg_user_id": r_user.id,
                                            "access_hash": str(r_user.access_hash) if getattr(r_user, 'access_hash', None) else "",
                                            "username": getattr(r_user, 'username', '') or "",
                                            "first_name": getattr(r_user, 'first_name', '') or "",
                                        })
                                except:
                                    pass

            # 5. Parse @username mentions from message text
                if getattr(msg, 'message', None):
                    import re
                    mentioned = re.findall(r'@([A-Za-z0-9_]{5,32})', msg.message)
                    for uname in mentioned:
                        uname_lower = uname.lower()
                        # Skip if we already have this username
                        if any(m.get('username', '').lower() == uname_lower for m in members):
                            continue
                        try:
                            m_user = await client.get_entity(uname)
                            if m_user and getattr(m_user, 'bot', False) is False and type(m_user).__name__ == 'User':
                                if m_user.id not in seen_ids:
                                    seen_ids.add(m_user.id)
                                    members.append({
                                        "tg_user_id": m_user.id,
                                        "access_hash": str(m_user.access_hash) if getattr(m_user, 'access_hash', None) else "",
                                        "username": getattr(m_user, 'username', '') or "",
                                        "first_name": getattr(m_user, 'first_name', '') or "",
                                    })
                        except:
                            pass

            logger.info(f"Parsed {msg_count} deep messages, found {len(members)} unique valid users total.")
        except Exception as e:
            logger.warning(f"Error while deep scraping messages to find members: {e}")

    # METHOD 3: Alphabet search via ChannelParticipantsSearch (finds silent members by name)
    from telethon.tl.types import ChannelParticipantsSearch
    alphabet = list('абвгдежзиклмнопрстуфхцчшщэюя') + list('abcdefghijklmnopqrstuvwxyz')
    logger.info(f"Running alphabet search across {len(alphabet)} letters to find silent members...")
    alpha_found = 0
    for letter in alphabet:
        try:
            participants = await client(GetParticipantsRequest(
                channel=channel,
                filter=ChannelParticipantsSearch(letter),
                offset=0,
                limit=200,
                hash=0,
            ))
            for user in (participants.users or []):
                if getattr(user, 'bot', False) or user.id in seen_ids:
                    continue
                if type(user).__name__ != 'User':
                    continue
                seen_ids.add(user.id)
                members.append({
                    "tg_user_id": user.id,
                    "access_hash": str(user.access_hash) if getattr(user, 'access_hash', None) else "",
                    "username": getattr(user, 'username', '') or "",
                    "first_name": getattr(user, 'first_name', '') or "",
                })
                alpha_found += 1
            await asyncio.sleep(0.5)
        except errors.ChatAdminRequiredError:
            logger.warning("Alphabet search requires admin. Skipping.")
            break
        except Exception as e:
            logger.warning(f"Alphabet search letter '{letter}': {e}")
            continue
    logger.info(f"Alphabet search found {alpha_found} additional silent members.")

    if not members:
        raise RuntimeError(f"Не удалось собрать участников из '{channel_identifier}' (участники скрыты, нет сообщений, или парсер не админ)")

    logger.info(f"Total fetched {len(members)} members from '{channel_identifier}'")
    return members


# ═══════════════════════════════════════════════════
#  Campaign Sending (uses SENDER pool)
# ═══════════════════════════════════════════════════

async def _get_sender_daily_sent(sender_id: int) -> int:
    """Count how many messages this sender account sent in last 24h."""
    since = datetime.utcnow() - timedelta(hours=24)
    async with async_session() as db:
        count = (await db.execute(
            select(func.count(TgCampaignRecipient.id)).where(
                TgCampaignRecipient.status == "sent",
                TgCampaignRecipient.sent_at >= since,
                TgCampaignRecipient.sent_by_account == str(sender_id),
            )
        )).scalar() or 0
    return count


async def run_tg_campaign(campaign_id: int):
    """Multi-account campaign sending: distribute across sender pool."""
    delay = int(os.getenv("TG_SEND_DELAY", "60"))

    async with async_session() as db:
        campaign = await db.get(TgCampaign, campaign_id)
        if not campaign:
            logger.error(f"TG Campaign {campaign_id} not found")
            return
        if campaign.delay_seconds:
            delay = max(TG_MIN_DELAY, campaign.delay_seconds)

    active_senders = _get_active_senders()

    # Include PARSER in the sender pool (it's admin, knows all channel members)
    parser = await get_tg_client()
    if parser and parser.is_connected():
        try:
            parser_me = await parser.get_me()
            parser_entry = {
                "client": parser,
                "session_name": PARSER_SESSION,
                "connected": True,
                "user_info": {
                    "id": parser_me.id,
                    "first_name": parser_me.first_name or "",
                    "username": parser_me.username or "",
                },
            }
            active_senders = [parser_entry] + active_senders
            logger.info(f"Parser {PARSER_SESSION} added to sender pool")
        except Exception as e:
            logger.warning(f"Could not add parser to sender pool: {e}")

    # Auto-add senders to source channel as admins
    async with async_session() as db:
        campaign = await db.get(TgCampaign, campaign_id)
        source_channel = campaign.source_channel if campaign else ""

    if parser and parser.is_connected() and source_channel:
        from telethon.tl.functions.channels import InviteToChannelRequest, EditAdminRequest
        from telethon.tl.functions.messages import AddChatUserRequest
        from telethon.tl.types import ChatAdminRights
        try:
            if source_channel.lstrip("-").isdigit():
                channel = await parser.get_entity(int(source_channel))
            else:
                channel = await parser.get_entity(source_channel)

            admin_rights = ChatAdminRights(
                post_messages=False, add_admins=False, invite_users=False,
                change_info=False, ban_users=False, delete_messages=False,
                pin_messages=False, edit_messages=False,
            )

            # Discover senders: each sender sends "hi" to parser via parser's username
            parser_me = await parser.get_me()
            for s in active_senders:
                if s.get("session_name") == PARSER_SESSION:
                    continue
                sc = s["client"]
                s_id = s.get("user_info", {}).get("id", 0)
                if not s_id:
                    continue

                # Try sending by username (works without access_hash)
                try:
                    if parser_me.username:
                        msg = await sc.send_message(parser_me.username, ".")
                        await asyncio.sleep(0.3)
                        await sc.delete_messages(parser_me.username, [msg])
                        logger.info(f"Sender {s_id} introduced to parser via @{parser_me.username}")
                except Exception as e:
                    logger.warning(f"Sender {s_id} intro failed: {e}")
                await asyncio.sleep(0.5)

            # Parser refreshes entity cache by loading dialogs and extracting users
            sender_entities = {}  # user_id -> User object
            try:
                dialogs = await parser.get_dialogs(limit=100)
                for d in dialogs:
                    if d.entity and hasattr(d.entity, 'id'):
                        sender_entities[d.entity.id] = d.entity
                logger.info(f"Parser loaded {len(dialogs)} dialogs, {len(sender_entities)} user entities found")
            except Exception as e:
                logger.warning(f"Parser get_dialogs failed: {e}")

            # Also try getting messages from parser's recent chats
            try:
                from telethon.tl.functions.messages import GetDialogsRequest
                from telethon.tl.types import InputPeerEmpty
                result = await parser(GetDialogsRequest(
                    offset_date=None, offset_id=0, offset_peer=InputPeerEmpty(),
                    limit=50, hash=0
                ))
                if hasattr(result, 'users'):
                    for u in result.users:
                        if hasattr(u, 'id') and hasattr(u, 'access_hash') and u.access_hash:
                            sender_entities[u.id] = u
                    logger.info(f"Raw GetDialogs found {len(result.users)} users total")
            except Exception as e:
                logger.warning(f"Raw GetDialogs failed: {e}")

            # Now invite and promote each sender using extracted entities
            for s in active_senders:
                if s.get("session_name") == PARSER_SESSION:
                    continue
                sc = s["client"]
                s_id = s.get("user_info", {}).get("id", 0)
                if not s_id:
                    continue

                sender_user = sender_entities.get(s_id)
                if not sender_user:
                    logger.warning(f"Sender {s_id} not found in parser dialogs, skipping invite")
                    continue

                try:
                    try:
                        await parser(InviteToChannelRequest(channel, [sender_user]))
                        logger.info(f"Invited sender {s_id} to channel")
                    except errors.UserAlreadyParticipantError:
                        logger.info(f"Sender {s_id} already in channel")
                    except Exception as e:
                        logger.warning(f"Could not invite sender {s_id}: {e}")

                    try:
                        await parser(EditAdminRequest(channel, sender_user, admin_rights, rank="sender"))
                        logger.info(f"Promoted sender {s_id} to admin")
                    except Exception as e:
                        logger.warning(f"Could not promote sender {s_id}: {e}")

                    await asyncio.sleep(1)

                    # Sender caches participants
                    try:
                        count = 0
                        async for _ in sc.iter_participants(channel, limit=500):
                            count += 1
                        logger.info(f"Sender {s_id} cached {count} participants")
                    except Exception as e:
                        logger.warning(f"Sender {s_id} couldn't cache participants: {e}")

                except Exception as e:
                    logger.warning(f"Could not setup sender {s_id}: {e}")

        except Exception as e:
            logger.warning(f"Could not set up senders in channel: {e}")

    if not active_senders:
        logger.error("No active sender accounts available!")
        async with async_session() as db:
            campaign = await db.get(TgCampaign, campaign_id)
            if campaign:
                campaign.status = TgCampaignStatus.PAUSED.value
                await db.commit()
        return

    # Collect own account IDs to skip
    own_ids = set()
    for s in active_senders:
        info = s.get("user_info")
        if info and info.get("id"):
            own_ids.add(info["id"])
    if own_ids:
        logger.info(f"Will skip own accounts: {own_ids}")

    logger.info(f"Starting TG campaign {campaign_id} with {len(active_senders)} senders (delay={delay}s)")

    sender_idx = 0

    while True:
        async with async_session() as db:
            campaign = await db.get(TgCampaign, campaign_id)
            if not campaign or campaign.status != TgCampaignStatus.SENDING.value:
                logger.info(f"TG Campaign {campaign_id} stopped (status={campaign.status if campaign else 'deleted'})")
                break

            result = await db.execute(
                select(TgCampaignRecipient)
                .where(
                    TgCampaignRecipient.campaign_id == campaign_id,
                    TgCampaignRecipient.status == "pending",
                )
                .limit(1)
            )
            recipient = result.scalar_one_or_none()

            if not recipient:
                campaign.status = TgCampaignStatus.COMPLETED.value
                campaign.completed_at = datetime.utcnow()
                await db.commit()
                logger.info(f"TG Campaign {campaign_id} completed!")
                break

            # Skip own accounts
            if recipient.tg_user_id in own_ids:
                recipient.status = "skipped"
                recipient.error_message = "Собственный аккаунт"
                await db.commit()
                continue

            # Find sender (round-robin, check daily limit)
            sender = None
            for _ in range(len(active_senders)):
                candidate = active_senders[sender_idx % len(active_senders)]
                sender_idx += 1
                cand_info = candidate.get("user_info", {})
                cand_id = cand_info.get("id", 0) if cand_info else 0
                daily = await _get_sender_daily_sent(cand_id)
                if daily < TG_DAILY_LIMIT_PER_ACCOUNT:
                    sender = candidate
                    break

            if not sender:
                campaign.status = TgCampaignStatus.PAUSED.value
                await db.commit()
                logger.warning(f"TG Campaign {campaign_id} auto-paused: all senders at daily limit")
                break

            sender_client = sender["client"]
            sender_info = sender.get("user_info", {})
            sender_account_id = str(sender_info.get("id", "")) if sender_info else ""

            # Resolve target — each sender resolves with its own entity cache
            target = None
            try:
                target = await sender_client.get_entity(recipient.tg_user_id)
            except Exception:
                pass
            if target is None and recipient.username:
                try:
                    target = await sender_client.get_entity(recipient.username)
                except Exception:
                    pass
            if target is None:
                target = recipient.tg_user_id

            try:
                if campaign.image_path and os.path.exists(campaign.image_path):
                    await sender_client.send_file(
                        target,
                        campaign.image_path,
                        caption=campaign.message_text,
                    )
                else:
                    await sender_client.send_message(target, campaign.message_text)
                recipient.status = "sent"
                recipient.sent_at = datetime.utcnow()
                recipient.sent_by_account = sender_account_id
                campaign.sent_count += 1
                logger.info(
                    f"TG sent to {recipient.tg_user_id} via sender {sender_account_id} "
                    f"({recipient.username or recipient.first_name})"
                )

            except errors.FloodWaitError as e:
                logger.warning(f"FloodWait {e.seconds}s on sender {sender_account_id} — pausing campaign")
                recipient.error_message = f"FloodWait {e.seconds}s"
                campaign.status = TgCampaignStatus.PAUSED.value
                await db.commit()
                break

            except errors.UserPrivacyRestrictedError:
                recipient.status = "blocked"
                recipient.error_message = "Privacy settings"
                recipient.sent_by_account = sender_account_id
                campaign.failed_count += 1

            except errors.PeerFloodError:
                logger.warning(f"PeerFlood on sender {sender_account_id} — pausing campaign")
                recipient.error_message = "PeerFlood"
                campaign.status = TgCampaignStatus.PAUSED.value
                await db.commit()
                break

            except errors.UserIsBlockedError:
                recipient.status = "blocked"
                recipient.error_message = "User blocked"
                recipient.sent_by_account = sender_account_id
                campaign.failed_count += 1

            except Exception as e:
                recipient.status = "failed"
                recipient.error_message = str(e)[:500]
                recipient.sent_by_account = sender_account_id
                campaign.failed_count += 1
                logger.error(f"TG send error to {recipient.tg_user_id}: {e}")

            await db.commit()

        await asyncio.sleep(delay)

    _running_tasks.pop(campaign_id, None)


def start_tg_campaign(campaign_id: int):
    """Launch the campaign sending loop as an asyncio task."""
    if campaign_id in _running_tasks:
        task = _running_tasks[campaign_id]
        if not task.done():
            logger.info(f"TG Campaign {campaign_id} already running")
            return

    task = asyncio.create_task(run_tg_campaign(campaign_id))
    _running_tasks[campaign_id] = task
    logger.info(f"TG Campaign {campaign_id} task started")
