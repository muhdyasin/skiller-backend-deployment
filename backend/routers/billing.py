"""Subscription billing — trial + Skiller Pro plan + redemption-by-tokens.

Razorpay (live in test mode), Stripe (still mock until keys are added).
On a successful subscription, we:
  - extend `premium_until`
  - flip the user's `plan`
  - reward the referrer with REFERRAL_REWARD_TOKENS (one-shot per referral)
"""
import os
import hmac
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import razorpay

from core import (
    db, now, now_iso, get_current_user, get_user_by_id,
    is_premium_active, credit_tokens, debit_tokens, ensure_token_wallet,
    REFERRAL_REWARD_TOKENS, TRIAL_DAYS,
)

from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from services.payment_service import PaymentService
from services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger("skiller")

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
_rzp_client: Optional[razorpay.Client] = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    _rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# Single active plan during the "trial-only" phase. Others arrive with keys.
PLANS = {
    "trial_active": {
        "id": "trial_active",
        "name": "Skiller Trial Active",
        "price_inr": 299,
        "duration_days": 30,
        "perks": [
            "All premium tools unlocked",
            "Unlimited AI skill recommendations",
            "Run unlimited ads",
            "Full insights & CRM",
            "Priority support",
        ],
        "active": True,
    },
    "pro_quarterly": {
        "id": "pro_quarterly", "name": "Skiller Pro · Quarterly",
        "price_inr": 799, "duration_days": 90,
        "perks": ["3 months · save 11%"],
        "active": False, "coming_soon": True,
    },
    "pro_yearly": {
        "id": "pro_yearly", "name": "Skiller Pro · Yearly",
        "price_inr": 2499, "duration_days": 365,
        "perks": ["12 months · save 30% · bonus 250 tokens"],
        "active": False, "coming_soon": True,
    },
}


class CheckoutIn(BaseModel):
    plan_id: str
    pay_with: Literal["razorpay", "stripe", "tokens"] = "razorpay"


class VerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ---------- helpers ----------
def _parse_until(until) -> Optional[datetime]:
    if not until:
        return None
    try:
        if isinstance(until, str):
            d = datetime.fromisoformat(until)
        else:
            d = until
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except (ValueError, TypeError):
        return None


async def _extend_premium_and_reward(user_id: str, plan: dict, provider: str,
                                     payment_id: str = "", order_id: str = "") -> str:
    """Common post-payment effects: extend premium_until, set plan,
    record subscription_events row, and reward referrer one-shot."""
    user = await db.users.find_one(
        {"id": user_id}, {"_id": 0, "premium_until": 1, "referred_by": 1},
    )
    base = now()
    cur_until = _parse_until(user.get("premium_until")) if user else None
    if cur_until and cur_until > base:
        base = cur_until
    new_until = base + timedelta(days=plan["duration_days"])
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"premium_until": new_until.isoformat(), "plan": "pro"}},
    )
    await db.subscription_events.insert_one({
        "user_id": user_id,
        "plan_id": plan["id"],
        "provider": provider,
        "status": "paid",
        "amount_inr": plan["price_inr"],
        "payment_id": payment_id,
        "order_id": order_id,
        "created_at": now_iso(),
    })

    referrer_id = (user or {}).get("referred_by")
    if referrer_id:
        rec = await db.referrals.find_one({
            "referrer_id": referrer_id,
            "referred_user_id": user_id,
            "status": "pending",
        })
        if rec:
            await db.referrals.update_one(
                {"id": rec["id"]},
                {"$set": {"status": "rewarded", "rewarded_at": now_iso()}},
            )
            await credit_tokens(
                referrer_id, REFERRAL_REWARD_TOKENS, "referral",
                meta={"referred_user_id": user_id, "plan_id": plan["id"]},
            )
    return new_until.isoformat()


# ---------- public endpoints ----------
@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)):
    plans = await SubscriptionService.get_active_plans(db)

    return {
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "user_type": plan.user_type,
                "price": plan.price,
                "duration_days": plan.duration_days
            }
            for plan in plans
        ]
    }


@router.get("/me")
async def my_subscription(current=Depends(get_current_user)):
    user = await db.users.find_one({"id": current["id"]}, {"_id": 0, "premium_until": 1, "plan": 1})
    until = user.get("premium_until")
    days_left = 0
    parsed = _parse_until(until)
    if parsed:
        days_left = max(0, (parsed - now()).days)
    return {
        "plan": user.get("plan", "free"),
        "premium_until": until,
        "is_premium": is_premium_active(user),
        "days_left": days_left,
    }


