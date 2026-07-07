"""Courses CRUD + enrollment."""

from fastapi import APIRouter, HTTPException, Depends
from core import (
    get_current_user,
    award_xp,
    CourseCreate,
    CourseUpdate,
)

from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from services.payment_service import PaymentService
from services.wallet_service import WalletService
from services.enrollment_service import EnrollmentService
from services.course_service import CourseService

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("")
async def list_courses(pg_db: AsyncSession = Depends(get_db)):
    courses = await CourseService.list_courses(
    pg_db
    )

    return courses

@router.get("/{course_id}")
async def get_course(
    course_id: str,
    pg_db: AsyncSession = Depends(get_db)
):
    course = await CourseService.get_course(
        pg_db,
        course_id
    )

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    return course


@router.post("")
async def create_course(
    data: CourseCreate,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    course = await CourseService.create_course(
        db=pg_db,
        owner_id=current["id"],
        instructor=current["name"],
        title=data.title,
        description=data.description,
        price=data.price,
        lessons=data.lessons,
        thumbnail=data.thumbnail or "https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=1200&q=80",
        category=data.category,
        rating=5.0,
        students=0
    )

    return course


@router.patch("/{course_id}")
async def update_course(
    course_id: str,
    data: CourseUpdate,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    course = await CourseService.get_course(
        pg_db,
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

    updates = {
        k: v
        for k, v in data.model_dump().items()
        if v is not None
    }

    updated_course = await CourseService.update_course(
        pg_db,
        course,
        updates
    )

    return updated_course


@router.delete("/{course_id}")
async def delete_course(
    course_id: str,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    course = await CourseService.get_course(
        pg_db,
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

    await CourseService.delete_course(
        pg_db,
        course
    )

    return {
        "ok": True
    }


@router.post("/{course_id}/enroll")
async def enroll_course(
    course_id: str,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    course = await CourseService.get_course(
        pg_db,
        course_id
    )

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    existing = await EnrollmentService.get_user_enrollment(
        pg_db,
        current["id"],
        course_id
    )

    if existing:
        return {
            "ok": True,
            "already": True
        }

    await EnrollmentService.create_enrollment(
        db=pg_db,
        user_id=current["id"],
        course_id=course_id
    )

    await CourseService.increment_students(
        pg_db,
        course
    )

    await award_xp(
        current["id"],
        "course_enroll"
    )

    return {
        "ok": True
    }


@router.post("/{course_id}/purchase")
async def purchase_course(
    course_id: str,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    # Find course
    course = await CourseService.get_course(
        pg_db,
        course_id
    )
    
    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    # Prevent buying own course
    if course.owner_id == current["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot purchase your own course"
        )

    # Check existing enrollment
    existing = await EnrollmentService.get_user_enrollment(
        pg_db,
        current["id"],
        course_id
    )

    if existing:
        return {
            "ok": True,
            "already_enrolled": True
        }

    price = int(course.price)

    # Commission (10%)
    commission_amount = int(price * 0.10)

    # Creator receives 90%
    creator_amount = price - commission_amount

    # Create payment transaction
    transaction = (
        await PaymentService.create_course_purchase_transaction(
            db=pg_db,
            payer_id=current["id"],
            payee_id=course.owner_id,
            amount=price,
            commission_amount=commission_amount
        )
    )

    # Credit creator wallet
    creator_wallet = (
        await WalletService.get_or_create_wallet(
            pg_db,
            course.owner_id,
            "creator"
        )
    )

    await WalletService.credit_wallet(
        pg_db,
        creator_wallet,
        creator_amount,
        f"Course purchase: {course.title}"
    )

    # Mark transaction paid
    await PaymentService.mark_paid(
        pg_db,
        transaction
    )

    # Create enrollment
    await EnrollmentService.create_enrollment(
        db=pg_db,
        user_id=current["id"],
        course_id=course_id,
        amount_paid=price,
        payment_transaction_id=transaction.id
    )

    # Increment student count
    await CourseService.increment_students(
        pg_db,
        course
    )

    await award_xp(
        current["id"],
        "course_enroll"
    )

    return {
        "ok": True,
        "transaction_id": transaction.id,
        "course_id": course_id,
        "amount": price,
        "commission_amount": commission_amount,
        "creator_amount": creator_amount
    }
