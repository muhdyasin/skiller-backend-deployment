from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from core import get_current_user

from services.enrollment_service import EnrollmentService

router = APIRouter(
    prefix="/api/enrollments",
    tags=["Enrollments"]
)

@router.get("/me")
async def my_enrollments(
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await EnrollmentService.get_user_enrollments(
        db,
        current["id"]
    )