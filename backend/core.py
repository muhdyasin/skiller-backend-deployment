"""Shared core: db, auth, xp/badges, ws_manager, storage, helpers, models."""
from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import json
import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Set, Dict

import bcrypt
import jwt
import requests

from fastapi import HTTPException, Request, WebSocket
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, field_validator

from db.session import AsyncSessionLocal
from models.xp_event import XPEvent
from services.user_service import UserService

logger = logging.getLogger("skiller")
logging.basicConfig(level=logging.INFO)

# ---------- DB ----------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"
APP_NAME = os.environ.get("APP_NAME", "skiller")
APP_ENV = os.environ.get("APP_ENV", "development")  # "production" suppresses dev logs
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:admin@skiller.app")

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
storage_key: Optional[str] = None


# ---------- Time / hashing / JWT ----------
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


async def get_user_by_id(user_id: str):
    
    async with AsyncSessionLocal() as pg_db:

        return await UserService.get_user_dict(
            pg_db,
            user_id
        )

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


async def require_creator(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") not in ("creator", "admin"):
        raise HTTPException(status_code=403, detail="Creator account required")
    return user


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

    try:
        async with AsyncSessionLocal() as pg_db:

            pg_db.add(
                XPEvent(
                    user_id=user_id,
                    reason=reason,
                    amount=amount,
                    meta=meta or {}
                )
            )

            await pg_db.commit()

    except Exception as e:
        logger.error(
            f"Postgres XP write failed: {e}"
        )
    await check_badges(user_id)


async def check_badges(user_id: str):
    from notifications_service import create_notification  # avoid circular import on startup
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


# ---------- WebSocket manager ----------
class WSManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

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


# ---------- Referral / Tokens / Subscription helpers ----------
TRIAL_DAYS = 30
REFERRAL_REWARD_TOKENS = 500


def generate_referral_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()


def trial_premium_until() -> datetime:
    return now() + timedelta(days=TRIAL_DAYS)


async def ensure_token_wallet(user_id: str):
    existing = await db.token_wallets.find_one({"user_id": user_id})
    if not existing:
        await db.token_wallets.insert_one({
            "user_id": user_id,
            "balance": 0,
            "lifetime_earned": 0,
            "lifetime_spent": 0,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })


async def credit_tokens(user_id: str, amount: int, reason: str, meta: Optional[dict] = None) -> int:
    if amount <= 0:
        return 0
    await ensure_token_wallet(user_id)
    res = await db.token_wallets.find_one_and_update(
        {"user_id": user_id},
        {
            "$inc": {"balance": amount, "lifetime_earned": amount},
            "$set": {"updated_at": now_iso()},
        },
        return_document=True,
        projection={"_id": 0, "balance": 1},
    )
    await db.token_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "credit",
        "amount": amount,
        "reason": reason,
        "meta": meta or {},
        "balance_after": res["balance"] if res else amount,
        "created_at": now_iso(),
    })
    return res["balance"] if res else amount


async def debit_tokens(user_id: str, amount: int, reason: str, meta: Optional[dict] = None) -> int:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    await ensure_token_wallet(user_id)
    wallet = await db.token_wallets.find_one({"user_id": user_id}, {"_id": 0, "balance": 1})
    if not wallet or wallet.get("balance", 0) < amount:
        raise HTTPException(status_code=400, detail="Insufficient token balance")
    res = await db.token_wallets.find_one_and_update(
        {"user_id": user_id, "balance": {"$gte": amount}},
        {
            "$inc": {"balance": -amount, "lifetime_spent": amount},
            "$set": {"updated_at": now_iso()},
        },
        return_document=True,
        projection={"_id": 0, "balance": 1},
    )
    if not res:
        raise HTTPException(status_code=400, detail="Insufficient token balance")
    await db.token_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "debit",
        "amount": amount,
        "reason": reason,
        "meta": meta or {},
        "balance_after": res["balance"],
        "created_at": now_iso(),
    })
    return res["balance"]


def is_premium_active(user: dict) -> bool:
    until = user.get("premium_until")
    if not until:
        return False
    try:
        if isinstance(until, str):
            until = datetime.fromisoformat(until)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return until > now()
    except Exception:
        return False


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
    role: str = "student"
    referral_code: Optional[str] = None

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str) -> str:
        v = (v or "student").lower().strip()
        if v not in {"student", "creator"}:
            raise ValueError("role must be 'student' or 'creator'")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


class PostCreate(BaseModel):
    caption: str = ""
    media: str
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


class GigCreate(BaseModel):
    title: str
    description: str
    budget: int = 0
    location: str = "Remote"
    category: str = "General"
    skills: List[str] = []


class GigUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[int] = None
    location: Optional[str] = None
    category: Optional[str] = None
    skills: Optional[List[str]] = None


class ApplicationStatusIn(BaseModel):
    status: str  # pending|shortlisted|hired|rejected

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        if v not in {"pending", "shortlisted", "hired", "rejected"}:
            raise ValueError("invalid status")
        return v


class RoleUpgradeIn(BaseModel):
    role: str  # creator only

    @field_validator("role")
    @classmethod
    def _validate(cls, v: str) -> str:
        if v != "creator":
            raise ValueError("Only upgrade to 'creator' is supported")
        return v


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
    status: str


class PushSubscribeIn(BaseModel):
    subscription: dict


class PushUnsubscribeIn(BaseModel):
    endpoint: str
