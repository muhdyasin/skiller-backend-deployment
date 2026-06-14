from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from core import get_current_user

from services.wallet_service import WalletService

router = APIRouter(
    prefix="/api/wallets",
    tags=["Wallets"]
)

@router.get("/me")
async def my_wallet(
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    wallet = await WalletService.get_or_create_wallet(
        db,
        current["id"],
        current["role"]
    )

    return wallet

@router.get("/ledger")
async def wallet_ledger(
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    wallet = await WalletService.get_or_create_wallet(
        db,
        current["id"],
        current["role"]
    )

    ledger = await WalletService.get_wallet_ledger(
        db,
        wallet.id
    )

    return ledger


