"""Skill-Token wallet + ledger + redemption + referral status."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import (
    db, now_iso, get_current_user, ensure_token_wallet,
    debit_tokens, REFERRAL_REWARD_TOKENS,
)

from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from services.user_service import UserService

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


class RedeemIn(BaseModel):
    amount: int = Field(gt=0)
    purpose: Literal["course", "ads", "ai_credits"]
    target_id: Optional[str] = None  # course_id / ad_id


@router.get("/me")
async def my_wallet(current=Depends(get_current_user),
                    pg_db: AsyncSession = Depends(get_db)):
    await ensure_token_wallet(current["id"])
    wallet = await db.token_wallets.find_one({"user_id": current["id"]}, {"_id": 0})
    ledger = await db.token_ledger.find(
        {"user_id": current["id"]}, {"_id": 0},
    ).sort("created_at", -1).limit(30).to_list(30)

    user = await UserService.get_user(
        pg_db,
        current["id"]
    )
    referrals = await db.referrals.find(
        {"referrer_id": current["id"]}, {"_id": 0},
    ).sort("created_at", -1).limit(50).to_list(50)
    rewarded_count = sum(1 for r in referrals if r.get("status") == "rewarded")
    pending_count = sum(1 for r in referrals if r.get("status") == "pending")

    # enrich referrals with referee usernames
    referee_ids = [r["referred_user_id"] for r in referrals]
    users = await UserService.get_users_by_ids(
        pg_db,
        referee_ids
    )
    by_id = {
        u.id: {
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "avatar_url": u.avatar_url,
        }
        for u in users
    }
    
    for r in referrals:
        r["referred"] = by_id.get(r["referred_user_id"])

    return {
        "wallet": wallet or {"balance": 0, "lifetime_earned": 0, "lifetime_spent": 0},
        "ledger": ledger,
        "referral_code": user.referral_code,
        "reward_per_referral": REFERRAL_REWARD_TOKENS,
        "referrals": referrals,
        "stats": {
            "total": len(referrals),
            "rewarded": rewarded_count,
            "pending": pending_count,
        },
    }


@router.post("/redeem")
async def redeem(data: RedeemIn, current=Depends(get_current_user)):
    """Spend tokens against a course / ad / AI credits.

    Subscription redemption uses /api/billing/checkout with pay_with=tokens.
    """
    if data.purpose == "course":
        if not data.target_id:
            raise HTTPException(status_code=400, detail="target_id (course) required")
        course = await db.courses.find_one({"id": data.target_id}, {"_id": 0, "id": 1, "price": 1})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        if data.amount < course.get("price", 0):
            raise HTTPException(status_code=400, detail="Amount less than course price")
        balance = await debit_tokens(current["id"], data.amount, "course",
                                     meta={"course_id": course["id"]})
        # auto-enroll
        existing = await db.enrollments.find_one(
            {"user_id": current["id"], "course_id": course["id"]}
        )
        if not existing:
            from uuid import uuid4
            await db.enrollments.insert_one({
                "id": str(uuid4()),
                "user_id": current["id"],
                "course_id": course["id"],
                "paid_with": "tokens",
                "amount": data.amount,
                "created_at": now_iso(),
            })
        return {"balance": balance, "purpose": "course", "course_id": course["id"]}

    if data.purpose == "ads":
        balance = await debit_tokens(current["id"], data.amount, "ads",
                                     meta={"campaign_id": data.target_id})
        return {"balance": balance, "purpose": "ads", "credit": data.amount}

    if data.purpose == "ai_credits":
        raise HTTPException(
            status_code=501,
            detail="AI credits feature not implemented"
        )
    raise HTTPException(status_code=400, detail="Unknown purpose")


@router.get("/referral-link")
async def referral_link(current=Depends(get_current_user),
                        pg_db: AsyncSession = Depends(get_db)):
    user = await UserService.get_user(
        pg_db,
        current["id"]
    )    
    return {"code": user.referral_code}
