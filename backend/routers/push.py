"""Web Push subscriptions."""
import uuid
from fastapi import APIRouter, Depends
from core import db, now_iso, get_current_user, PushSubscribeIn, PushUnsubscribeIn
from notifications_service import get_vapid_public_key

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-public-key")
async def vapid_public_key():
    return {"public_key": get_vapid_public_key()}


@router.post("/subscribe")
async def subscribe(data: PushSubscribeIn, current=Depends(get_current_user)):
    sub = data.subscription or {}
    endpoint = sub.get("endpoint")
    if not endpoint:
        return {"ok": False, "detail": "Invalid subscription"}
    existing = await db.push_subscriptions.find_one({"subscription.endpoint": endpoint})
    if existing:
        await db.push_subscriptions.update_one(
            {"subscription.endpoint": endpoint},
            {"$set": {"user_id": current["id"], "subscription": sub, "active": True}},
        )
    else:
        await db.push_subscriptions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current["id"],
            "subscription": sub,
            "active": True,
            "created_at": now_iso(),
        })
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(data: PushUnsubscribeIn, current=Depends(get_current_user)):
    await db.push_subscriptions.update_one(
        {"subscription.endpoint": data.endpoint, "user_id": current["id"]},
        {"$set": {"active": False}},
    )
    return {"ok": True}
