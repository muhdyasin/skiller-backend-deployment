"""Posts, comments, likes, plus reels + subscriptions feeds."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request

from core import (
    db, now_iso, get_current_user, maybe_current_user, award_xp, compute_level,
    PostCreate, CommentCreate,
)
from notifications_service import create_notification

router = APIRouter(prefix="/api/posts", tags=["posts"])


async def enrich_post(p: dict, viewer_id: Optional[str]) -> dict:
    author = await db.users.find_one(
        {"id": p["user_id"]},
        {"_id": 0, "id": 1, "username": 1, "name": 1, "avatar_url": 1, "xp": 1},
    )
    if author:
        author["level"] = compute_level(author.get("xp", 0))
    p["author"] = author
    p["like_count"] = len(p.get("likes", []))
    p["comment_count"] = len(p.get("comments", []))
    p["liked"] = bool(viewer_id and viewer_id in p.get("likes", []))
    return p


@router.post("")
async def create_post(data: PostCreate, current=Depends(get_current_user)):
    post = {
        "id": str(uuid.uuid4()), "user_id": current["id"],
        "caption": data.caption, "media": data.media, "media_type": data.media_type,
        "tags": data.tags, "likes": [], "comments": [], "created_at": now_iso(),
    }
    await db.posts.insert_one(post.copy())
    await award_xp(current["id"], "post_create")
    return await enrich_post(post, current["id"])


@router.get("/feed")
async def get_feed(request: Request, limit: int = 30):
    viewer = await maybe_current_user(request)
    posts = await db.posts.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    viewer_id = viewer["id"] if viewer else None
    return [await enrich_post(p, viewer_id) for p in posts]


@router.get("/explore")
async def explore(request: Request, limit: int = 60):
    viewer = await maybe_current_user(request)
    posts = await db.posts.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    viewer_id = viewer["id"] if viewer else None
    return [await enrich_post(p, viewer_id) for p in posts]


@router.get("/reels")
async def reels(request: Request, limit: int = 50):
    viewer = await maybe_current_user(request)
    posts = await db.posts.find(
        {"media_type": "video"}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    viewer_id = viewer["id"] if viewer else None
    return [await enrich_post(p, viewer_id) for p in posts]


@router.get("/subscriptions")
async def subscriptions(limit: int = 30, current=Depends(get_current_user)):
    following = current.get("following", [])
    if not following:
        return []
    posts = await db.posts.find(
        {"user_id": {"$in": following}}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return [await enrich_post(p, current["id"]) for p in posts]


@router.get("/{post_id}")
async def get_post(post_id: str, request: Request):
    p = await db.posts.find_one({"id": post_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    viewer = await maybe_current_user(request)
    return await enrich_post(p, viewer["id"] if viewer else None)


@router.post("/{post_id}/like")
async def toggle_like(post_id: str, current=Depends(get_current_user)):
    p = await db.posts.find_one({"id": post_id})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    if current["id"] in p.get("likes", []):
        await db.posts.update_one({"id": post_id}, {"$pull": {"likes": current["id"]}})
        liked = False
    else:
        await db.posts.update_one({"id": post_id}, {"$addToSet": {"likes": current["id"]}})
        liked = True
        await award_xp(current["id"], "like_given")
        await award_xp(p["user_id"], "like_received")
        await create_notification(p["user_id"], "like", f"@{current['username']} liked your post", actor_id=current["id"], meta={"post_id": post_id})
    p2 = await db.posts.find_one({"id": post_id}, {"_id": 0})
    return {"liked": liked, "like_count": len(p2.get("likes", []))}


@router.post("/{post_id}/comments")
async def add_comment(post_id: str, data: CommentCreate, current=Depends(get_current_user)):
    p = await db.posts.find_one({"id": post_id})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    comment = {
        "id": str(uuid.uuid4()), "user_id": current["id"], "username": current["username"],
        "name": current["name"], "avatar_url": current.get("avatar_url", ""),
        "text": data.text, "created_at": now_iso(),
    }
    await db.posts.update_one({"id": post_id}, {"$push": {"comments": comment}})
    await award_xp(current["id"], "comment_given")
    await award_xp(p["user_id"], "comment_received")
    await create_notification(p["user_id"], "comment", f"@{current['username']} commented on your post", actor_id=current["id"], meta={"post_id": post_id})
    return comment


@router.get("/{post_id}/comments")
async def list_comments(post_id: str):
    p = await db.posts.find_one({"id": post_id}, {"_id": 0, "comments": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    return p.get("comments", [])


@router.delete("/{post_id}")
async def delete_post(post_id: str, current=Depends(get_current_user)):
    p = await db.posts.find_one({"id": post_id})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    if p["user_id"] != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.posts.delete_one({"id": post_id})
    return {"ok": True}
