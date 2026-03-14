"""
SMTP Accounts management — CRUD API for multi-account rotation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
import datetime

from backend.database import get_db
from backend.models import SmtpAccount

router = APIRouter(prefix="/api/smtp-accounts", tags=["smtp"])


class SmtpAccountCreate(BaseModel):
    email: str
    password: str
    smtp_host: str = "smtp.mail.ru"
    smtp_port: int = 465
    use_tls: bool = True


class SmtpAccountUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    use_tls: Optional[bool] = None
    active: Optional[bool] = None


class SmtpAccountResponse(BaseModel):
    id: int
    email: str
    smtp_host: str
    smtp_port: int
    use_tls: bool
    active: bool
    send_count: int
    last_used_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[SmtpAccountResponse])
async def list_smtp_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SmtpAccount).order_by(SmtpAccount.id))
    return result.scalars().all()


@router.post("", response_model=SmtpAccountResponse)
async def create_smtp_account(data: SmtpAccountCreate, db: AsyncSession = Depends(get_db)):
    account = SmtpAccount(**data.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.put("/{account_id}", response_model=SmtpAccountResponse)
async def update_smtp_account(account_id: int, data: SmtpAccountUpdate, db: AsyncSession = Depends(get_db)):
    account = await db.get(SmtpAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="SMTP account not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(account, key, value)

    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}")
async def delete_smtp_account(account_id: int, db: AsyncSession = Depends(get_db)):
    account = await db.get(SmtpAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="SMTP account not found")

    await db.delete(account)
    await db.commit()
    return {"message": "SMTP account deleted"}
