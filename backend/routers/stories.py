"""Stories — Instagram-style. Auto-expire 24h via Mongo TTL index."""
import uuid
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from core import db, now, now_iso, get_current_user

from db.session import AsyncSessionLocal
from services.user_service import UserService

router = APIRouter(prefix="/api/stories", tags=["stories"])

STORY_TTL_HOURS = 24


class StoryCreate(BaseModel):
    media: str
    media_type: str = "image"  # image | video
    caption: str = ""

    @field_validator("media")
    @classmethod
    def _validate_media(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("media required")
        if v.startswith("/api/files/") or v.startswith("https://") or v.startswith("http://"):
            return v
        raise ValueError("media must be an https URL or /api/files/ path")

    @field_validator("media_type")
    @classmethod
    def _validate_mt(cls, v: str) -> str:
        v = (v or "image").lower().strip()
        if v not in {"image", "video"}:
            raise ValueError("media_type must be image or video")
        return v


@router.post("")
async def create_story(data: StoryCreate, current=Depends(get_current_user)):
    expires_dt = now() + timedelta(hours=STORY_TTL_HOURS)
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": current["id"],
        "media": data.media,
        "media_type": data.media_type,
        "caption": data.caption.strip()[:280],
        "created_at": now_iso(),
        "expires_at_dt": expires_dt,  # TTL index
        "viewers": [],
    }
    await db.stories.insert_one(doc)
    return await _enrich_story(doc, current["id"])


@router.get("/feed")
async def stories_feed(current=Depends(get_current_user)):
    """Returns stories from people I follow + my own, grouped by user."""
    
    async with AsyncSessionLocal() as pg_db:

        user = await UserService.get_user(
            pg_db,
            current["id"]
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        following_ids = await UserService.get_following_ids(
            pg_db,
            current["id"]
        )

    user_ids = list(
        set(
            following_ids +
            [current["id"]]
        )
    )
    
    cursor = db.stories.find(
        {"user_id": {"$in": user_ids}, "expires_at_dt": {"$gt": now()}},
        {"_id": 0},
    ).sort("created_at", 1)
    raw = await cursor.to_list(500)

    # Group by user
    by_user = {}
    
    async with AsyncSessionLocal() as pg_db:

        users = await UserService.get_users_by_ids(
            pg_db,
            user_ids
        )

    meta_by_id = {
        u.id: {
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "avatar_url": u.avatar_url,
        }
        for u in users
    }
    

    for s in raw:
        if s["user_id"] not in by_user:
            by_user[s["user_id"]] = {
                "user": meta_by_id.get(s["user_id"]),
                "stories": [],
                "has_unviewed": False,
            }
        s_clean = {k: v for k, v in s.items() if k != "expires_at_dt"}
        s_clean["expires_at"] = s["expires_at_dt"].isoformat() if s.get("expires_at_dt") else None
        s_clean["viewed_by_me"] = current["id"] in s.get("viewers", [])
        if not s_clean["viewed_by_me"] and s["user_id"] != current["id"]:
            by_user[s["user_id"]]["has_unviewed"] = True
        by_user[s["user_id"]]["stories"].append(s_clean)

    # Order: self first, then unviewed, then viewed
    ordered = []
    if current["id"] in by_user:
        ordered.append(by_user.pop(current["id"]))
    unviewed = [g for g in by_user.values() if g["has_unviewed"]]
    viewed = [g for g in by_user.values() if not g["has_unviewed"]]
    ordered.extend(unviewed + viewed)
    return ordered


@router.get("/u/{username}")
async def user_stories(username: str, current=Depends(get_current_user)):
    
    async with AsyncSessionLocal() as pg_db:

        user_obj = await UserService.get_user_by_username(
            pg_db,
            username.lower()
        )

    if not user_obj:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user = {
        "id": user_obj.id,
        "username": user_obj.username,
        "name": user_obj.name,
        "avatar_url": user_obj.avatar_url,
    }
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    cursor = db.stories.find(
        {"user_id": user["id"], "expires_at_dt": {"$gt": now()}},
        {"_id": 0},
    ).sort("created_at", 1)
    raw = await cursor.to_list(50)
    out = []
    for s in raw:
        c = {k: v for k, v in s.items() if k != "expires_at_dt"}
        c["expires_at"] = s["expires_at_dt"].isoformat() if s.get("expires_at_dt") else None
        c["viewed_by_me"] = current["id"] in s.get("viewers", [])
        out.append(c)
    return {"user": user, "stories": out}


@router.post("/{story_id}/view")
async def view_story(story_id: str, current=Depends(get_current_user)):
    res = await db.stories.update_one(
        {"id": story_id},
        {"$addToSet": {"viewers": current["id"]}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Story not found or expired")
    return {"ok": True}


@router.delete("/{story_id}")
async def delete_story(story_id: str, current=Depends(get_current_user)):
    res = await db.stories.delete_one({"id": story_id, "user_id": current["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"ok": True}


async def _enrich_story(doc: dict, viewer_id: str) -> dict:
    out = {k: v for k, v in doc.items() if k not in {"_id", "expires_at_dt"}}
    out["expires_at"] = doc["expires_at_dt"].isoformat() if doc.get("expires_at_dt") else None
    out["viewed_by_me"] = viewer_id in doc.get("viewers", [])
    return out
