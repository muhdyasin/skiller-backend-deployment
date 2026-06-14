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
    amount: int = Field(gt=0)
    
@router.post("/")
async def request_withdrawal(
    data: WithdrawalRequest,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    wallet = await WalletService.get_or_create_wallet(
        db,
        current["id"],
        current["role"]
    )

    if wallet.balance < data.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )

    withdrawal = Withdrawal(
        user_id=current["id"],
        amount=data.amount,
        status="pending"
    )

    db.add(withdrawal)

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