@router.post("/checkout")
async def checkout(data: CheckoutIn, current=Depends(get_current_user), pg_db: AsyncSession = Depends(get_db)):
    plan = await SubscriptionService.get_plan(
    pg_db,
    data.plan_id
    )

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )

    if not plan.is_active:
        raise HTTPException(
            status_code=400,
            detail="Plan inactive"
        )

    # ---- Token-funded path (instant) ----
    if data.pay_with == "tokens":
        await debit_tokens(current["id"], plan.price, "subscription",
                           meta={"plan_id": plan.id})
        
        new_until = await _extend_premium_and_reward(
            current["id"],
            {
                "id": plan.id,
                "duration_days": plan.duration_days,
                "price_inr": plan.price
            },
            "tokens"
        )
        return {"provider": "tokens", "status": "paid", "new_until": new_until}

    # ---- Razorpay (live in test mode) ----
    if data.pay_with == "razorpay":
        if not _rzp_client:
            raise HTTPException(status_code=503,
                                detail="Razorpay not configured — please contact support")
        amount_paise = plan.price * 100
        # Receipt must be ≤ 40 chars
        receipt = f"sk_{plan.id[:12]}_{current['id'][:18]}"[:40]
        try:
            order = _rzp_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt,
                "payment_capture": 1,
                "notes": {
                    "plan_id": plan.id,
                    "user_id": current["id"],
                    "user_email": current.get("email", ""),
                },
            })
        except Exception as e:
            logger.exception("Razorpay order create failed")
            raise HTTPException(status_code=502, detail=f"Razorpay error: {e}")

        await PaymentService.create_razorpay_order_transaction(
            db=pg_db,
            payer_id=current["id"],
            amount=plan.price,
            plan_id=plan.id,
            order_id=order["id"]
        )

        return {
            "provider": "razorpay",
            "status": "order_created",
            "key_id": RAZORPAY_KEY_ID,
            "order_id": order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "plan_name": plan.name,
            "prefill": {
                "name": current.get("name", ""),
                "email": current.get("email", ""),
            },
            "notes": {"plan_id": plan.id},
        }

    # ---- Stripe (still mock until keys arrive) ----
    if data.pay_with == "stripe":
        await PaymentService.create_subscription_transaction(
            db=pg_db,
            payer_id=current["id"],
            plan_id=plan.id,
            amount=plan.price,
            payment_provider="stripe"
        )
        return {
            "provider": "stripe",
            "status": "mock",
            "message": "Stripe integration is being wired up — your trial stays active for now. Use Razorpay or pay with tokens to activate immediately.",
        }

    raise HTTPException(status_code=400, detail="Unknown payment provider")


@router.post("/verify-payment")
async def verify_payment(
    data: VerifyIn,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Razorpay not configured"
        )

    # Verify Razorpay signature
    body = (
        f"{data.razorpay_order_id}|"
        f"{data.razorpay_payment_id}"
    ).encode()

    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        expected,
        data.razorpay_signature
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid signature"
        )

    # Find transaction
    transaction = await PaymentService.get_transaction_by_order_id(
        pg_db,
        data.razorpay_order_id
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # Idempotency
    if transaction.status == "paid":
        return {
            "status": "already_paid",
            "transaction_id": transaction.id,
            "plan_id": transaction.plan_id
        }

    # Load plan
    plan = await SubscriptionService.get_plan(
        pg_db,
        transaction.plan_id
    )

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )

    # Load/Create subscription
    subscription = (
        await SubscriptionService.get_subscription_by_user(
            pg_db,
            current["id"]
        )
    )

    if not subscription:
        subscription = (
            await SubscriptionService.create_trial_subscription(
                pg_db,
                current["id"],
                current["role"]
            )
        )

    # Activate plan
    subscription = (
        await SubscriptionService.activate_plan(
            pg_db,
            subscription,
            plan
        )
    )

    # Mark payment successful
    transaction = await PaymentService.mark_paid(
        pg_db,
        transaction,
        provider_order_id=data.razorpay_order_id,
        provider_payment_id=data.razorpay_payment_id
    )

    # Keep legacy Mongo premium flow alive during migration
    await _extend_premium_and_reward(
        current["id"],
        {
            "id": plan.id,
            "duration_days": plan.duration_days,
            "price_inr": plan.price
        },
        "razorpay",
        payment_id=data.razorpay_payment_id,
        order_id=data.razorpay_order_id,
    )

    return {
        "status": "paid",
        "provider": "razorpay",
        "transaction_id": transaction.id,
        "subscription_id": subscription.id,
        "plan_id": plan.id,
        "starts_at": subscription.starts_at,
        "expires_at": subscription.expires_at
    }
