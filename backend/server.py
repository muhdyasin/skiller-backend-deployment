from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import logging
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

# ---------- DB ----------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"

app = FastAPI(title="Skiller API")
api = APIRouter(prefix="/api")


# ---------- Utils ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_user_by_id(user_id: str) -> Optional[dict]:
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return u


async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    token = None
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user = await get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def maybe_current_user(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# ---------- Models ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    username: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    username: str
    bio: Optional[str] = ""
    avatar_url: Optional[str] = ""
    followers: List[str] = []
    following: List[str] = []
    role: Optional[str] = "user"
    created_at: str


class PostCreate(BaseModel):
    caption: str = ""
    media: str  # base64 data URL
    media_type: str = "image"  # image|video
    tags: List[str] = []


class CommentCreate(BaseModel):
    text: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class GigApply(BaseModel):
    message: str = ""


# ---------- AUTH ----------
@api.post("/auth/register")
async def register(data: RegisterIn, response: Response):
    email = data.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": data.username.lower().strip()}):
        raise HTTPException(status_code=400, detail="Username already taken")

    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "email": email,
        "username": data.username.lower().strip(),
        "name": data.name.strip(),
        "password_hash": hash_password(data.password),
        "bio": "",
        "avatar_url": "",
        "followers": [],
        "following": [],
        "role": "user",
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)

    token = create_access_token(user_id, email)
    user = await get_user_by_id(user_id)
    return {"token": token, "user": user}


@api.post("/auth/login")
async def login(data: LoginIn):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], email)
    safe = await get_user_by_id(user["id"])
    return {"token": token, "user": safe}


@api.get("/auth/me")
async def me(current=Depends(get_current_user)):
    return current


