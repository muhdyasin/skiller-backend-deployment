"""Search across users, posts, courses, gigs."""
import re
from fastapi import APIRouter, HTTPException, Query
from core import db, compute_level

router = APIRouter(prefix="/api/search", tags=["search"])


def _re(q: str):
    return {"$regex": re.escape(q), "$options": "i"}


@router.get("")
async def search(q: str = Query(..., min_length=1), limit: int = 8):
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query required")

    users = await db.users.find(
        {
            "$or": [
                {"username": _re(q)},
                {"name": _re(q)},
                {"bio": _re(q)},
            ]
        },
        {"_id": 0, "password_hash": 0, "followers": 0, "following": 0},
    ).limit(limit).to_list(limit)

    for u in users:
        u["level"] = compute_level(u.get("xp", 0))

    posts = await db.posts.find(
        {
            "$or": [
                {"caption": _re(q)},
                {"tags": {"$in": [re.compile(re.escape(q), re.I)]}},
            ]
        },
        {"_id": 0, "likes": 0, "comments": 0},
    ).sort("created_at", -1).limit(limit).to_list(limit)

    # attach minimal author for each post
    for p in posts:
        a = await db.users.find_one(
            {"id": p["user_id"]},
            {"_id": 0, "id": 1, "username": 1, "name": 1, "avatar_url": 1},
        )
        p["author"] = a

    courses = await db.courses.find(
        {
            "$or": [
                {"title": _re(q)},
                {"description": _re(q)},
                {"category": _re(q)},
                {"instructor": _re(q)},
            ]
        },
        {"_id": 0},
    ).limit(limit).to_list(limit)

    gigs = await db.gigs.find(
        {
            "$or": [
                {"title": _re(q)},
                {"description": _re(q)},
                {"category": _re(q)},
                {"skills": _re(q)},
            ]
        },
        {"_id": 0},
    ).limit(limit).to_list(limit)

    return {
        "q": q,
        "users": users,
        "posts": posts,
        "courses": courses,
        "gigs": gigs,
        "counts": {
            "users": len(users),
            "posts": len(posts),
            "courses": len(courses),
            "gigs": len(gigs),
        },
    }
