"""Search across users, posts, courses, gigs.

Hybrid strategy:
- Try Mongo $text search first (uses indexes from seed.py).
- If $text returns nothing (e.g. partial token like "re" or "may"), fall back
  to regex on the same fields. This keeps prefix/typeahead queries usable.
"""
import re
from fastapi import APIRouter, HTTPException, Query
from core import db, compute_level

router = APIRouter(prefix="/api/search", tags=["search"])


def _re(q: str):
    return {"$regex": re.escape(q), "$options": "i"}


async def _text_then_regex(coll, q: str, regex_filter: dict, projection: dict, limit: int, sort=None):
    """Run $text first; on empty result, fall back to regex_filter."""
    cursor = db[coll].find({"$text": {"$search": q}}, projection)
    if sort:
        cursor = cursor.sort(*sort)
    docs = await cursor.limit(limit).to_list(limit)
    if docs:
        return docs
    cursor = db[coll].find(regex_filter, projection)
    if sort:
        cursor = cursor.sort(*sort)
    return await cursor.limit(limit).to_list(limit)


@router.get("")
async def search(q: str = Query(..., min_length=1), limit: int = 8):
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query required")

    user_proj = {"_id": 0, "password_hash": 0, "followers": 0, "following": 0}
    users = await _text_then_regex(
        "users", q,
        {"$or": [{"username": _re(q)}, {"name": _re(q)}, {"bio": _re(q)}]},
        user_proj, limit,
    )
    for u in users:
        u["level"] = compute_level(u.get("xp", 0))

    posts = await _text_then_regex(
        "posts", q,
        {"$or": [{"caption": _re(q)}, {"tags": {"$in": [re.compile(re.escape(q), re.I)]}}]},
        {"_id": 0, "likes": 0, "comments": 0},
        limit,
        sort=("created_at", -1),
    )
    for p in posts:
        a = await db.users.find_one(
            {"id": p["user_id"]},
            {"_id": 0, "id": 1, "username": 1, "name": 1, "avatar_url": 1},
        )
        p["author"] = a

    courses = await _text_then_regex(
        "courses", q,
        {"$or": [{"title": _re(q)}, {"description": _re(q)}, {"category": _re(q)}, {"instructor": _re(q)}]},
        {"_id": 0}, limit,
    )

    gigs = await _text_then_regex(
        "gigs", q,
        {"$or": [{"title": _re(q)}, {"description": _re(q)}, {"category": _re(q)}, {"skills": _re(q)}]},
        {"_id": 0}, limit,
    )

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