# ---------- USERS ----------
@api.get("/users/{username}")
async def get_user_profile(username: str, request: Request):
    user = await db.users.find_one(
        {"username": username.lower()}, {"_id": 0, "password_hash": 0}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    posts = await db.posts.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    viewer = await maybe_current_user(request)
    is_following = False
    if viewer:
        is_following = viewer["id"] in user.get("followers", [])
    return {
        "user": user,
        "posts": posts,
        "post_count": len(posts),
        "follower_count": len(user.get("followers", [])),
        "following_count": len(user.get("following", [])),
        "is_following": is_following,
        "is_self": bool(viewer and viewer["id"] == user["id"]),
    }


@api.post("/users/{user_id}/follow")
async def follow_user(user_id: str, current=Depends(get_current_user)):
    if user_id == current["id"]:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    following = current["id"] in target.get("followers", [])
    if following:
        await db.users.update_one({"id": user_id}, {"$pull": {"followers": current["id"]}})
        await db.users.update_one({"id": current["id"]}, {"$pull": {"following": user_id}})
        return {"following": False}
    else:
        await db.users.update_one({"id": user_id}, {"$addToSet": {"followers": current["id"]}})
        await db.users.update_one({"id": current["id"]}, {"$addToSet": {"following": user_id}})
        return {"following": True}


@api.patch("/users/me")
async def update_profile(data: ProfileUpdate, current=Depends(get_current_user)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": current["id"]}, {"$set": updates})
    return await get_user_by_id(current["id"])


@api.get("/users")
async def list_users(limit: int = 20):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).limit(limit).to_list(limit)
    return users


# ---------- POSTS ----------
async def enrich_post(p: dict, viewer_id: Optional[str]) -> dict:
    author = await db.users.find_one(
        {"id": p["user_id"]}, {"_id": 0, "password_hash": 0, "followers": 0, "following": 0}
    )
    p["author"] = author
    p["like_count"] = len(p.get("likes", []))
    p["comment_count"] = len(p.get("comments", []))
    p["liked"] = bool(viewer_id and viewer_id in p.get("likes", []))
    return p


@api.post("/posts")
async def create_post(data: PostCreate, current=Depends(get_current_user)):
    post = {
        "id": str(uuid.uuid4()),
        "user_id": current["id"],
        "caption": data.caption,
        "media": data.media,
        "media_type": data.media_type,
        "tags": data.tags,
        "likes": [],
        "comments": [],
        "created_at": now_iso(),
    }
    await db.posts.insert_one(post.copy())
    return await enrich_post(post, current["id"])


@api.get("/posts/feed")
async def get_feed(request: Request, limit: int = 30):
    viewer = await maybe_current_user(request)
    posts = await db.posts.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    viewer_id = viewer["id"] if viewer else None
    return [await enrich_post(p, viewer_id) for p in posts]


@api.get("/posts/explore")
async def explore(request: Request, limit: int = 60):
    viewer = await maybe_current_user(request)
    posts = await db.posts.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    viewer_id = viewer["id"] if viewer else None
    return [await enrich_post(p, viewer_id) for p in posts]


@api.get("/posts/{post_id}")
async def get_post(post_id: str, request: Request):
    p = await db.posts.find_one({"id": post_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    viewer = await maybe_current_user(request)
    return await enrich_post(p, viewer["id"] if viewer else None)


@api.post("/posts/{post_id}/like")
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
    p2 = await db.posts.find_one({"id": post_id}, {"_id": 0})
    return {"liked": liked, "like_count": len(p2.get("likes", []))}


@api.post("/posts/{post_id}/comments")
async def add_comment(post_id: str, data: CommentCreate, current=Depends(get_current_user)):
    p = await db.posts.find_one({"id": post_id})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    comment = {
        "id": str(uuid.uuid4()),
        "user_id": current["id"],
        "username": current["username"],
        "name": current["name"],
        "avatar_url": current.get("avatar_url", ""),
        "text": data.text,
        "created_at": now_iso(),
    }
    await db.posts.update_one({"id": post_id}, {"$push": {"comments": comment}})
    return comment


@api.get("/posts/{post_id}/comments")
async def list_comments(post_id: str):
    p = await db.posts.find_one({"id": post_id}, {"_id": 0, "comments": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    return p.get("comments", [])


@api.delete("/posts/{post_id}")
async def delete_post(post_id: str, current=Depends(get_current_user)):
    p = await db.posts.find_one({"id": post_id})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    if p["user_id"] != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.posts.delete_one({"id": post_id})
    return {"ok": True}


# ---------- COURSES ----------
@api.get("/courses")
async def list_courses():
    courses = await db.courses.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return courses


@api.get("/courses/{course_id}")
async def get_course(course_id: str):
    c = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return c


# ---------- GIGS ----------
@api.get("/gigs")
async def list_gigs():
    gigs = await db.gigs.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return gigs


@api.post("/gigs/{gig_id}/apply")
async def apply_gig(gig_id: str, data: GigApply, current=Depends(get_current_user)):
    gig = await db.gigs.find_one({"id": gig_id})
    if not gig:
        raise HTTPException(status_code=404, detail="Gig not found")
    application = {
        "id": str(uuid.uuid4()),
        "gig_id": gig_id,
        "user_id": current["id"],
        "username": current["username"],
        "message": data.message,
        "created_at": now_iso(),
    }
    await db.applications.insert_one(application.copy())
    return {"ok": True, "application": application}


# ---------- SEED ----------
DEMO_AVATARS = [
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=400&q=80",
    "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&q=80",
    "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=400&q=80",
    "https://images.pexels.com/photos/10657877/pexels-photo-10657877.jpeg?w=400",
]

DEMO_POST_IMAGES = [
    "https://images.pexels.com/photos/6446678/pexels-photo-6446678.jpeg?w=1200",
    "https://images.unsplash.com/photo-1648111320024-3a08e28d20ff?w=1200&q=80",
    "https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=1200&q=80",
    "https://images.pexels.com/photos/8546798/pexels-photo-8546798.jpeg?w=1200",
    "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&q=80",
    "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=1200&q=80",
]

DEMO_COURSE_IMAGES = [
    "https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=1200&q=80",
    "https://images.pexels.com/photos/8546798/pexels-photo-8546798.jpeg?w=1200",
    "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200&q=80",
    "https://images.unsplash.com/photo-1517180102446-f3ece451e9d8?w=1200&q=80",
]


async def seed():
    # indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.posts.create_index([("created_at", -1)])

    # Admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@skiller.app")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "username": "admin",
            "name": "Skiller Admin",
            "password_hash": hash_password(admin_pw),
            "bio": "Official Skiller team account. Welcome to the community.",
            "avatar_url": DEMO_AVATARS[0],
            "followers": [],
            "following": [],
            "role": "admin",
            "created_at": now_iso(),
        })
    elif not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw)}})

    # Demo users
    demo_users = [
        ("maya@skiller.app", "maya", "Maya Sharma", "UI/UX designer · Bangalore. Turning ideas into pixels.", DEMO_AVATARS[1]),
        ("arjun@skiller.app", "arjun", "Arjun Verma", "Full-stack dev · Freelancer · Teaching React on Skiller.", DEMO_AVATARS[3]),
        ("neha@skiller.app", "neha", "Neha Iyer", "Product manager · Ex-Razorpay · Writing about 0→1.", DEMO_AVATARS[2]),
    ]
    user_ids = {}
    for email, username, name, bio, avatar in demo_users:
        u = await db.users.find_one({"email": email})
        if not u:
            uid = str(uuid.uuid4())
            await db.users.insert_one({
                "id": uid, "email": email, "username": username, "name": name,
                "password_hash": hash_password("Demo@123"),
                "bio": bio, "avatar_url": avatar,
                "followers": [], "following": [],
                "role": "user", "created_at": now_iso(),
            })
            user_ids[username] = uid
        else:
            user_ids[username] = u["id"]

    # Demo posts
    if await db.posts.count_documents({}) == 0:
        demo_posts = [
            ("maya", "Shipped a new design system today. Blues and whites — clean, calm, and crazy scalable.", DEMO_POST_IMAGES[0], ["design", "systems"]),
            ("arjun", "Built a mini Instagram clone in 4 hours using React + FastAPI. Tutorial dropping this weekend.", DEMO_POST_IMAGES[1], ["react", "fastapi", "tutorial"]),
            ("neha", "Three frameworks I use to decide what NOT to build. Saved us 6 months last quarter.", DEMO_POST_IMAGES[2], ["product", "strategy"]),
            ("maya", "Typography is 90% of good UI. Here's the exact scale I use on every project.", DEMO_POST_IMAGES[3], ["typography", "ui"]),
            ("arjun", "Landed my first ₹50k freelance gig through Skiller gigs marketplace. It works.", DEMO_POST_IMAGES[4], ["freelance", "win"]),
            ("neha", "Weekend read: how to price yourself without undercutting your worth.", DEMO_POST_IMAGES[5], ["career"]),
        ]
        for username, caption, media, tags in demo_posts:
            await db.posts.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user_ids[username],
                "caption": caption,
                "media": media,
                "media_type": "image",
                "tags": tags,
                "likes": [],
                "comments": [],
                "created_at": now_iso(),
            })

    # Courses
    if await db.courses.count_documents({}) == 0:
        courses = [
            ("React Mastery 2026", "Learn modern React 19 with hooks, server components, and real projects.", "Arjun Verma", 12, 2999, DEMO_COURSE_IMAGES[0], "Development"),
            ("UI/UX Design Foundations", "Design stunning interfaces from scratch — color, type, layout, motion.", "Maya Sharma", 18, 3499, DEMO_COURSE_IMAGES[1], "Design"),
            ("Product Management 0→1", "Go from idea to MVP to PMF. Frameworks from top Indian PMs.", "Neha Iyer", 10, 2499, DEMO_COURSE_IMAGES[2], "Product"),
            ("Freelancing Without Begging", "Get your first 5 clients in 30 days. Pricing, pitching, delivery.", "Arjun Verma", 8, 1999, DEMO_COURSE_IMAGES[3], "Business"),
        ]
        for title, desc, instructor, lessons, price, thumb, cat in courses:
            await db.courses.insert_one({
                "id": str(uuid.uuid4()),
                "title": title,
                "description": desc,
                "instructor": instructor,
                "lessons": lessons,
                "price": price,
                "thumbnail": thumb,
                "category": cat,
                "rating": 4.7,
                "students": 1200,
                "created_at": now_iso(),
            })

    # Gigs
    if await db.gigs.count_documents({}) == 0:
        gigs = [
            ("Landing page in React + Tailwind", "Need a clean conversion-focused landing page for a SaaS.", 25000, "Remote", "Web Development", ["React", "Tailwind"]),
            ("Logo + Brand identity for D2C brand", "Full brand identity kit — logo, type, palette, usage.", 40000, "Remote", "Design", ["Logo", "Branding"]),
            ("Instagram content calendar (30 days)", "Plan and design 30 reels + carousel posts for a coaching brand.", 15000, "Remote", "Content", ["Social", "Design"]),
            ("Python automation for lead scraping", "Scrape LinkedIn + clean into Google Sheets daily.", 20000, "Remote", "Development", ["Python", "Automation"]),
            ("Product strategy consulting (4 hrs)", "Help us pick the right v1 scope for our healthtech app.", 18000, "Remote", "Product", ["Strategy"]),
        ]
        for title, desc, budget, location, cat, skills in gigs:
            await db.gigs.insert_one({
                "id": str(uuid.uuid4()),
                "title": title,
                "description": desc,
                "budget": budget,
                "currency": "INR",
                "location": location,
                "category": cat,
                "skills": skills,
                "created_at": now_iso(),
            })


@app.on_event("startup")
async def startup():
    await seed()


@app.on_event("shutdown")
async def shutdown():
    client.close()


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
