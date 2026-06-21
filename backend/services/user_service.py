from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


class UserService:

    @staticmethod
    async def get_user(
        db: AsyncSession,
        user_id: str
    ):
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(
        db: AsyncSession,
        email: str
    ):
        result = await db.execute(
            select(User)
            .where(User.email == email)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(
        db: AsyncSession,
        username: str
    ):
        result = await db.execute(
            select(User)
            .where(User.username == username)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        db: AsyncSession,
        **kwargs
    ):
        user = User(**kwargs)

        db.add(user)

        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user: User,
        updates: dict
    ):
        for key, value in updates.items():
            setattr(user, key, value)

        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def list_users(
        db: AsyncSession
    ):
        result = await db.execute(
            select(User)
            .order_by(User.created_at.desc())
        )

        return result.scalars().all()
    
    @staticmethod
    async def get_all_users(
        db: AsyncSession
    ):
        result = await db.execute(
            select(User)
            .order_by(User.created_at.desc())
        )

        return result.scalars().all()


    @staticmethod
    async def get_user_by_username(
        db: AsyncSession,
        username: str
    ):
        result = await db.execute(
            select(User)
            .where(User.username == username)
        )

        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_leaderboard(
        db: AsyncSession,
        limit: int = 20
    ):
        result = await db.execute(
            select(User)
            .order_by(User.xp.desc())
            .limit(limit)
        )

        return result.scalars().all()