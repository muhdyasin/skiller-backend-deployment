from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import json
import secrets
import logging
import bcrypt
import jwt
import requests
import asyncio
from datetime import datetime, timezone, timedelta, date
from typing import List, Optional, Set, Dict

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Header, Query, WebSocket, WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response as StarletteResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, field_validator

# ---------- DB ----------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"
APP_NAME = os.environ.get("APP_NAME", "skiller")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
storage_key: Optional[str] = None

app = FastAPI(title="Skiller API")
api = APIRouter(prefix="/api")
logger = logging.getLogger("skiller")
logging.basicConfig(level=logging.INFO)


# ---------- Utils ----------
def now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now().isoformat()


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
        "exp": now() + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_user_by_id(user_id: str) -> Optional[dict]:
    return await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})


async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else request.cookies.get("access_token")
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


# ---------- XP / Levels / Badges ----------
LEVEL_THRESHOLDS = [
    (0, "Newbie"), (50, "Spark"), (150, "Apprentice"), (350, "Builder"),
    (750, "Maker"), (1500, "Pro"), (3000, "Mentor"), (6000, "Master"), (12000, "Legend"),
]

XP_RULES = {
    "post_create": 20,
    "like_received": 2,
    "like_given": 1,
    "comment_given": 5,
    "comment_received": 3,
    "follow_given": 1,
    "follow_received": 5,
    "course_enroll": 10,
    "gig_apply": 15,
    "daily_login": 5,
}

BADGE_DEFS = [
    {"key": "first_post", "title": "First Post", "icon": "🎬", "desc": "Published your first post"},
    {"key": "creator_10", "title": "Creator", "icon": "🎨", "desc": "Published 10 posts"},
    {"key": "loved_10", "title": "Liked", "icon": "💙", "desc": "Received 10 likes"},
    {"key": "loved_50", "title": "Beloved", "icon": "💖", "desc": "Received 50 likes"},
    {"key": "convo_10", "title": "Conversationalist", "icon": "💬", "desc": "Posted 10 comments"},
    {"key": "connector_10", "title": "Connector", "icon": "🤝", "desc": "10 followers"},
    {"key": "earner", "title": "Earner", "icon": "💼", "desc": "Applied to your first gig"},
    {"key": "scholar", "title": "Scholar", "icon": "📚", "desc": "Enrolled in your first course"},
    {"key": "streak_3", "title": "On Fire", "icon": "🔥", "desc": "3-day login streak"},
    {"key": "streak_7", "title": "Week Warrior", "icon": "⚡", "desc": "7-day login streak"},
]


def compute_level(xp: int) -> dict:
    level_idx = 0
    for i, (thr, _) in enumerate(LEVEL_THRESHOLDS):
        if xp >= thr:
            level_idx = i
    name = LEVEL_THRESHOLDS[level_idx][1]
    next_thr = LEVEL_THRESHOLDS[level_idx + 1][0] if level_idx + 1 < len(LEVEL_THRESHOLDS) else None
    cur_thr = LEVEL_THRESHOLDS[level_idx][0]
    if next_thr is None:
        progress = 1.0
        to_next = 0
    else:
        progress = (xp - cur_thr) / max(1, (next_thr - cur_thr))
        to_next = next_thr - xp
    return {
        "level": level_idx + 1,
        "name": name,
        "xp": xp,
        "current_threshold": cur_thr,
        "next_threshold": next_thr,
        "progress": round(min(max(progress, 0), 1), 3),
        "xp_to_next": max(to_next, 0),
    }


async def award_xp(user_id: str, reason: str, amount: Optional[int] = None, meta: Optional[dict] = None):
    if amount is None:
        amount = XP_RULES.get(reason, 0)
    if amount == 0:
        return
    await db.users.update_one({"id": user_id}, {"$inc": {"xp": amount}})
    await db.xp_events.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "reason": reason,
        "amount": amount,
        "meta": meta or {},
        "created_at": now_iso(),
    })
    await check_badges(user_id)


