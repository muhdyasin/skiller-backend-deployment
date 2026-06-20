from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enrollment import Enrollment


class EnrollmentService:

    @staticmethod
    async def create_enrollment(
        db: AsyncSession,
        user_id: str,
        course_id: str,
        amount_paid: int = 0,
        payment_transaction_id: str = None
    ):
        enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id,
            amount_paid=amount_paid,
            payment_transaction_id=payment_transaction_id
        )

        db.add(enrollment)

        await db.commit()
        await db.refresh(enrollment)

        return enrollment

    @staticmethod
    async def get_user_enrollment(
        db: AsyncSession,
        user_id: str,
        course_id: str
    ):
        result = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_enrollments(
        db: AsyncSession,
        user_id: str
    ):
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.user_id == user_id)
        )

        return result.scalars().all()