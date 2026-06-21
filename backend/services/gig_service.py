from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.gig import Gig
from models.application import Application


class GigService:

    @staticmethod
    async def create_gig(
        db: AsyncSession,
        **kwargs
    ):
        gig = Gig(**kwargs)

        db.add(gig)

        await db.commit()
        await db.refresh(gig)

        return gig

    @staticmethod
    async def get_gig(
        db: AsyncSession,
        gig_id: str
    ):
        result = await db.execute(
            select(Gig)
            .where(Gig.id == gig_id)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_gigs(
        db: AsyncSession
    ):
        result = await db.execute(
            select(Gig)
            .order_by(Gig.created_at.desc())
        )

        return result.scalars().all()

    @staticmethod
    async def get_creator_gigs(
        db: AsyncSession,
        owner_id: str
    ):
        result = await db.execute(
            select(Gig)
            .where(Gig.owner_id == owner_id)
            .order_by(Gig.created_at.desc())
        )

        return result.scalars().all()

    @staticmethod
    async def update_gig(
        db: AsyncSession,
        gig,
        updates: dict
    ):
        for k, v in updates.items():
            setattr(gig, k, v)

        await db.commit()
        await db.refresh(gig)

        return gig

    @staticmethod
    async def delete_gig(
        db: AsyncSession,
        gig
    ):
        await db.delete(gig)
        await db.commit()
        

    @staticmethod
    async def count_applications(
        db: AsyncSession,
        gig_id: str
    ):
        result = await db.execute(
            select(Application)
            .where(Application.gig_id == gig_id)
        )

        return len(result.scalars().all())


    @staticmethod
    async def get_creator_gigs_with_counts(
        db: AsyncSession,
        owner_id: str
    ):
        gigs = await GigService.get_creator_gigs(
            db,
            owner_id
        )

        result = []

        for gig in gigs:

            count = await GigService.count_applications(
                db,
                gig.id
            )

            item = {
                "id": gig.id,
                "owner_id": gig.owner_id,
                "owner_username": gig.owner_username,
                "owner_name": gig.owner_name,
                "title": gig.title,
                "description": gig.description,
                "budget": gig.budget,
                "currency": gig.currency,
                "location": gig.location,
                "category": gig.category,
                "skills": gig.skills,
                "created_at": gig.created_at,
                "application_count": count
            }

            result.append(item)

        return result