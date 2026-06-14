from sqlalchemy import select

from db.session import AsyncSessionLocal
from models.subscription_plan import SubscriptionPlan

CREATOR_MONTHLY = 499
CREATOR_YEARLY = 4999

INSTITUTION_MONTHLY = 999
INSTITUTION_YEARLY = 9999


async def seed_subscription_plans():

    async with AsyncSessionLocal() as db:

        plans = [
            {
                "name": "Creator Monthly",
                "user_type": "creator",
                "price": CREATOR_MONTHLY,
                "duration_days": 30
            },
            {
                "name": "Creator Yearly",
                "user_type": "creator",
                "price": CREATOR_YEARLY,
                "duration_days": 365
            },
            {
                "name": "Institution Monthly",
                "user_type": "institution",
                "price": INSTITUTION_MONTHLY,
                "duration_days": 30
            },
            {
                "name": "Institution Yearly",
                "user_type": "institution",
                "price": INSTITUTION_YEARLY,
                "duration_days": 365
            }
        ]

        for plan_data in plans:

            existing = await db.execute(
                select(SubscriptionPlan).where(
                    SubscriptionPlan.name == plan_data["name"]
                )
            )

            if existing.scalar_one_or_none():
                continue

            db.add(
                SubscriptionPlan(**plan_data)
            )

        await db.commit()