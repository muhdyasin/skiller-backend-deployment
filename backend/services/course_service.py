from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.course import Course
from models.lesson import Lesson


class CourseService:

    @staticmethod
    async def create_course(
        db: AsyncSession,
        **kwargs
    ):
        lesson_items = kwargs.pop("lesson_items", [])

        # Keep lesson count synchronized
        kwargs["lessons"] = len(lesson_items)

        # Create course
        course = Course(**kwargs)

        db.add(course)

        # Flush so course.id is available
        await db.flush()

        # Create lesson records
        for lesson in lesson_items:
            db.add(
                Lesson(
                    course_id=course.id,
                    title=lesson.title,
                    description=lesson.description,
                    youtube_url=lesson.youtube_url,
                    notes_links=lesson.notes_links,
                    order_index=lesson.order_index
                )
            )

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
            .options(
                selectinload(Course.lesson_items)
            )
            .where(Course.id == course_id)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_courses(
        db: AsyncSession
    ):
        result = await db.execute(
            select(Course)
            .options(
                selectinload(Course.lesson_items)
            )
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


