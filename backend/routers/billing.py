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
async def list_plans():
    return {
        "plans": list(PLANS.values()),
        "trial_days": TRIAL_DAYS,
        "referral_reward_tokens": REFERRAL_REWARD_TOKENS,
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
async def checkout(data: CheckoutIn, current=Depends(get_current_user)):
    plan = PLANS.get(data.plan_id)
    if not plan or not plan.get("active"):
        raise HTTPException(status_code=400, detail="Plan not available yet")

    # ---- Token-funded path (instant) ----
    if data.pay_with == "tokens":
        await debit_tokens(current["id"], plan["price_inr"], "subscription",
                           meta={"plan_id": plan["id"]})
        new_until = await _extend_premium_and_reward(current["id"], plan, "tokens")
        return {"provider": "tokens", "status": "paid", "new_until": new_until}

    # ---- Razorpay (live in test mode) ----
    if data.pay_with == "razorpay":
        if not _rzp_client:
            raise HTTPException(status_code=503,
                                detail="Razorpay not configured — please contact support")
        amount_paise = plan["price_inr"] * 100
        # Receipt must be ≤ 40 chars
        receipt = f"sk_{plan['id'][:12]}_{current['id'][:18]}"[:40]
        try:
            order = _rzp_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt,
                "payment_capture": 1,
                "notes": {
                    "plan_id": plan["id"],
                    "user_id": current["id"],
                    "user_email": current.get("email", ""),
                },
            })
        except Exception as e:
            logger.exception("Razorpay order create failed")
            raise HTTPException(status_code=502, detail=f"Razorpay error: {e}")

        await db.subscription_events.insert_one({
            "user_id": current["id"],
            "plan_id": plan["id"],
            "provider": "razorpay",
            "status": "created",
            "amount_inr": plan["price_inr"],
            "order_id": order["id"],
            "created_at": now_iso(),
        })

        return {
            "provider": "razorpay",
            "status": "order_created",
            "key_id": RAZORPAY_KEY_ID,
            "order_id": order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "plan_name": plan["name"],
            "prefill": {
                "name": current.get("name", ""),
                "email": current.get("email", ""),
            },
            "notes": {"plan_id": plan["id"]},
        }

    # ---- Stripe (still mock until keys arrive) ----
    if data.pay_with == "stripe":
        await db.subscription_events.insert_one({
            "user_id": current["id"],
            "plan_id": plan["id"],
            "provider": "stripe",
            "status": "mock",
            "amount_inr": plan["price_inr"],
            "created_at": now_iso(),
        })
        return {
            "provider": "stripe",
            "status": "mock",
            "message": "Stripe integration is being wired up — your trial stays active for now. Use Razorpay or pay with tokens to activate immediately.",
        }

    raise HTTPException(status_code=400, detail="Unknown payment provider")


@router.post("/verify-payment")
async def verify_payment(data: VerifyIn, current=Depends(get_current_user)):
    """Verify Razorpay HMAC signature server-side, then upgrade plan."""
    if not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay not configured")

    # Verify signature: HMAC-SHA256(order_id|payment_id, secret) == signature
    body = f"{data.razorpay_order_id}|{data.razorpay_payment_id}".encode()
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, data.razorpay_signature):
        await db.subscription_events.update_one(
            {"order_id": data.razorpay_order_id, "user_id": current["id"]},
            {"$set": {"status": "signature_failed", "verified_at": now_iso()}},
        )
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Look up the order in our log to find the plan
    evt = await db.subscription_events.find_one(
        {"order_id": data.razorpay_order_id, "user_id": current["id"]},
        sort=[("created_at", -1)],
    )
    if not evt:
        raise HTTPException(status_code=404, detail="Order not found for this user")
    if evt.get("status") == "paid":
        # Already processed — idempotent
        u = await db.users.find_one({"id": current["id"]}, {"_id": 0, "premium_until": 1})
        return {"status": "already_paid", "new_until": u.get("premium_until")}

    plan = PLANS.get(evt["plan_id"])
    if not plan:
        raise HTTPException(status_code=400, detail="Plan vanished")

    new_until = await _extend_premium_and_reward(
        current["id"], plan, "razorpay",
        payment_id=data.razorpay_payment_id, order_id=data.razorpay_order_id,
    )
    return {
        "status": "paid",
        "provider": "razorpay",
        "new_until": new_until,
        "plan_id": plan["id"],
    }
