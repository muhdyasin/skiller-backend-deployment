from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from core import get_current_user
from services.withdrawal_service import WithdrawalService

router = APIRouter(
    prefix="/api/admin/withdrawals",
    tags=["admin-withdrawals"]
)


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

    return await WithdrawalService.approve(
        db,
        withdrawal
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

    return await WithdrawalService.reject(
        db,
        withdrawal,
        "Rejected by admin"
    )