from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_follow import UserFollow


class UserFollowService:

    @staticmethod
    async def get_follow(
        db: AsyncSession,
        follower_id: str,
        following_id: str
    ):
        result = await db.execute(
            select(UserFollow).where(
                UserFollow.follower_id == follower_id,
                UserFollow.following_id == following_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create_follow(
        db: AsyncSession,
        follower_id: str,
        following_id: str
    ):
        follow = UserFollow(
            follower_id=follower_id,
            following_id=following_id
        )

        db.add(follow)

        await db.commit()
        await db.refresh(follow)

        return follow

    @staticmethod
    async def delete_follow(
        db: AsyncSession,
        follow: UserFollow
    ):
        await db.delete(follow)
        await db.commit()
        
    @staticmethod
    async def count_followers(
        db,
        user_id: str
    ):
        result = await db.execute(
            select(func.count())
            .select_from(UserFollow)
            .where(
                UserFollow.following_id == user_id
            )
        )

        return result.scalar() or 0
    
    @staticmethod
    async def count_following(
        db,
        user_id: str
    ):
        result = await db.execute(
            select(func.count())
            .select_from(UserFollow)
            .where(
                UserFollow.follower_id == user_id
            )
        )

        return result.scalar() or 0
    
    
    @staticmethod
    async def is_following(
        db,
        follower_id: str,
        following_id: str
    ):
        result = await db.execute(
            select(UserFollow)
            .where(
                UserFollow.follower_id == follower_id,
                UserFollow.following_id == following_id
            )
        )

        return result.scalar_one_or_none() is not None
    
    
    @staticmethod
    async def get_following_ids(
        db,
        follower_id: str
    ):
        result = await db.execute(
            select(UserFollow.following_id)
            .where(
                UserFollow.follower_id == follower_id
            )
        )

        return list(result.scalars().all())
