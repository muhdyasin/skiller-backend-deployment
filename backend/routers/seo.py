"""SEO endpoints — sitemap.xml + crawler-friendly OG metadata for /c/ pages.

`/api/og/c/{username}` returns JSON with the OG metadata so external bots
(e.g. WhatsApp, Slack, LinkedIn unfurlers, custom share-preview tools) can
fetch a stable, server-rendered description without executing JS.
"""

from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse

from core import db, FRONTEND_URL

from db.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import AsyncSessionLocal
from services.user_service import UserService


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
    async with AsyncSessionLocal() as pg_db:
        creator_rows = await UserService.get_creators(
            pg_db,
            2000
        )

    creators = [
        {"username": u.username}
        for u in creator_rows
    ]

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
    async with AsyncSessionLocal() as pg_db:

        user_obj = await UserService.get_user_by_username(
            pg_db,
            username.lower()
        )

        if not user_obj:
            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        followers = await UserService.follower_count(
            pg_db,
            user_obj.id
        )
        
    user = {
    "id": user_obj.id,
    "username": user_obj.username,
    "name": user_obj.name,
    "bio": user_obj.bio,
    "avatar_url": user_obj.avatar_url,
    "role": user_obj.role,
    }
    
    if user.get("role") not in ("creator", "admin"):
        raise HTTPException(status_code=404, detail="Not a creator")

    courses_count = await db.courses.count_documents({"owner_id": user["id"]})
    gigs_count = await db.gigs.count_documents({"owner_id": user["id"]})
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


# ---------- SSR wrappers: these return a thin HTML page with OG tags + JS/meta
# redirect. Paste one in WhatsApp / Slack / LinkedIn / Twitter to get a proper
# link preview even though the real app is client-rendered.
def _og_html(title: str, description: str, image: str, url: str,
             og_type: str = "profile", twitter_creator: str = "") -> str:
    tt = escape(title, {'"': "&quot;"})
    dd = escape(description, {'"': "&quot;"})
    ii = escape(image, {'"': "&quot;"})
    uu = escape(url, {'"': "&quot;"})
    tc = escape(twitter_creator, {'"': "&quot;"})
    twitter_creator_tag = f'<meta name="twitter:creator" content="{tc}"/>' if twitter_creator else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>{tt}</title>
  <meta name="description" content="{dd}"/>
  <link rel="canonical" href="{uu}"/>
  <meta property="og:type" content="{escape(og_type)}"/>
  <meta property="og:site_name" content="Skiller"/>
  <meta property="og:title" content="{tt}"/>
  <meta property="og:description" content="{dd}"/>
  <meta property="og:image" content="{ii}"/>
  <meta property="og:url" content="{uu}"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{tt}"/>
  <meta name="twitter:description" content="{dd}"/>
  <meta name="twitter:image" content="{ii}"/>
  {twitter_creator_tag}
  <meta http-equiv="refresh" content="0;url={uu}"/>
  <meta name="robots" content="index,follow,max-image-preview:large"/>
  <style>body{{font-family:-apple-system,Segoe UI,Roboto,Inter,sans-serif;background:#0a0a0a;color:#fafafa;margin:0;padding:40px;text-align:center}}a{{color:#B91C1C;font-weight:600}}.card{{max-width:420px;margin:10vh auto;border:1px solid #27272a;border-radius:20px;padding:32px}}.av{{width:96px;height:96px;border-radius:50%;object-fit:cover;border:1px solid #27272a}}</style>
</head>
<body>
  <div class="card">
    <img src="{ii}" alt="" class="av"/>
    <h1 style="margin:18px 0 4px;font-size:22px">{tt}</h1>
    <p style="color:#a1a1aa;font-size:14px">{dd}</p>
    <p style="margin-top:24px"><a href="{uu}">Open in Skiller →</a></p>
  </div>
  <script>window.location.replace({uu!r});</script>
</body>
</html>"""


@router.get("/share/c/{username}", response_class=HTMLResponse)
async def share_creator(username: str):
    async with AsyncSessionLocal() as pg_db:

        user_obj = await UserService.get_user_by_username(
            pg_db,
            username.lower()
        )

        if not user_obj:
            raise HTTPException(
                status_code=404,
                detail="Creator not found"
            )

        followers = await UserService.follower_count(
            pg_db,
            user_obj.id
        )
        
    user = {
    "id": user_obj.id,
    "username": user_obj.username,
    "name": user_obj.name,
    "bio": user_obj.bio,
    "avatar_url": user_obj.avatar_url,
    "role": user_obj.role,
    }
    
    courses_count = await db.courses.count_documents({"owner_id": user["id"]})
    gigs_count = await db.gigs.count_documents({"owner_id": user["id"]})
    title = f"{user['name']} (@{user['username']}) — Skiller"
    desc = (
        f"{user.get('bio') or 'Creator on Skiller'} · "
        f"{courses_count} courses · {gigs_count} gigs · {followers} followers"
    )
    image = user.get("avatar_url") or "https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80"
    canonical = f"{_site_root()}/c/{user['username']}"
    return HTMLResponse(_og_html(title, desc, image, canonical, og_type="profile",
                                 twitter_creator=f"@{user['username']}"))


@router.get("/share/p/{post_id}", response_class=HTMLResponse)
async def share_post(post_id: str,pg_db: AsyncSession = Depends(get_db)):
    post = await db.posts.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    author_obj = await UserService.get_user(
        pg_db,
        post["user_id"]
    )
    
    author = {
    "username": author_obj.username,
    "name": author_obj.name,
    "avatar_url": author_obj.avatar_url,
    }
    
    caption = post.get("caption") or f"Post by @{author.get('username', 'creator')}"
    title = f"{caption[:70]}"
    desc = f"On Skiller · @{author.get('username', 'creator')} · {len(post.get('likes', []))} likes · {len(post.get('comments', []))} comments"
    image = post.get("media") if post.get("media_type") != "video" else (
        author.get("avatar_url") or "https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80"
    )
    canonical = f"{_site_root()}/p/{post_id}"
    return HTMLResponse(_og_html(
        title, desc, image or "", canonical,
        og_type="article",
        twitter_creator=f"@{author.get('username', '')}" if author.get("username") else "",
    ))


@router.get("/share/u/{username}", response_class=HTMLResponse)
async def share_user(username: str,pg_db: AsyncSession = Depends(get_db)):
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
    "bio": user_obj.bio,
    "avatar_url": user_obj.avatar_url,
    "role": user_obj.role,
    }
    
    followers = await UserService.follower_count(
    pg_db,
    user_obj.id
    )
    title = f"{user['name']} (@{user['username']}) — Skiller"
    desc = user_obj.bio or f"{followers} followers on Skiller"    
    image = user.get("avatar_url") or "https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80"
    canonical = f"{_site_root()}/u/{user['username']}"
    return HTMLResponse(_og_html(title, desc, image, canonical, og_type="profile",
                                 twitter_creator=f"@{user['username']}"))
