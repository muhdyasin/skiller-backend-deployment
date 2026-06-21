"""Users + XP + leaderboard."""
from fastapi import APIRouter, HTTPException, Depends, Request
from core import (
    db, get_current_user, get_user_by_id, maybe_current_user, award_xp,
    compute_level, BADGE_DEFS, ProfileUpdate, RoleUpgradeIn,
)
from notifications_service import create_notification

from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from services.user_service import UserService
from services.user_follow_service import UserFollowService

router = APIRouter(prefix="/api", tags=["users"])



@router.get("/c/{username}")
async def creator_storefront(username: str, request: Request):
    """Public, SEO-friendly creator storefront — courses + gigs + reels +
    latest posts in one payload. Open to anonymous visitors."""
    user = await db.users.find_one(
        {"username": username.lower()},
        {"_id": 0, "password_hash": 0},
    )
    if not user:
        raise HTTPException(status_code=404, detail="Creator not found")
    if user.get("role") not in ("creator", "admin"):
        raise HTTPException(status_code=404, detail="Not a creator")

    courses = await db.courses.find(
        {"owner_id": user["id"]}, {"_id": 0},
    ).sort("created_at", -1).to_list(50)
    for c in courses:
        c["enrollments"] = await db.enrollments.count_documents({"course_id": c["id"]})

    gigs = await db.gigs.find(
        {"owner_id": user["id"]}, {"_id": 0},
    ).sort("created_at", -1).to_list(50)

    reels = await db.posts.find(
        {"user_id": user["id"], "media_type": "video"}, {"_id": 0},
    ).sort("created_at", -1).to_list(12)
    posts = await db.posts.find(
        {"user_id": user["id"], "media_type": {"$ne": "video"}}, {"_id": 0},
    ).sort("created_at", -1).to_list(12)

    viewer = await maybe_current_user(request)
    is_following = bool(viewer and viewer["id"] in user.get("followers", []))

    return {
        "user": {
            "id": user["id"], "username": user["username"], "name": user["name"],
            "bio": user.get("bio", ""), "avatar_url": user.get("avatar_url", ""),
            "role": user.get("role"),
        },
        "stats": {
            "followers": len(user.get("followers", [])),
            "following": len(user.get("following", [])),
            "courses": len(courses),
            "gigs": len(gigs),
            "posts": len(posts) + len(reels),
        },
        "level": compute_level(user.get("xp", 0)),
        "badges": [b for b in BADGE_DEFS if b["key"] in user.get("badges", [])],
        "courses": courses,
        "gigs": gigs,
        "reels": reels,
        "posts": posts,
        "is_following": is_following,
        "is_self": bool(viewer and viewer["id"] == user["id"]),
    }



@router.post("/users/{user_id}/follow")
async def follow_user(
    user_id: str,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    if user_id == current["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot follow yourself"
        )

    target = await UserService.get_user(
        pg_db,
        user_id
    )

    if not target:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    existing_follow = (
        await UserFollowService.get_follow(
            pg_db,
            current["id"],
            user_id
        )
    )

    # Unfollow
    if existing_follow:

        await UserFollowService.delete_follow(
            pg_db,
            existing_follow
        )

        return {
            "following": False
        }

    # Follow
    await UserFollowService.create_follow(
        pg_db,
        current["id"],
        user_id
    )

    await award_xp(
        current["id"],
        "follow_given"
    )

    await award_xp(
        user_id,
        "follow_received"
    )

    await create_notification(
        user_id,
        "follow",
        f"@{current['username']} started following you",
        actor_id=current["id"]
    )

    return {
        "following": True
    }

@router.patch("/users/me")
async def update_profile(
    data: ProfileUpdate,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    user = await UserService.get_user(
        pg_db,
        current["id"]
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    updates = {
        k: v
        for k, v in data.model_dump().items()
        if v is not None
    }

    user = await UserService.update_user(
        pg_db,
        user,
        updates
    )

    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "bio": user.bio,
        "avatar_url": user.avatar_url
    }


@router.post("/users/me/upgrade-role")
async def upgrade_role(data: RoleUpgradeIn, current=Depends(get_current_user)):
    if current.get("role") == "admin":
        return await get_user_by_id(current["id"])
    await db.users.update_one({"id": current["id"]}, {"$set": {"role": data.role}})
    return await get_user_by_id(current["id"])


@router.get("")
async def list_users(pg_db: AsyncSession = Depends(get_db)):
    users = await UserService.get_all_users(
        pg_db
    )

    return [
        {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "xp": user.xp
        }
        for user in users
    ]

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


@router.get("/users/me/enrollments")
async def my_enrollments(current=Depends(get_current_user)):
    enrolls = await db.enrollments.find({"user_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    course_ids = [e["course_id"] for e in enrolls]
    courses = await db.courses.find({"id": {"$in": course_ids}}, {"_id": 0}).to_list(200)
    course_map = {c["id"]: c for c in courses}
    return [course_map[cid] for cid in course_ids if cid in course_map]


@router.get("/users/me/applications")
async def my_applications(current=Depends(get_current_user)):
    apps = await db.applications.find({"user_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    gig_ids = [a["gig_id"] for a in apps]
    gigs = await db.gigs.find({"id": {"$in": gig_ids}}, {"_id": 0}).to_list(200)
    gig_map = {g["id"]: g for g in gigs}
    return [{**a, "gig": gig_map.get(a["gig_id"])} for a in apps]


@router.get("/leaderboard")
async def leaderboard(limit: int = 20):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("xp", -1).limit(limit).to_list(limit)
    return [{
        "id": u["id"], "username": u["username"], "name": u["name"],
        "avatar_url": u.get("avatar_url", ""), "xp": u.get("xp", 0),
        "level": compute_level(u.get("xp", 0)),
        "badge_count": len(u.get("badges", [])),
    } for u in users]
    

@router.get("/users/{username}")
async def get_profile(
    username: str,
    pg_db: AsyncSession = Depends(get_db)
):
    user = await UserService.get_user_by_username(
        pg_db,
        username
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "xp": user.xp,
        "badges": user.badges,
        "streak": user.streak,
        "created_at": user.created_at
    }
