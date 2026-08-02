"""Courses CRUD + enrollment."""

from fastapi import APIRouter, HTTPException, Depends
from core import (
    get_current_user,
    award_xp,
    CourseCreate,
    CourseUpdate,
)

import os
import razorpay
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Literal, Optional

from db.dependencies import get_db
from services.payment_service import PaymentService
from services.wallet_service import WalletService
from services.enrollment_service import EnrollmentService
from services.course_service import CourseService
from routers.billing import verify_razorpay_signature

router = APIRouter(prefix="/api/courses", tags=["courses"])

logger = logging.getLogger("skiller")

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

_rzp_client: Optional[razorpay.Client] = None

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    _rzp_client = razorpay.Client(
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )

class CourseCheckoutIn(BaseModel):
    pay_with: Literal["razorpay"] = "razorpay"
    
class CourseVerifyPaymentIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.get("")
async def list_courses(pg_db: AsyncSession = Depends(get_db)):
    courses = await CourseService.list_courses(
    pg_db
    )

    return courses

@router.get("/enrolled")
async def list_enrolled_courses(
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    return await CourseService.list_enrolled_courses(
        pg_db,
        current["id"]
    )


@router.get("/not-enrolled")
async def list_not_enrolled_courses(
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    return await CourseService.list_not_enrolled_courses(
        pg_db,
        current["id"]
    )

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

        # NEW
        lesson_items=data.lesson_items,

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

    return {
        "ok": True
    }

@router.post("/{course_id}/checkout")
async def checkout_course(
    course_id: str,
    data: CourseCheckoutIn,
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
        
    existing = await EnrollmentService.get_user_enrollment(
    pg_db,
    current["id"],
    course_id
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Already enrolled in this course"
        )

    # Check Razorpay configuration
    if not _rzp_client:
        raise HTTPException(
            status_code=503,
            detail="Razorpay not configured"
        )

    amount_paise = int(course.price) * 100

    # Receipt must be <= 40 characters
    receipt = f"course_{course.id[:12]}_{current['id'][:18]}"[:40]

    try:
        order = _rzp_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
            "notes": {
                "course_id": course.id,
                "user_id": current["id"],
                "user_email": current.get("email", "")
            }
        })
    except Exception as e:
        logger.exception("Course Razorpay order creation failed")
        raise HTTPException(
            status_code=502,
            detail=f"Razorpay error: {e}"
        )

    # Store transaction in 'created' state
    await PaymentService.create_razorpay_order_transaction(
        db=pg_db,
        payer_id=current["id"],
        amount=int(course.price),
        order_id=order["id"],
        course_id=course.id
    )

    return {
        "provider": "razorpay",
        "status": "order_created",
        "key_id": RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "course_id": course.id,
        "course_title": course.title,
        "prefill": {
            "name": current.get("name", ""),
            "email": current.get("email", "")
        }
    }
    
@router.post("/verify-payment")
async def verify_course_payment(
    data: CourseVerifyPaymentIn,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Razorpay not configured"
        )

    # Verify Razorpay signature
    verify_razorpay_signature(
        data.razorpay_order_id,
        data.razorpay_payment_id,
        data.razorpay_signature
    )

    # Find pending transaction
    transaction = await PaymentService.get_transaction_by_order_id(
        pg_db,
        data.razorpay_order_id
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    if transaction.transaction_type != "course_purchase":
        raise HTTPException(
            status_code=400,
            detail="Invalid transaction type"
        )

    if transaction.status == "paid":
        return {
            "status": "already_paid",
            "transaction_id": transaction.id
        }

    course = await CourseService.get_course(
        pg_db,
        transaction.course_id
    )

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found"
        )

    existing = await EnrollmentService.get_user_enrollment(
        pg_db,
        current["id"],
        course.id
    )

    if existing:
        return {
            "status": "already_enrolled",
            "transaction_id": transaction.id
        }

    commission_amount = int(course.price * 0.10)
    creator_amount = int(course.price) - commission_amount

    await PaymentService.mark_paid(
        pg_db,
        transaction,
        provider_order_id=data.razorpay_order_id,
        provider_payment_id=data.razorpay_payment_id
    )

    creator_wallet = await WalletService.get_or_create_wallet(
        pg_db,
        course.owner_id,
        "creator"
    )

    await WalletService.credit_wallet(
        pg_db,
        creator_wallet,
        creator_amount,
        f"Course purchase: {course.title}"
    )

    enrollment = await EnrollmentService.create_enrollment(
        db=pg_db,
        user_id=current["id"],
        course_id=course.id,
        amount_paid=course.price,
        payment_transaction_id=transaction.id
    )

    await CourseService.increment_students(
        pg_db,
        course
    )

    return {
        "status": "paid",
        "transaction_id": transaction.id,
        "enrollment_id": enrollment.id,
        "course_id": course.id,
        "creator_amount": creator_amount,
        "commission_amount": commission_amount
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

    return {
        "ok": True,
        "transaction_id": transaction.id,
        "course_id": course_id,
        "amount": price,
        "commission_amount": commission_amount,
        "creator_amount": creator_amount
    }
