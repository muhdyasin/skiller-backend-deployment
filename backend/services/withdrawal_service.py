from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.withdrawal import Withdrawal
from services.wallet_service import WalletService


class WithdrawalService:

    @staticmethod
    async def get_pending_withdrawals(
        db: AsyncSession
    ):
        result = await db.execute(
            select(Withdrawal)
            .where(
                Withdrawal.status == "pending"
            )
            .order_by(
                Withdrawal.requested_at.desc()
            )
        )

        return result.scalars().all()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        withdrawal_id: str
    ):
        result = await db.execute(
            select(Withdrawal)
            .where(
                Withdrawal.id == withdrawal_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def approve(
        db: AsyncSession,
        withdrawal: Withdrawal
    ):
        wallet = await WalletService.get_wallet(
            db,
            withdrawal.user_id
        )

        if wallet:
            await WalletService.create_ledger_entry(
                db=db,
                wallet_id=wallet.id,
                transaction_type="withdrawal_approved",
                amount=withdrawal.amount,
                reference_type="withdrawal",
                reference_id=withdrawal.id,
                description="Withdrawal approved"
            )

        withdrawal.status = "approved"
        withdrawal.processed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(withdrawal)

        return withdrawal

    @staticmethod
    async def reject(
        db: AsyncSession,
        withdrawal: Withdrawal,
        remarks: str = None,
    ):
        wallet = await WalletService.get_wallet(
            db,
            withdrawal.user_id
        )

        if wallet:
            await WalletService.credit_wallet(
                db,
                wallet,
                withdrawal.amount,
                "Withdrawal rejected refund"
            )

        withdrawal.status = "rejected"
        withdrawal.remarks = remarks
        withdrawal.processed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(withdrawal)

        return withdrawal