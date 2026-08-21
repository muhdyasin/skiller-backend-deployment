from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.wallet import Wallet
from models.wallet_ledger import WalletLedger


class WalletService:

    @staticmethod
    async def get_wallet(
        db: AsyncSession,
        owner_id: str
    ):
        result = await db.execute(
            select(Wallet).where(
                Wallet.owner_id == owner_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_wallet_for_update(
        db: AsyncSession,
        owner_id: str
    ):
        result = await db.execute(
            select(Wallet)
            .where(Wallet.owner_id == owner_id)
            .with_for_update()
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create_wallet(
        db: AsyncSession,
        owner_id: str,
        owner_type: str
    ):
        wallet = Wallet(
            owner_id=owner_id,
            owner_type=owner_type
        )

        db.add(wallet)

        await db.commit()
        await db.refresh(wallet)

        return wallet

    @staticmethod
    async def get_or_create_wallet(
        db: AsyncSession,
        owner_id: str,
        owner_type: str
    ):
        wallet = await WalletService.get_wallet(
            db,
            owner_id
        )

        if wallet:
            return wallet

        return await WalletService.create_wallet(
            db,
            owner_id,
            owner_type
        )

    @staticmethod
    async def create_ledger_entry(
        db: AsyncSession,
        wallet_id: str,
        transaction_type: str,
        amount,
        reference_type: str = None,
        reference_id: str = None,
        description: str = None
    ):
        entry = WalletLedger(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            amount=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description
        )

        db.add(entry)
        await db.flush()

        return entry

    @staticmethod
    async def get_wallet_ledger(
        db: AsyncSession,
        wallet_id: str
    ):
        result = await db.execute(
            select(WalletLedger)
            .where(
                WalletLedger.wallet_id == wallet_id
            )
            .order_by(
                WalletLedger.created_at.desc()
            )
        )

        return result.scalars().all()

    @staticmethod
    async def credit_wallet(
        db: AsyncSession,
        wallet: Wallet,
        amount,
        description: str = None,
        reference_type: str = None,
        reference_id: str = None
    ):
        wallet.balance += amount
        wallet.lifetime_earned += amount

        await WalletService.create_ledger_entry(
            db=db,
            wallet_id=wallet.id,
            transaction_type="credit",
            amount=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description
        )

        await db.flush()
        return wallet

    @staticmethod
    async def debit_wallet(
        db: AsyncSession,
        wallet: Wallet,
        amount: int,
        description: str = None
    ):
        if wallet.balance < amount:
            raise ValueError(
                "Insufficient wallet balance"
            )

        wallet.balance -= amount
        wallet.lifetime_withdrawn += amount

        await db.commit()
        await db.refresh(wallet)

        await WalletService.create_ledger_entry(
        db=db,
        wallet_id=wallet.id,
        transaction_type="debit",
        amount=amount,
        description=description
        )

        return wallet

    @staticmethod
    async def reserve_withdrawal(
        db: AsyncSession,
        wallet: Wallet,
        amount,
        withdrawal_id: str
    ):
        if wallet.balance < amount:
            raise ValueError("Insufficient wallet balance")

        wallet.balance -= amount
        wallet.pending_balance += amount

        await WalletService.create_ledger_entry(
            db=db,
            wallet_id=wallet.id,
            transaction_type="withdrawal_pending",
            amount=amount,
            reference_type="withdrawal",
            reference_id=withdrawal_id,
            description="Withdrawal funds reserved"
        )

        await db.flush()

        return wallet


    @staticmethod
    async def complete_withdrawal(
        db: AsyncSession,
        wallet: Wallet,
        amount,
        withdrawal_id: str
    ):
        if wallet.pending_balance < amount:
            raise ValueError("Insufficient pending withdrawal balance")

        wallet.pending_balance -= amount
        wallet.lifetime_withdrawn += amount

        await WalletService.create_ledger_entry(
            db=db,
            wallet_id=wallet.id,
            transaction_type="withdrawal_completed",
            amount=amount,
            reference_type="withdrawal",
            reference_id=withdrawal_id,
            description="Withdrawal completed"
        )

        await db.flush()

        return wallet


    @staticmethod
    async def release_withdrawal(
        db: AsyncSession,
        wallet: Wallet,
        amount,
        withdrawal_id: str,
        description: str = "Withdrawal failed - funds released"
    ):
        if wallet.pending_balance < amount:
            raise ValueError("Insufficient pending withdrawal balance")

        wallet.pending_balance -= amount
        wallet.balance += amount

        await WalletService.create_ledger_entry(
            db=db,
            wallet_id=wallet.id,
            transaction_type="withdrawal_released",
            amount=amount,
            reference_type="withdrawal",
            reference_id=withdrawal_id,
            description=description
        )

        await db.flush()

        return wallet
