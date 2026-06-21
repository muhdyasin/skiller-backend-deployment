from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.xp_event import XPEvent


class XPService:

    @staticmethod
    async def award_xp(
        db: AsyncSession,
        user: User,
        reason: str,
        amount: int,
        meta: dict | None = None
    ):
        user.xp += amount

        event = XPEvent(
            user_id=user.id,
            reason=reason,
            amount=amount,
            meta=meta or {}
        )

        db.add(event)

        await db.commit()

        await db.refresh(user)

        return user