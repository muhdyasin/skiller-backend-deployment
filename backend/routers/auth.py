"""Auth, password reset, email verification."""
import os
import uuid
import logging
import secrets
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from core import (
    db, now, now_iso, hash_password, verify_password, create_access_token,
    get_current_user, get_user_by_id, award_xp, FRONTEND_URL, APP_ENV,
    RegisterIn, LoginIn, ForgotPasswordIn, ResetPasswordIn,
    generate_referral_code, ensure_token_wallet, trial_premium_until,
)
from notifications_service import send_email, password_reset_html, email_verification_html

from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from services.user_service import UserService

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger("skiller")


class VerifyEmailIn(BaseModel):
    token: str


async def update_streak_on_login(user_id: str):
    async def update_streak_on_login(
    user_id: str,
    pg_db: AsyncSession
):
        user = await UserService.get_user(
            pg_db,
            user_id
        )

        if not user:
            return

        today = date.today().isoformat()
        last = user.last_login_date
        streak = user.streak or 0

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

        await UserService.update_streak(
            pg_db,
            user,
            streak,
            today
        )

        await award_xp(
            user_id,
            "daily_login"
        )
    await award_xp(user_id, "daily_login")


@router.post("/register")
async def register(data: RegisterIn,
                   pg_db: AsyncSession = Depends(get_db)):
    email = data.email.lower().strip()
    if await UserService.get_user_by_email(pg_db,email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await UserService.get_user_by_username(pg_db,data.username.lower().strip()):
        raise HTTPException(status_code=400, detail="Username already taken")
    user_id = str(uuid.uuid4())

    # Generate a unique referral code
    for _ in range(5):
        ref_code = generate_referral_code()
        if not await UserService.get_user_by_referral_code(pg_db,ref_code):
            break

    # Resolve who referred this user (via stored cookie/body field)
    referred_by = None
    incoming_ref = (data.referral_code or "").strip().upper() if data.referral_code else None
    if incoming_ref:
        ref_user = await UserService.get_user_by_referral_code(pg_db,incoming_ref)
        if ref_user:
            referred_by = ref_user.id

    user = await UserService.create_user(
        pg_db,
        id=user_id,
        email=email,
        username=data.username.lower().strip(),
        name=data.name.strip(),
        password_hash=hash_password(data.password),
        bio="",
        avatar_url="",
        role=data.role,
        xp=0,
        badges=[],
        streak=0,
        last_login_date=None,
        referral_code=ref_code,
        referred_by=referred_by,
        premium_until=trial_premium_until(),
        plan="trial",
        email_verified=False,
    )
    
    await ensure_token_wallet(user_id)
    if referred_by:
        await db.referrals.insert_one({
            "id": str(uuid.uuid4()),
            "referrer_id": referred_by,
            "referred_user_id": user_id,
            "status": "pending",  # → "rewarded" after first paid subscription
            "created_at": now_iso(),
        })
    await update_streak_on_login(user_id)
    # fire-and-forget verification email
    try:
        await _issue_verification_token(user_id, email, data.name.strip())
    except Exception as e:
        logger.warning(f"Verify email dispatch failed: {e}")
    token = create_access_token(user_id, email)
    return {"token": token, "user": await get_user_by_id(user_id)}


async def _issue_verification_token(user_id: str, email: str, name: str):
    token = secrets.token_urlsafe(32)
    expires_dt = now() + timedelta(days=7)
    await db.email_verification_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "email": email,
        "token": token,
        "used": False,
        "expires_at_dt": expires_dt,  # TTL-indexed
        "created_at": now_iso(),
    })
    link = f"{FRONTEND_URL.rstrip('/')}/verify-email/{token}" if FRONTEND_URL else f"/verify-email/{token}"
    if APP_ENV != "production":
        logger.info(f"EMAIL_VERIFICATION_LINK for {email}: {link}")
    await send_email(
        to_email=email,
        subject="Verify your Skiller email",
        html=email_verification_html(name or "there", link),
    )


