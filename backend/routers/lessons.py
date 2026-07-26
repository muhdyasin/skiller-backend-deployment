from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from core import (
    get_current_user,
    LessonCreate,
    LessonUpdate
)
from models.course import Course
from models.lesson import Lesson
from services.course_service import CourseService
from services.lesson_service import LessonService

router = APIRouter(
    prefix="/api",
    tags=["Lessons"]
)


@router.post("/courses/{course_id}/lessons")
async def create_lesson(
    course_id: str,
    data: LessonCreate,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    course = await CourseService.get_course(
        db,
        course_id
    )

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    if (
        course.owner_id != current["id"]
        and current.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    return await LessonService.create_lesson(
        db=db,
        course_id=course_id,
        title=data.title,
        description=data.description,
        youtube_url=data.youtube_url,
        notes_links=data.notes_links,
        order_index=data.order_index
    )


@router.get("/courses/{course_id}/lessons")
async def list_lessons(
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    return await LessonService.list_course_lessons(
        db,
        course_id
    )


@router.patch("/lessons/{lesson_id}")
async def update_lesson(
    lesson_id: str,
    data: LessonUpdate,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    lesson = await LessonService.get_lesson(
        db,
        lesson_id
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found"
        )

    course = await CourseService.get_course(
        db,
        lesson.course_id
    )

    if (
        course.owner_id != current["id"]
        and current.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    updates = data.model_dump(exclude_unset=True)

    return await LessonService.update_lesson(
        db,
        lesson,
        updates
    )


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: str,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    lesson = await LessonService.get_lesson(
        db,
        lesson_id
    )

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found"
        )

    course = await CourseService.get_course(
        db,
        lesson.course_id
    )

    if (
        course.owner_id != current["id"]
        and current.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    await LessonService.delete_lesson(
        db,
        lesson
    )

    return {
        "ok": True
    }