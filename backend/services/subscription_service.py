from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.subscription import Subscription
from models.subscription_plan import SubscriptionPlan


class SubscriptionService:

    @staticmethod
    async def get_subscription_by_user(
        db: AsyncSession,
        user_id: str
    ):
        result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create_trial_subscription(
        db: AsyncSession,
        user_id: str,
        user_type: str
    ):
        existing = await SubscriptionService.get_subscription_by_user(
            db,
            user_id
        )

        if existing:
            return existing

        start_date = datetime.utcnow()
        expiry_date = start_date + timedelta(days=30)

        subscription = Subscription(
            user_id=user_id,
            user_type=user_type,
            plan_id="trial",
            status="trial",
            starts_at=start_date,
            expires_at=expiry_date
        )

        db.add(subscription)

        await db.commit()
        await db.refresh(subscription)

        return subscription

    @staticmethod
    async def activate_plan(
        db: AsyncSession,
        subscription: Subscription,
        plan: SubscriptionPlan,
        payment_provider: str = None
    ):
        
        if payment_provider:
            subscription.payment_provider = payment_provider
            
        now = datetime.utcnow()

        subscription.plan_id = plan.id
        subscription.status = "active"

        if (
            subscription.expires_at
            and subscription.expires_at > now
        ):
            # extend active subscription
            subscription.expires_at += timedelta(
                days=plan.duration_days
            )
        else:
            # activate fresh subscription
            subscription.starts_at = now
            subscription.expires_at = (
                now + timedelta(days=plan.duration_days)
            )

        await db.commit()
        await db.refresh(subscription)

        return subscription

    @staticmethod
    async def expire_subscription(
        db: AsyncSession,
        subscription: Subscription
    ):
        subscription.status = "expired"

        await db.commit()

        return subscription

    @staticmethod
    def is_subscription_active(
        subscription: Subscription
    ) -> bool:

        return (
            subscription.status in ["trial", "active"]
            and subscription.expires_at > datetime.utcnow()
        )
        
    @staticmethod
    async def get_plan(
    db: AsyncSession,
    plan_id: str
    ):
        result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.id == plan_id)
        )

        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_active_plans(
    db: AsyncSession
    ):
        result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active == True)
        )

        return result.scalars().all()
    