async def check_badges(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        return
    earned = set(user.get("badges", []))
    new = set()

    post_count = await db.posts.count_documents({"user_id": user_id})
    likes_received = 0
    async for p in db.posts.find({"user_id": user_id}, {"likes": 1}):
        likes_received += len(p.get("likes", []))
    comments_given = await db.posts.count_documents({"comments.user_id": user_id})
    follower_count = len(user.get("followers", []))
    streak = user.get("streak", 0)
    has_gig_app = await db.applications.count_documents({"user_id": user_id}) > 0
    has_enroll = await db.enrollments.count_documents({"user_id": user_id}) > 0

    rules = {
        "first_post": post_count >= 1,
        "creator_10": post_count >= 10,
        "loved_10": likes_received >= 10,
        "loved_50": likes_received >= 50,
        "convo_10": comments_given >= 10,
        "connector_10": follower_count >= 10,
        "earner": has_gig_app,
        "scholar": has_enroll,
        "streak_3": streak >= 3,
        "streak_7": streak >= 7,
    }
    for k, ok in rules.items():
        if ok and k not in earned:
            new.add(k)
    if new:
        await db.users.update_one({"id": user_id}, {"$addToSet": {"badges": {"$each": list(new)}}})
        for b in new:
            await create_notification(user_id, "badge", f"New badge unlocked: {b}", meta={"badge": b})


# ---------- Notifications ----------
class WSManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.connections.setdefault(user_id, set()).add(ws)

    async def disconnect(self, user_id: str, ws: WebSocket):
        async with self.lock:
            if user_id in self.connections:
                self.connections[user_id].discard(ws)
                if not self.connections[user_id]:
                    self.connections.pop(user_id, None)

    async def send_to(self, user_id: str, payload: dict):
        sockets = list(self.connections.get(user_id, set()))
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                await self.disconnect(user_id, ws)


ws_manager = WSManager()


async def create_notification(user_id: str, kind: str, message: str, actor_id: Optional[str] = None, meta: Optional[dict] = None):
    if actor_id == user_id:
        return
    notif = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "actor_id": actor_id,
        "kind": kind,
        "message": message,
        "meta": meta or {},
        "read": False,
        "created_at": now_iso(),
    }
    await db.notifications.insert_one(notif.copy())
    # broadcast over websocket if connected
    actor = None
    if actor_id:
        actor = await db.users.find_one({"id": actor_id}, {"_id": 0, "id": 1, "username": 1, "name": 1, "avatar_url": 1})
    payload = {**notif, "actor": actor}
    try:
        await ws_manager.send_to(user_id, {"type": "notification", "data": payload})
    except Exception as e:
        logger.warning(f"WS send failed: {e}")


async def enrich_notification(n: dict) -> dict:
    if n.get("actor_id"):
        actor = await db.users.find_one({"id": n["actor_id"]}, {"_id": 0, "id": 1, "username": 1, "name": 1, "avatar_url": 1})
        n["actor"] = actor
    return n


