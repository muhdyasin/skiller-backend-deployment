from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.creator_payout_account import CreatorPayoutAccount


class PayoutAccountService:

    @staticmethod
    async def get_by_user(
        db: AsyncSession,
        user_id: str
    ):
        result = await db.execute(
            select(CreatorPayoutAccount)
            .where(
                CreatorPayoutAccount.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create_or_update(
        db: AsyncSession,
        user_id: str,
        **data
    ):
        account = await PayoutAccountService.get_by_user(
            db,
            user_id
        )

        if account:
            for key, value in data.items():
                setattr(account, key, value)

            if data.get("payout_type") == "bank_account":
                account.upi_id = None

            elif data.get("payout_type") == "upi":
                account.account_holder_name = None
                account.account_number = None
                account.ifsc_code = None

            # Any change to payout details requires verification again.
            account.is_verified = False

        else:
            account = CreatorPayoutAccount(
                user_id=user_id,
                **data
            )
            db.add(account)

        await db.commit()
        await db.refresh(account)

        return account