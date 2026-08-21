from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from core import get_current_user

from models.withdrawal import Withdrawal
from services.wallet_service import WalletService

router = APIRouter(
    prefix="/api/withdrawals",
    tags=["Withdrawals"]
)

from pydantic import BaseModel, Field


class WithdrawalRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    idempotency_key:str = Field(
        min_length=1,
        max_length=255
    )

@router.post("/")
async def request_withdrawal(
    data: WithdrawalRequest,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    existing_result = await db.execute(
        select(Withdrawal)
        .where(
            Withdrawal.user_id == current["id"],
            Withdrawal.idempotency_key == data.idempotency_key
        )
    )

    existing = existing_result.scalar_one_or_none()

    if existing:
        return existing

    wallet = await WalletService.get_wallet_for_update(
        db,
        current["id"]
    )

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found"
        )

    withdrawal = Withdrawal(
        user_id=current["id"],
        amount=data.amount,
        status="pending",

        idempotency_key = data.idempotency_key
    )

    db.add(withdrawal)

    await db.flush()

    try:
        await WalletService.reserve_withdrawal(
            db=db,
            wallet=wallet,
            amount=data.amount,
            withdrawal_id=withdrawal.id
        )

    except ValueError as e:
        await db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    await db.commit()
    await db.refresh(withdrawal)

    return withdrawal

@router.get("/me")
async def my_withdrawals(
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Withdrawal)
        .where(
            Withdrawal.user_id == current["id"]
        )
        .order_by(
            Withdrawal.requested_at.desc()
        )
    )

    return result.scalars().all()

