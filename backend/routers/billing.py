"""Subscription billing — trial + Skiller Pro plan + redemption-by-tokens.

Mock checkout for now: real Razorpay/Stripe wires up once user gives keys.
On a successful subscription, we:
  - extend `premium_until`
  - flip the user's `plan`
  - reward the referrer with REFERRAL_REWARD_TOKENS (one-shot per referral)
"""
from datetime import timedelta
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import (
    db, now, now_iso, get_current_user, get_user_by_id,
    is_premium_active, credit_tokens, debit_tokens, ensure_token_wallet,
    REFERRAL_REWARD_TOKENS, TRIAL_DAYS,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])

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
    # Locked previews — visible in UI but not purchasable yet
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
    if until:
        try:
            from datetime import datetime, timezone
            d = datetime.fromisoformat(until) if isinstance(until, str) else until
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            days_left = max(0, (d - now()).days)
        except Exception:
            days_left = 0
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

    if data.pay_with == "tokens":
        # 1 token = ₹1
        await debit_tokens(current["id"], plan["price_inr"], "subscription",
                           meta={"plan_id": plan["id"]})
        provider_payload = {"provider": "tokens", "status": "paid"}
    else:
        # Razorpay/Stripe not wired yet — return a mock acceptance so the UX flows end-to-end.
        # The frontend will pop a "Coming soon" state if it sees status=mock.
        provider_payload = {
            "provider": data.pay_with,
            "status": "mock",
            "message": (
                f"{data.pay_with.title()} integration is being wired up — "
                "your trial stays active for now. Subscribe via tokens to activate immediately."
            ),
        }
        # Don't extend premium_until on mock — but record the attempt
        await db.subscription_events.insert_one({
            "user_id": current["id"],
            "plan_id": plan["id"],
            "provider": data.pay_with,
            "status": "mock",
            "amount_inr": plan["price_inr"],
            "created_at": now_iso(),
        })
        return provider_payload

    # Token-paid path — extend premium and reward referrer
    user = await db.users.find_one({"id": current["id"]}, {"_id": 0, "premium_until": 1, "referred_by": 1})
    base = now()
    try:
        from datetime import datetime, timezone
        cur_until = user.get("premium_until")
        if cur_until:
            d = datetime.fromisoformat(cur_until) if isinstance(cur_until, str) else cur_until
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            if d > base:
                base = d
    except Exception:
        pass
    new_until = base + timedelta(days=plan["duration_days"])
    await db.users.update_one(
        {"id": current["id"]},
        {"$set": {"premium_until": new_until.isoformat(), "plan": "pro"}},
    )
    await db.subscription_events.insert_one({
        "user_id": current["id"],
        "plan_id": plan["id"],
        "provider": "tokens",
        "status": "paid",
        "amount_inr": plan["price_inr"],
        "created_at": now_iso(),
    })

    # Reward referrer (one-shot per referral)
    referrer_id = user.get("referred_by")
    if referrer_id:
        rec = await db.referrals.find_one({
            "referrer_id": referrer_id,
            "referred_user_id": current["id"],
            "status": "pending",
        })
        if rec:
            await db.referrals.update_one(
                {"id": rec["id"]},
                {"$set": {"status": "rewarded", "rewarded_at": now_iso()}},
            )
            await credit_tokens(
                referrer_id, REFERRAL_REWARD_TOKENS, "referral",
                meta={"referred_user_id": current["id"], "plan_id": plan["id"]},
            )

    provider_payload["new_until"] = new_until.isoformat()
    return provider_payload