@router.post("/resend-verification")
async def resend_verification(current=Depends(get_current_user)):
    if current.get("email_verified"):
        return {"ok": True, "already_verified": True}
    # rate-limit: one email per 60s
    recent = await db.email_verification_tokens.find_one(
        {"user_id": current["id"], "used": False},
        sort=[("created_at", -1)],
    )
    if recent:
        try:
            ca = datetime.fromisoformat(recent["created_at"])
            if (now() - ca).total_seconds() < 60:
                raise HTTPException(status_code=429, detail="Please wait a minute before requesting another email")
        except (ValueError, TypeError):
            pass
    try:
        await _issue_verification_token(current["id"], current["email"], current.get("name", ""))
    except Exception as e:
        logger.warning(f"resend failed: {e}")
        raise HTTPException(status_code=500, detail="Could not send verification email")
    return {"ok": True}


@router.post("/verify-email")
async def verify_email(data: VerifyEmailIn,
                       pg_db: AsyncSession = Depends(get_db)):
    rec = await db.email_verification_tokens.find_one({"token": data.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired link")
    try:
        exp = rec["expires_at_dt"]
        if exp.tzinfo is None:
            from datetime import timezone as _tz
            exp = exp.replace(tzinfo=_tz.utc)
        if exp < now():
            raise HTTPException(status_code=400, detail="Verification link expired")
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid link")
    
    user = await UserService.get_user(
        pg_db,
        rec["user_id"]
    )

    if user:
        await UserService.update_user(
            pg_db,
            user,
            {
                "email_verified": True
            }
        )
    await db.email_verification_tokens.update_one(
        {"token": data.token}, {"$set": {"used": True}},
    )
    # +25 XP reward for verifying
    try:
        await award_xp(rec["user_id"], "email_verified", amount=25)
    except Exception:
        pass
    return {"ok": True}


@router.post("/login")
async def login(data: LoginIn,
                pg_db: AsyncSession = Depends(get_db)):
    email = data.email.lower().strip()
    user = await UserService.get_user_by_email(pg_db,email)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await update_streak_on_login(user.id)
    token = create_access_token(user.id, email)
    return {"token": token, "user": await get_user_by_id(user.id)}


@router.get("/me")
async def me(current=Depends(get_current_user)):
    await update_streak_on_login(current["id"])
    return await get_user_by_id(current["id"])


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordIn,
                          pg_db: AsyncSession = Depends(get_db)):
    email = data.email.lower().strip()
    user = await UserService.get_user_by_email(pg_db,email)
    if user:
        token = secrets.token_urlsafe(32)
        expires_dt = now() + timedelta(hours=1)
        await db.password_reset_tokens.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user.id,
            "token": token,
            "used": False,
            "expires_at": expires_dt.isoformat(),
            "expires_at_dt": expires_dt,  # used by Mongo TTL index
            "created_at": now_iso(),
        })
        link = f"{FRONTEND_URL.rstrip('/')}/reset-password/{token}" if FRONTEND_URL else f"/reset-password/{token}"
        if APP_ENV != "production":
            logger.info(f"PASSWORD_RESET_LINK for {email}: {link}")
        try:
            await send_email(
                to_email=email,
                subject="Reset your Skiller password",
                html=password_reset_html(user.name, link),
            )
        except Exception as e:
            logger.warning(f"Reset email send failed: {e}")
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordIn,
                         pg_db: AsyncSession = Depends(get_db)):
    rec = await db.password_reset_tokens.find_one({"token": data.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    try:
        if datetime.fromisoformat(rec["expires_at"]) < now():
            raise HTTPException(status_code=400, detail="Token expired")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid token")
    
    user = await UserService.get_user(
        pg_db,
        rec["user_id"]
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    await UserService.update_password(
        pg_db,
        user,
        hash_password(data.new_password)
    )
    await db.password_reset_tokens.update_one({"token": data.token}, {"$set": {"used": True}})
    return {"ok": True}
