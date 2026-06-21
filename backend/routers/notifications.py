"""In-app notifications endpoints."""
from fastapi import APIRouter, Depends
from core import db, get_current_user

from db.session import AsyncSessionLocal
from services.user_service import UserService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


async def enrich(n: dict) -> dict:
    if n.get("actor_id"):

        async with AsyncSessionLocal() as pg_db:

            user = await UserService.get_user(
                pg_db,
                n["actor_id"]
            )

            if user:
                n["actor"] = {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "avatar_url": user.avatar_url,
                }
            else:
                n["actor"] = None

    return n


@router.get("")
async def list_notifications(current=Depends(get_current_user), limit: int = 30):
    items = await db.notifications.find({"user_id": current["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [await enrich(n) for n in items]


@router.get("/unread-count")
async def unread_count(current=Depends(get_current_user)):
    n = await db.notifications.count_documents({"user_id": current["id"], "read": False})
    return {"count": n}


@router.post("/read-all")
async def read_all(current=Depends(get_current_user)):
    await db.notifications.update_many({"user_id": current["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}


@router.post("/{nid}/read")
async def read_one(nid: str, current=Depends(get_current_user)):
    await db.notifications.update_one({"id": nid, "user_id": current["id"]}, {"$set": {"read": True}})
    return {"ok": True}
