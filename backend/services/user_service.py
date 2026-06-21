from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from sqlalchemy import func
from models.user_follow import UserFollow


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
    
    @staticmethod
    async def increment_xp(
        db: AsyncSession,
        user: User,
        amount: int
    ):
        user.xp += amount

        await db.commit()

        await db.refresh(user)

        return user
    

    @staticmethod
    async def get_user_dict(
        db: AsyncSession,
        user_id: str
    ):
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
        )

        user = result.scalar_one_or_none()

        if not user:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "name": user.name,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "xp": user.xp,
            "badges": user.badges or [],
            "streak": user.streak,
            "email_verified": user.email_verified,
            "referral_code": user.referral_code,
            "referred_by": user.referred_by,
            "plan": user.plan,
            "premium_until": (
                user.premium_until.isoformat()
                if user.premium_until
                else None
            ),
            "created_at": (
                user.created_at.isoformat()
                if user.created_at
                else None
            )
        }
        
        
    @staticmethod
    async def get_followers_count(
        db: AsyncSession,
        user_id: str
    ):
        
        result = await db.execute(
            select(
                func.count(UserFollow.id)
            ).where(
                UserFollow.following_id == user_id
            )
        )

        return result.scalar() or 0
        
        
    @staticmethod
    async def get_user_summary(
        db: AsyncSession,
        user_id: str
    ):
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
        )

        user = result.scalar_one_or_none()

        if not user:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
        }
        