from sqlalchemy import func,select
from sqlalchemy.ext.asyncio import AsyncSession

from models.lesson import Lesson
from models.course import Course


class LessonService:

    @staticmethod
    async def create_lesson(
        db: AsyncSession,
        course_id: str,
        **kwargs
    ):
        lesson = Lesson(
            course_id=course_id,
            **kwargs
        )

        db.add(lesson)

        # Update lesson count
        course = await db.get(Course, course_id)

        if course:
            course.lessons += 1

        await db.commit()
        await db.refresh(lesson)

        return lesson

    @staticmethod
    async def list_course_lessons(
        db: AsyncSession,
        course_id: str
    ):
        result = await db.execute(
            select(Lesson)
            .where(Lesson.course_id == course_id)
            .order_by(Lesson.order_index)
        )

        return result.scalars().all()

    @staticmethod
    async def get_lesson(
        db: AsyncSession,
        lesson_id: str
    ):
        return await db.get(
            Lesson,
            lesson_id
        )

    @staticmethod
    async def update_lesson(
        db: AsyncSession,
        lesson: Lesson,
        updates: dict
    ):
        for key, value in updates.items():
            setattr(
                lesson,
                key,
                value
            )

        await db.commit()
        await db.refresh(lesson)

        return lesson

    @staticmethod
    async def delete_lesson(
        db: AsyncSession,
        lesson: Lesson
    ):
        course = await db.get(
            Course,
            lesson.course_id
        )

        await db.delete(lesson)

        result = await db.execute(
            select(func.count(Lesson.id))
            .where(Lesson.course_id == course.id)
        )

        course.lessons = max(result.scalar() - 1,0)

        await db.commit()