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
        withdrawal: Withdrawal,
        payout_provider: str = "manual",
        payout_reference: str = None,
        remarks: str = None,
    ):
        if withdrawal.status != "pending":
            raise ValueError(
                f"Withdrawal cannot be approved from status '{withdrawal.status}'"
            )

        if not payout_reference:
            raise ValueError(
                "Payout reference is required"
        )

        wallet = await WalletService.get_wallet_for_update(
            db,
            withdrawal.user_id
        )

        if not wallet:
            raise ValueError(
                "Wallet not found"
            )

        await WalletService.complete_withdrawal(
            db=db,
            wallet=wallet,
            amount=withdrawal.amount,
            withdrawal_id=withdrawal.id
        )

        withdrawal.status = "successful"
        withdrawal.payout_provider = payout_provider
        withdrawal.payout_reference = payout_reference
        withdrawal.remarks = remarks
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
        if withdrawal.status != "pending":
            raise ValueError(
                f"Withdrawal cannot be rejected from status '{withdrawal.status}'"
            )

        wallet = await WalletService.get_wallet_for_update(
            db,
            withdrawal.user_id
        )

        if not wallet:
            raise ValueError(
                "Wallet not found"
            )

        await WalletService.release_withdrawal(
            db=db,
            wallet=wallet,
            amount=withdrawal.amount,
            withdrawal_id=withdrawal.id,
            description="Withdrawal rejected - funds released"
        )

        withdrawal.status = "failed"
        withdrawal.remarks = remarks
        withdrawal.processed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(withdrawal)

        return withdrawal