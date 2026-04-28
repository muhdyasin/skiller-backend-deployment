"""Users + XP + leaderboard."""
from fastapi import APIRouter, HTTPException, Depends, Request
from core import (
    db, get_current_user, get_user_by_id, maybe_current_user, award_xp,
    compute_level, BADGE_DEFS, ProfileUpdate,
)
from notifications_service import create_notification

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users/{username}")
async def get_user_profile(username: str, request: Request):
    user = await db.users.find_one({"username": username.lower()}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    posts = await db.posts.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    viewer = await maybe_current_user(request)
    is_following = bool(viewer and viewer["id"] in user.get("followers", []))
    return {
        "user": user, "posts": posts, "post_count": len(posts),
        "follower_count": len(user.get("followers", [])),
        "following_count": len(user.get("following", [])),
        "is_following": is_following,
        "is_self": bool(viewer and viewer["id"] == user["id"]),
        "level": compute_level(user.get("xp", 0)),
        "badges": [b for b in BADGE_DEFS if b["key"] in user.get("badges", [])],
    }


@router.post("/users/{user_id}/follow")
async def follow_user(user_id: str, current=Depends(get_current_user)):
    if user_id == current["id"]:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    is_following = current["id"] in target.get("followers", [])
    if is_following:
        await db.users.update_one({"id": user_id}, {"$pull": {"followers": current["id"]}})
        await db.users.update_one({"id": current["id"]}, {"$pull": {"following": user_id}})
        return {"following": False}
    await db.users.update_one({"id": user_id}, {"$addToSet": {"followers": current["id"]}})
    await db.users.update_one({"id": current["id"]}, {"$addToSet": {"following": user_id}})
    await award_xp(current["id"], "follow_given")
    await award_xp(user_id, "follow_received")
    await create_notification(user_id, "follow", f"@{current['username']} started following you", actor_id=current["id"])
    return {"following": True}


@router.patch("/users/me")
async def update_profile(data: ProfileUpdate, current=Depends(get_current_user)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": current["id"]}, {"$set": updates})
    return await get_user_by_id(current["id"])


@router.get("/users")
async def list_users(limit: int = 20):
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).limit(limit).to_list(limit)


@router.get("/users/me/xp")
async def my_xp(current=Depends(get_current_user)):
    user = await db.users.find_one({"id": current["id"]})
    xp = user.get("xp", 0)
    earned = user.get("badges", [])
    return {
        "xp": xp,
        "level": compute_level(xp),
        "streak": user.get("streak", 0),
        "earned_badges": [b for b in BADGE_DEFS if b["key"] in earned],
        "all_badges": BADGE_DEFS,
        "recent_events": await db.xp_events.find({"user_id": current["id"]}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20),
    }


@router.get("/leaderboard")
async def leaderboard(limit: int = 20):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("xp", -1).limit(limit).to_list(limit)
    return [{
        "id": u["id"], "username": u["username"], "name": u["name"],
        "avatar_url": u.get("avatar_url", ""), "xp": u.get("xp", 0),
        "level": compute_level(u.get("xp", 0)),
        "badge_count": len(u.get("badges", [])),
    } for u in users]
