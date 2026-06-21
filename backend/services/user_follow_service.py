from sqlalchemy import select
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