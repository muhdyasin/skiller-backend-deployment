from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from db.dependencies import get_db
from core import get_current_user
from services.withdrawal_service import WithdrawalService


router = APIRouter(
    prefix="/api/admin/withdrawals",
    tags=["admin-withdrawals"]
)

class ApproveWithdrawalRequest(BaseModel):
    payout_provider: str = Field(
        default="manual",
        min_length=1,
        max_length=50
    )

    payout_reference: str = Field(
        min_length=1,
        max_length=255
    )

    remarks: str | None = None

def require_admin(user):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin only"
        )


@router.get("")
async def list_pending_withdrawals(
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current)

    return await WithdrawalService.get_pending_withdrawals(
        db
    )


@router.patch("/{withdrawal_id}/approve")
async def approve_withdrawal(
    withdrawal_id: str,
    data: ApproveWithdrawalRequest,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current)

    withdrawal = await WithdrawalService.get_by_id(
        db,
        withdrawal_id
    )

    if not withdrawal:
        raise HTTPException(
            status_code=404,
            detail="Withdrawal not found"
        )

    try:
        return await WithdrawalService.approve(
            db=db,
            withdrawal=withdrawal,
            payout_provider=data.payout_provider,
            payout_reference=data.payout_reference,
            remarks=data.remarks
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.patch("/{withdrawal_id}/reject")
async def reject_withdrawal(
    withdrawal_id: str,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    require_admin(current)

    withdrawal = await WithdrawalService.get_by_id(
        db,
        withdrawal_id
    )

    if not withdrawal:
        raise HTTPException(
            status_code=404,
            detail="Withdrawal not found"
        )

    try:
        return await WithdrawalService.reject(
            db,
            withdrawal,
            "Rejected by admin"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )