from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.course import Course


class CourseService:

    @staticmethod
    async def create_course(
        db: AsyncSession,
        **kwargs
    ):
        course = Course(**kwargs)

        db.add(course)

        await db.commit()
        await db.refresh(course)

        return course

    @staticmethod
    async def get_course(
        db: AsyncSession,
        course_id: str
    ):
        result = await db.execute(
            select(Course)
            .where(Course.id == course_id)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_courses(
        db: AsyncSession
    ):
        result = await db.execute(
            select(Course)
        )

        return result.scalars().all()

    @staticmethod
    async def increment_students(
        db: AsyncSession,
        course: Course
    ):
        course.students += 1

        await db.commit()
        await db.refresh(course)

        return course
    
    @staticmethod
    async def update_course(
        db: AsyncSession,
        course,
        updates: dict
    ):
        for key, value in updates.items():
            setattr(course, key, value)

        await db.commit()
        await db.refresh(course)

        return course


    @staticmethod
    async def delete_course(
        db: AsyncSession,
        course
    ):
        await db.delete(course)
        await db.commit()


