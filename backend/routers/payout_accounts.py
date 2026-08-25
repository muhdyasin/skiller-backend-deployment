from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core import get_current_user
from db.dependencies import get_db
from services.payout_account_service import PayoutAccountService


router = APIRouter(
    prefix="/api/payout-account",
    tags=["Payout Account"]
)


class PayoutAccountIn(BaseModel):
    payout_type: str = Field(
        min_length=1,
        max_length=20
    )
    account_holder_name: str | None = Field(
        default=None,
        max_length=255
    )
    account_number: str | None = Field(
        default=None,
        max_length=100
    )
    ifsc_code: str | None = Field(
        default=None,
        max_length=20
    )
    upi_id: str | None = Field(
        default=None,
        max_length=255
    )


@router.get("/me")
async def get_my_payout_account(
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current.get("role") != "creator":
        raise HTTPException(
            status_code=403,
            detail="Only creators can access payout accounts"
        )

    account = await PayoutAccountService.get_by_user(
        db,
        current["id"]
    )

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Payout account not found"
        )

    return account


@router.put("/me")
async def update_my_payout_account(
    data: PayoutAccountIn,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current.get("role") != "creator":
        raise HTTPException(
            status_code=403,
            detail="Only creators can manage payout accounts"
        )

    if data.payout_type not in ("bank_account", "upi"):
        raise HTTPException(
            status_code=400,
            detail="payout_type must be 'bank_account' or 'upi'"
        )

    if data.payout_type == "bank_account":
        if not data.account_holder_name:
            raise HTTPException(
                status_code=400,
                detail="Account holder name is required"
            )

        if not data.account_number:
            raise HTTPException(
                status_code=400,
                detail="Account number is required"
            )

        if not data.ifsc_code:
            raise HTTPException(
                status_code=400,
                detail="IFSC code is required"
            )

    if data.payout_type == "upi":
        if not data.upi_id:
            raise HTTPException(
                status_code=400,
                detail="UPI ID is required"
            )

    account = await PayoutAccountService.create_or_update(
        db=db,
        user_id=current["id"],
        payout_type=data.payout_type,
        account_holder_name=data.account_holder_name,
        account_number=data.account_number,
        ifsc_code=data.ifsc_code,
        upi_id=data.upi_id,
        is_active=True
    )

    return account
