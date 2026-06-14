from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db

from models.subscription_plan import SubscriptionPlan
from models.subscription import Subscription

from services.subscription_service import SubscriptionService

from pydantic import BaseModel

from typing import Literal

class TrialRequest(BaseModel):
    user_id: str
    user_type: Literal["creator", "institution"]

router = APIRouter(
    prefix="/api/subscriptions",
    tags=["Subscriptions"]
)

@router.get("/plans")
async def get_plans(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SubscriptionPlan)
    )

    plans = result.scalars().all()

    return plans

@router.post("/start-trial")
async def start_trial(
    data: TrialRequest,
    db: AsyncSession = Depends(get_db)
):
    subscription = (
        await SubscriptionService
        .create_trial_subscription(
            db,
            data.user_id,
            data.user_type
        )
    )

    return subscription

@router.get("/{user_id}")
async def get_subscription(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    subscription = (
        await SubscriptionService
        .get_subscription_by_user(
            db,
            user_id
        )
    )

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    return {
        "subscription": subscription,
        "is_active": SubscriptionService.is_subscription_active(
            subscription
        )
    }

