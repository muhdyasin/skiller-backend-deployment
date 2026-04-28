"""Dashboard stats + my-content listings."""
from fastapi import APIRouter, Depends
from core import db, get_current_user, compute_level

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats(current=Depends(get_current_user)):
    posts = await db.posts.find({"user_id": current["id"]}, {"_id": 0, "likes": 1, "comments": 1}).to_list(1000)
    total_likes = sum(len(p.get("likes", [])) for p in posts)
    total_comments = sum(len(p.get("comments", [])) for p in posts)
    courses = await db.courses.count_documents({"owner_id": current["id"]})
    enrollments = 0
    async for c in db.courses.find({"owner_id": current["id"]}, {"id": 1}):
        enrollments += await db.enrollments.count_documents({"course_id": c["id"]})
    ads = await db.ad_campaigns.find({"owner_id": current["id"]}, {"_id": 0}).to_list(200)
    ad_impressions = sum(a.get("impressions", 0) for a in ads)
    ad_clicks = sum(a.get("clicks", 0) for a in ads)
    ad_spend = sum(a.get("spend", 0) for a in ads)
    user = await db.users.find_one({"id": current["id"]}, {"_id": 0, "followers": 1, "xp": 1})
    return {
        "posts": len(posts),
        "likes": total_likes,
        "comments": total_comments,
        "followers": len(user.get("followers", [])),
        "courses": courses,
        "enrollments": enrollments,
        "active_ads": len([a for a in ads if a.get("status") == "active"]),
        "ad_impressions": ad_impressions,
        "ad_clicks": ad_clicks,
        "ad_spend": ad_spend,
        "ad_ctr": round((ad_clicks / ad_impressions * 100) if ad_impressions else 0, 2),
        "xp": user.get("xp", 0),
        "level": compute_level(user.get("xp", 0)),
    }


@router.get("/posts")
async def my_posts(current=Depends(get_current_user)):
    return await db.posts.find({"user_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.get("/courses")
async def my_courses(current=Depends(get_current_user)):
    return await db.courses.find({"owner_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
