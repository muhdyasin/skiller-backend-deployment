"""SEO endpoints — sitemap.xml + crawler-friendly OG metadata for /c/ pages.

`/api/og/c/{username}` returns JSON with the OG metadata so external bots
(e.g. WhatsApp, Slack, LinkedIn unfurlers, custom share-preview tools) can
fetch a stable, server-rendered description without executing JS.
"""
import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse

from core import db, FRONTEND_URL

router = APIRouter(prefix="/api", tags=["seo"])


def _site_root() -> str:
    return (FRONTEND_URL or "").rstrip("/") or ""


@router.get("/sitemap.xml")
async def sitemap():
    root = _site_root()
    now = datetime.now(timezone.utc).date().isoformat()
    urls = [
        ("", "1.0", "daily"),
        ("/explore", "0.9", "daily"),
        ("/reels", "0.9", "daily"),
        ("/courses", "0.9", "daily"),
        ("/gigs", "0.9", "daily"),
        ("/leaderboard", "0.7", "weekly"),
    ]
    creators = await db.users.find(
        {"role": {"$in": ["creator", "admin"]}}, {"_id": 0, "username": 1},
    ).limit(2000).to_list(2000)
    courses = await db.courses.find({}, {"_id": 0, "id": 1}).limit(2000).to_list(2000)

    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, prio, freq in urls:
        parts.append(
            f"<url><loc>{escape(root + path)}</loc><changefreq>{freq}</changefreq>"
            f"<priority>{prio}</priority><lastmod>{now}</lastmod></url>"
        )
    for c in creators:
        if not c.get("username"):
            continue
        loc = escape(f"{root}/c/{c['username']}")
        parts.append(f"<url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>0.8</priority><lastmod>{now}</lastmod></url>")
    parts.append('</urlset>')
    body = "\n".join(parts)
    return Response(content=body, media_type="application/xml")


@router.get("/og/c/{username}")
async def og_creator(username: str):
    """Crawler-friendly metadata for a creator's storefront."""
    user = await db.users.find_one(
        {"username": username.lower()},
        {"_id": 0, "id": 1, "username": 1, "name": 1, "bio": 1, "avatar_url": 1, "role": 1},
    )
    if not user:
        raise HTTPException(status_code=404, detail="Creator not found")
    if user.get("role") not in ("creator", "admin"):
        raise HTTPException(status_code=404, detail="Not a creator")

    courses_count = await db.courses.count_documents({"owner_id": user["id"]})
    gigs_count = await db.gigs.count_documents({"owner_id": user["id"]})
    fully = await db.users.find_one({"id": user["id"]}, {"_id": 0, "followers": 1})
    followers = len((fully or {}).get("followers", []))

    title = f"{user['name']} (@{user['username']}) — Skiller"
    desc = (
        f"{user.get('bio') or 'Creator on Skiller'} · "
        f"{courses_count} courses · {gigs_count} gigs · {followers} followers"
    )
    image = user.get("avatar_url") or "https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80"
    canonical = f"{_site_root()}/c/{user['username']}"

    return {
        "title": title,
        "description": desc,
        "image": image,
        "url": canonical,
        "type": "profile",
        "site_name": "Skiller",
        "username": user["username"],
        "name": user["name"],
        "stats": {
            "courses": courses_count,
            "gigs": gigs_count,
            "followers": followers,
        },
    }
