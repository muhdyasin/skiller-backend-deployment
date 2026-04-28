"""Dashboard stats + insights + CRM."""
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict
from fastapi import APIRouter, Depends
from core import db, get_current_user, require_creator, compute_level

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


def _daystr(d: datetime) -> str:
    return d.date().isoformat()


@router.get("/insights")
async def insights(current=Depends(require_creator)):
    """30-day series + top posts + top courses + ad summary."""
    posts = await db.posts.find(
        {"user_id": current["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)

    # Build 30-day series for posts/likes/comments
    days_iso = [_daystr(datetime.now(timezone.utc) - timedelta(days=i)) for i in range(29, -1, -1)]
    series_posts = {d: 0 for d in days_iso}
    series_likes = {d: 0 for d in days_iso}
    series_comments = {d: 0 for d in days_iso}
    for p in posts:
        try:
            d = datetime.fromisoformat(p["created_at"]).date().isoformat()
        except Exception:
            continue
        if d in series_posts:
            series_posts[d] += 1
            series_likes[d] += len(p.get("likes", []))
            series_comments[d] += len(p.get("comments", []))

    # Top 3 posts by engagement (likes + comments)
    posts_sorted = sorted(
        posts, key=lambda p: len(p.get("likes", [])) + len(p.get("comments", [])), reverse=True
    )[:3]
    top_posts = [
        {
            "id": p["id"], "caption": p.get("caption", ""),
            "media": p.get("media", ""), "media_type": p.get("media_type", "image"),
            "likes": len(p.get("likes", [])), "comments": len(p.get("comments", [])),
            "engagement": len(p.get("likes", [])) + len(p.get("comments", [])),
        }
        for p in posts_sorted
    ]

    # Top 3 courses by enrollments
    courses = await db.courses.find(
        {"owner_id": current["id"]}, {"_id": 0}
    ).to_list(100)
    course_stats = []
    for c in courses:
        enroll = await db.enrollments.count_documents({"course_id": c["id"]})
        course_stats.append({**c, "enrollments": enroll})
    course_stats.sort(key=lambda x: x["enrollments"], reverse=True)
    top_courses = course_stats[:3]

    # Ads
    ads = await db.ad_campaigns.find({"owner_id": current["id"]}, {"_id": 0}).to_list(200)
    ad_summary = {
        "campaigns": len(ads),
        "active": len([a for a in ads if a.get("status") == "active"]),
        "impressions": sum(a.get("impressions", 0) for a in ads),
        "clicks": sum(a.get("clicks", 0) for a in ads),
        "spend": sum(a.get("spend", 0) for a in ads),
    }
    ad_summary["ctr"] = round(
        (ad_summary["clicks"] / ad_summary["impressions"] * 100) if ad_summary["impressions"] else 0, 2
    )

    # Follower count snapshot
    user = await db.users.find_one({"id": current["id"]}, {"_id": 0, "followers": 1})

    return {
        "series": {
            "days": days_iso,
            "posts": [series_posts[d] for d in days_iso],
            "likes": [series_likes[d] for d in days_iso],
            "comments": [series_comments[d] for d in days_iso],
        },
        "top_posts": top_posts,
        "top_courses": top_courses,
        "ads": ad_summary,
        "followers": len(user.get("followers", [])),
        "totals": {
            "posts": len(posts),
            "likes": sum(len(p.get("likes", [])) for p in posts),
            "comments": sum(len(p.get("comments", [])) for p in posts),
            "courses": len(courses),
            "enrollments": sum(c["enrollments"] for c in course_stats),
        },
    }


@router.get("/crm")
async def crm(current=Depends(require_creator)):
    """List all gigs with applicants + courses with enrollees, suitable for CRM view."""
    gigs = await db.gigs.find({"owner_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    gig_blocks = []
    total_apps = 0
    for g in gigs:
        apps = await db.applications.find(
            {"gig_id": g["id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(200)
        total_apps += len(apps)
        gig_blocks.append({"gig": g, "applications": apps})

    courses = await db.courses.find({"owner_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    course_blocks = []
    total_enrolls = 0
    for c in courses:
        enrolls = await db.enrollments.find({"course_id": c["id"]}, {"_id": 0}).to_list(500)
        # enrich with user details
        enriched = []
        for e in enrolls:
            u = await db.users.find_one(
                {"id": e["user_id"]},
                {"_id": 0, "username": 1, "name": 1, "email": 1, "avatar_url": 1},
            )
            enriched.append({**e, "user": u})
        total_enrolls += len(enriched)
        course_blocks.append({"course": c, "enrollments": enriched})

    return {
        "gigs": gig_blocks,
        "courses": course_blocks,
        "summary": {
            "gigs": len(gigs),
            "applications": total_apps,
            "courses": len(courses),
            "enrollments": total_enrolls,
        },
    }
