import hashlib
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_db
from models.partner import Partner


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_partner(
    x_api_key: str = Header(..., alias="X-API-KEY"),
    db: AsyncSession = Depends(get_db),
) -> Partner:
    key_hash = _hash_api_key(x_api_key)
    result = await db.execute(
        select(Partner).where(Partner.api_key_hash == key_hash, Partner.is_active == True)
    )
    partner = result.scalars().first()
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key.",
        )
    return partner
