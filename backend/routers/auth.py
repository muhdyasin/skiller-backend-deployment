"""Auth, password reset."""
import os
import uuid
import logging
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends

from core import (
    db, now, now_iso, hash_password, verify_password, create_access_token,
    get_current_user, get_user_by_id, award_xp, FRONTEND_URL,
    RegisterIn, LoginIn, ForgotPasswordIn, ResetPasswordIn,
)
from notifications_service import send_email, password_reset_html

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("skiller")


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


@router.post("/register")
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
        "role": data.role, "xp": 0, "badges": [], "streak": 0,
        "last_login_date": None, "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    await update_streak_on_login(user_id)
    token = create_access_token(user_id, email)
    return {"token": token, "user": await get_user_by_id(user_id)}


@router.post("/login")
async def login(data: LoginIn):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await update_streak_on_login(user["id"])
    token = create_access_token(user["id"], email)
    return {"token": token, "user": await get_user_by_id(user["id"])}


@router.get("/me")
async def me(current=Depends(get_current_user)):
    await update_streak_on_login(current["id"])
    return await get_user_by_id(current["id"])


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordIn):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if user:
        token = secrets.token_urlsafe(32)
        expires_dt = now() + timedelta(hours=1)
        await db.password_reset_tokens.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "token": token,
            "used": False,
            "expires_at": expires_dt.isoformat(),
            "expires_at_dt": expires_dt,  # used by Mongo TTL index
            "created_at": now_iso(),
        })
        link = f"{FRONTEND_URL.rstrip('/')}/reset-password/{token}" if FRONTEND_URL else f"/reset-password/{token}"
        logger.info(f"PASSWORD_RESET_LINK for {email}: {link}")
        try:
            await send_email(
                to_email=email,
                subject="Reset your Skiller password",
                html=password_reset_html(user.get("name", ""), link),
            )
        except Exception as e:
            logger.warning(f"Reset email send failed: {e}")
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
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
