from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application


class ApplicationService:

    @staticmethod
    async def create_application(
        db: AsyncSession,
        **kwargs
    ):
        application = Application(**kwargs)

        db.add(application)

        await db.commit()
        await db.refresh(application)

        return application

    @staticmethod
    async def get_application(
        db: AsyncSession,
        application_id: str
    ):
        result = await db.execute(
            select(Application)
            .where(Application.id == application_id)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_gig_applications(
        db: AsyncSession,
        gig_id: str
    ):
        result = await db.execute(
            select(Application)
            .where(Application.gig_id == gig_id)
            .order_by(Application.created_at.desc())
        )

        return result.scalars().all()
    
    @staticmethod
    async def get_user_application(
        db: AsyncSession,
        gig_id: str,
        user_id: str
    ):
        result = await db.execute(
            select(Application)
            .where(
                Application.gig_id == gig_id,
                Application.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        application,
        status: str
    ):
        application.status = status

        await db.commit()
        await db.refresh(application)

        return application

    @staticmethod
    async def get_application_by_id(
        db: AsyncSession,
        application_id: str
    ):
        result = await db.execute(
            select(Application)
            .where(Application.id == application_id)
        )

        return result.scalar_one_or_none()
    