# ---------- Storage ----------
def init_storage() -> Optional[str]:
    global storage_key
    if storage_key:
        return storage_key
    if not EMERGENT_LLM_KEY:
        logger.warning("EMERGENT_LLM_KEY missing; storage disabled")
        return None
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        logger.info("Object storage initialized")
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=503, detail="Storage unavailable")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    if resp.status_code == 403:
        global storage_key
        storage_key = None
        key = init_storage()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=503, detail="Storage unavailable")
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 403:
        global storage_key
        storage_key = None
        key = init_storage()
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ---------- Models ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    username: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class PostCreate(BaseModel):
    caption: str = ""
    media: str  # URL: https://, /api/files/, or http://
    media_type: str = "image"
    tags: List[str] = []

    @field_validator("media")
    @classmethod
    def _validate_media(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("media is required")
        if v.startswith("/api/files/") or v.startswith("https://") or v.startswith("http://"):
            return v
        raise ValueError("media must be an https URL or a /api/files/ path")


class CommentCreate(BaseModel):
    text: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class GigApply(BaseModel):
    message: str = ""


class CourseCreate(BaseModel):
    title: str
    description: str
    price: int = 0
    lessons: int = 1
    thumbnail: str = ""
    category: str = "General"


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    lessons: Optional[int] = None
    thumbnail: Optional[str] = None
    category: Optional[str] = None


class AdCreate(BaseModel):
    title: str
    caption: str = ""
    media: str
    cta_label: str = "Learn more"
    cta_url: str = "#"
    daily_budget: int = 500
    duration_days: int = 7


class AdStatus(BaseModel):
    status: str  # active|paused


# ---------- AUTH ----------
async def update_streak_on_login(user_id: str):
    user = await db.users.find_one({"id": user_id})
    today = date.today().isoformat()
    last = user.get("last_login_date")
    streak = user.get("streak", 0)
    if last == today:
        return
    if last:
        prev = date.fromisoformat(last)
        diff = (date.today() - prev).days
        if diff == 1:
            streak += 1
        elif diff > 1:
            streak = 1
        else:
            streak = max(streak, 1)
    else:
        streak = 1
    await db.users.update_one({"id": user_id}, {"$set": {"streak": streak, "last_login_date": today}})
    await award_xp(user_id, "daily_login")


@api.post("/auth/register")
async def register(data: RegisterIn):
    email = data.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": data.username.lower().strip()}):
        raise HTTPException(status_code=400, detail="Username already taken")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id, "email": email, "username": data.username.lower().strip(),
        "name": data.name.strip(), "password_hash": hash_password(data.password),
        "bio": "", "avatar_url": "", "followers": [], "following": [],
        "role": "user", "xp": 0, "badges": [], "streak": 0,
        "last_login_date": None, "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    await update_streak_on_login(user_id)
    token = create_access_token(user_id, email)
    return {"token": token, "user": await get_user_by_id(user_id)}


@api.post("/auth/login")
async def login(data: LoginIn):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await update_streak_on_login(user["id"])
    token = create_access_token(user["id"], email)
    return {"token": token, "user": await get_user_by_id(user["id"])}


@api.get("/auth/me")
async def me(current=Depends(get_current_user)):
    await update_streak_on_login(current["id"])
    return await get_user_by_id(current["id"])


# ---------- PASSWORD RESET ----------
class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


@api.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordIn):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    # Always respond 200 to avoid leaking which emails exist
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "token": token,
            "used": False,
            "expires_at": (now() + timedelta(hours=1)).isoformat(),
            "created_at": now_iso(),
        })
        frontend = os.environ.get("FRONTEND_URL", "")
        link = f"{frontend.rstrip('/')}/reset-password/{token}" if frontend else f"/reset-password/{token}"
        # Dev mode: log the link to backend console. Wire to email provider in production.
        logger.info(f"PASSWORD_RESET_LINK for {email}: {link}")
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@api.post("/auth/reset-password")
async def reset_password(data: ResetPasswordIn):
    rec = await db.password_reset_tokens.find_one({"token": data.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    try:
        if datetime.fromisoformat(rec["expires_at"]) < now():
            raise HTTPException(status_code=400, detail="Token expired")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid token")
    await db.users.update_one({"id": rec["user_id"]}, {"$set": {"password_hash": hash_password(data.new_password)}})
    await db.password_reset_tokens.update_one({"token": data.token}, {"$set": {"used": True}})
    return {"ok": True}


# ---------- WEBSOCKET ----------
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = payload["sub"]
        user = await db.users.find_one({"id": user_id})
        if not user:
            await websocket.close(code=4401)
            return
    except Exception:
        await websocket.close(code=4401)
        return

    await ws_manager.connect(user_id, websocket)
    try:
        await websocket.send_json({"type": "connected", "user_id": user_id})
        while True:
            # Keepalive — read & ignore client pings
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WS error: {e}")
    finally:
        await ws_manager.disconnect(user_id, websocket)


# ---------- USERS ----------
@api.get("/users/{username}")
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


@api.post("/users/{user_id}/follow")
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


@api.patch("/users/me")
async def update_profile(data: ProfileUpdate, current=Depends(get_current_user)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": current["id"]}, {"$set": updates})
    return await get_user_by_id(current["id"])


@api.get("/users")
async def list_users(limit: int = 20):
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).limit(limit).to_list(limit)


@api.get("/users/me/xp")
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


@api.get("/leaderboard")
async def leaderboard(limit: int = 20):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("xp", -1).limit(limit).to_list(limit)
    return [{
        "id": u["id"], "username": u["username"], "name": u["name"],
        "avatar_url": u.get("avatar_url", ""), "xp": u.get("xp", 0),
        "level": compute_level(u.get("xp", 0)),
        "badge_count": len(u.get("badges", [])),
    } for u in users]


# ---------- POSTS ----------
async def enrich_post(p: dict, viewer_id: Optional[str]) -> dict:
    author = await db.users.find_one({"id": p["user_id"]}, {"_id": 0, "id": 1, "username": 1, "name": 1, "avatar_url": 1, "xp": 1})
    if author:
        author["level"] = compute_level(author.get("xp", 0))
    p["author"] = author
    p["like_count"] = len(p.get("likes", []))
    p["comment_count"] = len(p.get("comments", []))
    p["liked"] = bool(viewer_id and viewer_id in p.get("likes", []))
    return p


@api.post("/posts")
async def create_post(data: PostCreate, current=Depends(get_current_user)):
    post = {
        "id": str(uuid.uuid4()), "user_id": current["id"],
        "caption": data.caption, "media": data.media, "media_type": data.media_type,
        "tags": data.tags, "likes": [], "comments": [], "created_at": now_iso(),
    }
    await db.posts.insert_one(post.copy())
    await award_xp(current["id"], "post_create")
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
        await award_xp(current["id"], "like_given")
        await award_xp(p["user_id"], "like_received")
        await create_notification(p["user_id"], "like", f"@{current['username']} liked your post", actor_id=current["id"], meta={"post_id": post_id})
    p2 = await db.posts.find_one({"id": post_id}, {"_id": 0})
    return {"liked": liked, "like_count": len(p2.get("likes", []))}


@api.post("/posts/{post_id}/comments")
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
    return await db.courses.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.get("/courses/{course_id}")
async def get_course(course_id: str):
    c = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return c


@api.post("/courses")
async def create_course(data: CourseCreate, current=Depends(get_current_user)):
    course = {
        "id": str(uuid.uuid4()),
        "owner_id": current["id"],
        "instructor": current["name"],
        "title": data.title, "description": data.description,
        "price": data.price, "lessons": data.lessons,
        "thumbnail": data.thumbnail or "https://images.unsplash.com/photo-1519408469771-2586093c3f14?w=1200&q=80",
        "category": data.category,
        "rating": 5.0, "students": 0,
        "created_at": now_iso(),
    }
    await db.courses.insert_one(course.copy())
    return course


@api.patch("/courses/{course_id}")
async def update_course(course_id: str, data: CourseUpdate, current=Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.get("owner_id") != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.courses.update_one({"id": course_id}, {"$set": updates})
    return await db.courses.find_one({"id": course_id}, {"_id": 0})


@api.delete("/courses/{course_id}")
async def delete_course(course_id: str, current=Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.get("owner_id") != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.courses.delete_one({"id": course_id})
    return {"ok": True}


@api.post("/courses/{course_id}/enroll")
async def enroll_course(course_id: str, current=Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = await db.enrollments.find_one({"course_id": course_id, "user_id": current["id"]})
    if existing:
        return {"ok": True, "already": True}
    await db.enrollments.insert_one({
        "id": str(uuid.uuid4()), "course_id": course_id,
        "user_id": current["id"], "created_at": now_iso(),
    })
    await db.courses.update_one({"id": course_id}, {"$inc": {"students": 1}})
    await award_xp(current["id"], "course_enroll")
    return {"ok": True}


# ---------- GIGS ----------
@api.get("/gigs")
async def list_gigs():
    return await db.gigs.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.post("/gigs/{gig_id}/apply")
async def apply_gig(gig_id: str, data: GigApply, current=Depends(get_current_user)):
    gig = await db.gigs.find_one({"id": gig_id})
    if not gig:
        raise HTTPException(status_code=404, detail="Gig not found")
    application = {
        "id": str(uuid.uuid4()), "gig_id": gig_id, "user_id": current["id"],
        "username": current["username"], "message": data.message, "created_at": now_iso(),
    }
    await db.applications.insert_one(application.copy())
    await award_xp(current["id"], "gig_apply")
    return {"ok": True, "application": application}


# ---------- ADS ----------
@api.post("/ads")
async def create_ad(data: AdCreate, current=Depends(get_current_user)):
    ad = {
        "id": str(uuid.uuid4()),
        "owner_id": current["id"], "owner_username": current["username"], "owner_name": current["name"],
        "owner_avatar": current.get("avatar_url", ""),
        "title": data.title, "caption": data.caption, "media": data.media,
        "cta_label": data.cta_label, "cta_url": data.cta_url,
        "daily_budget": data.daily_budget, "duration_days": data.duration_days,
        "status": "active",
        "impressions": 0, "clicks": 0, "spend": 0,
        "created_at": now_iso(),
    }
    await db.ad_campaigns.insert_one(ad.copy())
    return ad


@api.get("/ads/mine")
async def my_ads(current=Depends(get_current_user)):
    return await db.ad_campaigns.find({"owner_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


@api.get("/ads/active")
async def active_ads(limit: int = 3):
    ads = await db.ad_campaigns.find({"status": "active"}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    if ads:
        await db.ad_campaigns.update_many(
            {"id": {"$in": [a["id"] for a in ads]}},
            {"$inc": {"impressions": 1}}
        )
    return ads


@api.post("/ads/{ad_id}/click")
async def ad_click(ad_id: str):
    ad = await db.ad_campaigns.find_one({"id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    cpc = 8  # fake cost-per-click
    await db.ad_campaigns.update_one(
        {"id": ad_id}, {"$inc": {"clicks": 1, "spend": cpc}}
    )
    return {"ok": True}


@api.patch("/ads/{ad_id}/status")
async def update_ad_status(ad_id: str, data: AdStatus, current=Depends(get_current_user)):
    ad = await db.ad_campaigns.find_one({"id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    if ad["owner_id"] != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    if data.status not in ("active", "paused"):
        raise HTTPException(status_code=400, detail="Invalid status")
    await db.ad_campaigns.update_one({"id": ad_id}, {"$set": {"status": data.status}})
    return {"ok": True}


@api.delete("/ads/{ad_id}")
async def delete_ad(ad_id: str, current=Depends(get_current_user)):
    ad = await db.ad_campaigns.find_one({"id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    if ad["owner_id"] != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.ad_campaigns.delete_one({"id": ad_id})
    return {"ok": True}


# ---------- DASHBOARD ----------
@api.get("/dashboard/stats")
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


@api.get("/dashboard/posts")
async def my_posts(current=Depends(get_current_user)):
    return await db.posts.find({"user_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.get("/dashboard/courses")
async def my_courses(current=Depends(get_current_user)):
    return await db.courses.find({"owner_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


# ---------- NOTIFICATIONS ----------
@api.get("/notifications")
async def list_notifications(current=Depends(get_current_user), limit: int = 30):
    items = await db.notifications.find({"user_id": current["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [await enrich_notification(n) for n in items]


@api.get("/notifications/unread-count")
async def unread_count(current=Depends(get_current_user)):
    n = await db.notifications.count_documents({"user_id": current["id"], "read": False})
    return {"count": n}


@api.post("/notifications/read-all")
async def read_all(current=Depends(get_current_user)):
    await db.notifications.update_many({"user_id": current["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}


@api.post("/notifications/{nid}/read")
async def read_one(nid: str, current=Depends(get_current_user)):
    await db.notifications.update_one({"id": nid, "user_id": current["id"]}, {"$set": {"read": True}})
    return {"ok": True}


# ---------- AI RECOMMENDATIONS ----------
@api.get("/ai/recommend")
async def ai_recommend(current=Depends(get_current_user)):
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="AI service unavailable")

    user = await db.users.find_one({"id": current["id"]})
    user_posts = await db.posts.find({"user_id": current["id"]}, {"_id": 0, "caption": 1, "tags": 1}).limit(10).to_list(10)
    courses = await db.courses.find({}, {"_id": 0, "id": 1, "title": 1, "category": 1, "description": 1}).to_list(50)
    gigs = await db.gigs.find({}, {"_id": 0, "id": 1, "title": 1, "skills": 1, "category": 1}).to_list(50)
    creators = await db.users.find({"id": {"$ne": current["id"]}}, {"_id": 0, "username": 1, "name": 1, "bio": 1}).limit(20).to_list(20)

    user_summary = f"Name: {user['name']}\nBio: {user.get('bio', '')}\nRecent posts: {json.dumps(user_posts)}"
    catalog = {
        "courses": courses[:20],
        "gigs": gigs[:20],
        "creators": creators[:15],
    }

    system = (
        "You are a friendly career coach inside Skiller, an Indian learn-to-earn platform. "
        "Pick the most relevant courses, gigs and creators for the given user based on their bio, posts and tags. "
        "Return ONLY valid JSON, no markdown, no commentary."
    )
    prompt = (
        f"USER PROFILE:\n{user_summary}\n\n"
        f"AVAILABLE CATALOG (JSON):\n{json.dumps(catalog)[:6000]}\n\n"
        "Return JSON of shape: {\"courses\": [{\"id\": str, \"why\": str}], "
        "\"gigs\": [{\"id\": str, \"why\": str}], \"creators\": [{\"username\": str, \"why\": str}]}. "
        "Pick at most 3 courses, 3 gigs, 3 creators. 'why' is a single short sentence."
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"recs-{current['id']}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        text = await chat.send_message(UserMessage(text=prompt))
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip("` \n")
        data = json.loads(text)
    except Exception as e:
        logger.error(f"AI recommend failed: {e}")
        # Fallback: pick top items
        data = {
            "courses": [{"id": c["id"], "why": "Trending right now"} for c in courses[:3]],
            "gigs": [{"id": g["id"], "why": "Matches general skills"} for g in gigs[:3]],
            "creators": [{"username": c["username"], "why": "Popular in your network"} for c in creators[:3]],
        }

    course_map = {c["id"]: c for c in courses}
    gig_map = {g["id"]: g for g in gigs}
    creator_map = {c["username"]: c for c in creators}

    out = {
        "courses": [{**course_map[r["id"]], "why": r.get("why", "")} for r in data.get("courses", []) if r.get("id") in course_map][:3],
        "gigs": [{**gig_map[r["id"]], "why": r.get("why", "")} for r in data.get("gigs", []) if r.get("id") in gig_map][:3],
        "creators": [{**creator_map[r["username"]], "why": r.get("why", "")} for r in data.get("creators", []) if r.get("username") in creator_map][:3],
    }
    return out


# ---------- UPLOAD ----------
ALLOWED_MIME = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/webm", "video/quicktime",
}


@api.post("/upload")
async def upload(file: UploadFile = File(...), current=Depends(get_current_user)):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Unsupported type {content_type}")
    data = await file.read()
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"
    if ext not in {"jpg", "jpeg", "png", "webp", "gif", "mp4", "webm", "mov"}:
        ext = "bin"
    path = f"{APP_NAME}/uploads/{current['id']}/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, content_type)
    file_doc = {
        "id": str(uuid.uuid4()),
        "owner_id": current["id"],
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "is_deleted": False,
        "created_at": now_iso(),
    }
    await db.files.insert_one(file_doc.copy())
    return {
        "id": file_doc["id"],
        "path": result["path"],
        "url": f"/api/files/{result['path']}",
        "content_type": content_type,
        "size": file_doc["size"],
    }


@api.get("/files/{path:path}")
async def download_file(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    data, ctype = get_object(path)
    return StarletteResponse(
        content=data,
        media_type=record.get("content_type") or ctype,
        headers={"Cache-Control": "public, max-age=86400"},
    )


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
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("xp")
    await db.posts.create_index([("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.password_reset_tokens.create_index("token", unique=True)
    await db.password_reset_tokens.create_index("expires_at")
    await db.files.create_index("storage_path")
    await db.ad_campaigns.create_index([("status", 1), ("created_at", -1)])

    # Migrate existing users to add xp/badges
    await db.users.update_many({"xp": {"$exists": False}}, {"$set": {"xp": 0, "badges": [], "streak": 0, "last_login_date": None}})

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@skiller.app")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": admin_email, "username": "admin",
            "name": "Skiller Admin", "password_hash": hash_password(admin_pw),
            "bio": "Official Skiller team account.", "avatar_url": DEMO_AVATARS[0],
            "followers": [], "following": [], "role": "admin",
            "xp": 0, "badges": [], "streak": 0, "last_login_date": None,
            "created_at": now_iso(),
        })
    elif not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw)}})

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
                "followers": [], "following": [], "role": "user",
                "xp": 0, "badges": [], "streak": 0, "last_login_date": None,
                "created_at": now_iso(),
            })
            user_ids[username] = uid
        else:
            user_ids[username] = u["id"]

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
                "id": str(uuid.uuid4()), "user_id": user_ids[username],
                "caption": caption, "media": media, "media_type": "image",
                "tags": tags, "likes": [], "comments": [], "created_at": now_iso(),
            })

    if await db.courses.count_documents({}) == 0:
        courses = [
            ("React Mastery 2026", "Learn modern React 19 with hooks, server components, and real projects.", "Arjun Verma", "arjun", 12, 2999, DEMO_COURSE_IMAGES[0], "Development"),
            ("UI/UX Design Foundations", "Design stunning interfaces from scratch — color, type, layout, motion.", "Maya Sharma", "maya", 18, 3499, DEMO_COURSE_IMAGES[1], "Design"),
            ("Product Management 0→1", "Go from idea to MVP to PMF. Frameworks from top Indian PMs.", "Neha Iyer", "neha", 10, 2499, DEMO_COURSE_IMAGES[2], "Product"),
            ("Freelancing Without Begging", "Get your first 5 clients in 30 days. Pricing, pitching, delivery.", "Arjun Verma", "arjun", 8, 1999, DEMO_COURSE_IMAGES[3], "Business"),
        ]
        for title, desc, instructor, owner_username, lessons, price, thumb, cat in courses:
            await db.courses.insert_one({
                "id": str(uuid.uuid4()), "title": title, "description": desc,
                "instructor": instructor, "owner_id": user_ids.get(owner_username, ""),
                "lessons": lessons, "price": price, "thumbnail": thumb, "category": cat,
                "rating": 4.7, "students": 1200, "created_at": now_iso(),
            })

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
                "id": str(uuid.uuid4()), "title": title, "description": desc,
                "budget": budget, "currency": "INR", "location": location,
                "category": cat, "skills": skills, "created_at": now_iso(),
            })


@app.on_event("startup")
async def startup():
    await seed()
    init_storage()


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
