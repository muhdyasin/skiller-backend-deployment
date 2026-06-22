"""Community groups — WhatsApp-style chat with text/image/share, reactions,
read receipts, typing indicators (no status bar). Real-time via WS."""
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from core import db, now_iso, get_current_user, ws_manager

from db.session import AsyncSessionLocal
from services.user_service import UserService

router = APIRouter(prefix="/api/community", tags=["community"])


# ---------- Models ----------
class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = ""
    avatar_url: str = ""
    member_usernames: List[str] = []
    is_dm: bool = False  # 1-1 DM is a group with 2 members + is_dm=True


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None


class MessageCreate(BaseModel):
    type: Literal["text", "image", "voice", "share"] = "text"
    text: str = ""
    media: str = ""  # for type=image | voice
    duration_ms: int = 0  # for type=voice
    share: Optional[dict] = None  # {"kind": "post"|"course"|"gig"|"creator", "id": "..."}

    @field_validator("text")
    @classmethod
    def _trim(cls, v: str) -> str:
        return (v or "").strip()[:4000]


class ReactionIn(BaseModel):
    emoji: str = Field(min_length=1, max_length=8)


# ---------- Helpers ----------
async def _require_member(group_id: str, user_id: str) -> dict:
    g = await db.groups.find_one({"id": group_id}, {"_id": 0})
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    if user_id not in g.get("members", []):
        raise HTTPException(status_code=403, detail="Not a member")
    return g


async def _broadcast_to_group(group: dict, payload: dict, exclude_user: Optional[str] = None):
    for member_id in group.get("members", []):
        if member_id == exclude_user:
            continue
        try:
            await ws_manager.send_to(member_id, payload)
        except Exception:
            pass


async def _user_summary(user_ids: List[str]) -> dict:

    async with AsyncSessionLocal() as pg_db:

        users = await UserService.get_users_by_ids(
            pg_db,
            user_ids
        )

    return {
        u.id: {
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "avatar_url": u.avatar_url,
        }
        for u in users
    }


# ---------- Group CRUD ----------
@router.post("/groups")
async def create_group(data: GroupCreate, current=Depends(get_current_user)):
    member_ids = {current["id"]}
    for un in data.member_usernames:
        async with AsyncSessionLocal() as pg_db:

            u = await UserService.get_user_by_username(
                pg_db,
                un.lower()
            )

        if u:
            member_ids.add(u.id)

    if data.is_dm:
        if len(member_ids) != 2:
            raise HTTPException(status_code=400, detail="DM requires exactly one other member")
        existing = await db.groups.find_one({
            "is_dm": True,
            "members": {"$all": list(member_ids), "$size": 2},
        })
        if existing:
            return await _enriched_group(existing, current["id"])

    doc = {
        "id": str(uuid.uuid4()),
        "name": data.name.strip(),
        "description": data.description.strip()[:300],
        "avatar_url": data.avatar_url.strip(),
        "members": list(member_ids),
        "admins": [current["id"]],
        "is_dm": data.is_dm,
        "created_by": current["id"],
        "created_at": now_iso(),
        "last_message_at": now_iso(),
        "last_message_preview": "",
    }
    await db.groups.insert_one(doc)
    return await _enriched_group(doc, current["id"])


@router.get("/groups")
async def list_my_groups(current=Depends(get_current_user)):
    cursor = db.groups.find(
        {"members": current["id"]}, {"_id": 0},
    ).sort("last_message_at", -1)
    groups = await cursor.to_list(200)
    out = []
    for g in groups:
        out.append(await _enriched_group(g, current["id"]))
    return out


@router.get("/groups/{group_id}")
async def get_group(group_id: str, current=Depends(get_current_user)):
    g = await _require_member(group_id, current["id"])
    return await _enriched_group(g, current["id"])


@router.patch("/groups/{group_id}")
async def update_group(group_id: str, data: GroupUpdate, current=Depends(get_current_user)):
    g = await _require_member(group_id, current["id"])
    if current["id"] not in g.get("admins", []):
        raise HTTPException(status_code=403, detail="Admins only")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.groups.update_one({"id": group_id}, {"$set": updates})
    g2 = await db.groups.find_one({"id": group_id}, {"_id": 0})
    return await _enriched_group(g2, current["id"])


@router.post("/groups/{group_id}/members")
async def add_member(group_id: str, body: dict, current=Depends(get_current_user)):
    g = await _require_member(group_id, current["id"])
    if current["id"] not in g.get("admins", []):
        raise HTTPException(status_code=403, detail="Admins only")
    username = (body.get("username") or "").lower().strip()
    if not username:
        raise HTTPException(status_code=400, detail="username required")
    
    async with AsyncSessionLocal() as pg_db:

        u = await UserService.get_user_by_username(
            pg_db,
            username
        )

    if not u:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    await db.groups.update_one({"id": group_id}, {"$addToSet": {"members": u.id}})
    return {"ok": True, "added": u.id}


@router.delete("/groups/{group_id}/members/{user_id}")
async def remove_member(group_id: str, user_id: str, current=Depends(get_current_user)):
    g = await _require_member(group_id, current["id"])
    if user_id != current["id"] and current["id"] not in g.get("admins", []):
        raise HTTPException(status_code=403, detail="Admins only (or self-leave)")
    await db.groups.update_one({"id": group_id}, {"$pull": {"members": user_id, "admins": user_id}})
    return {"ok": True}


# ---------- Messages ----------
@router.get("/groups/{group_id}/messages")
async def list_messages(group_id: str, limit: int = 50, before: Optional[str] = None,
                        current=Depends(get_current_user)):
    await _require_member(group_id, current["id"])
    q = {"group_id": group_id}
    if before:
        q["created_at"] = {"$lt": before}
    cursor = db.group_messages.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    msgs = await cursor.to_list(limit)
    msgs.reverse()
    sender_ids = list({m["sender_id"] for m in msgs})
    senders = await _user_summary(sender_ids)
    for m in msgs:
        m["sender"] = senders.get(m["sender_id"])
    return msgs


@router.post("/groups/{group_id}/messages")
async def send_message(group_id: str, data: MessageCreate, current=Depends(get_current_user)):
    g = await _require_member(group_id, current["id"])
    if data.type == "text" and not data.text:
        raise HTTPException(status_code=400, detail="text required")
    if data.type == "image" and not data.media:
        raise HTTPException(status_code=400, detail="media required")
    if data.type == "voice" and not data.media:
        raise HTTPException(status_code=400, detail="voice media required")
    if data.type == "share" and not data.share:
        raise HTTPException(status_code=400, detail="share payload required")

    msg = {
        "id": str(uuid.uuid4()),
        "group_id": group_id,
        "sender_id": current["id"],
        "type": data.type,
        "text": data.text,
        "media": data.media,
        "duration_ms": data.duration_ms if data.type == "voice" else 0,
        "share": data.share or {},
        "reactions": {},  # emoji -> [user_ids]
        "read_by": [current["id"]],
        "created_at": now_iso(),
    }
    await db.group_messages.insert_one(msg.copy())

    preview = data.text or {
        "image": "📷 Photo",
        "voice": "🎤 Voice note",
        "share": "🔗 Shared",
    }.get(data.type, "")
    await db.groups.update_one(
        {"id": group_id},
        {"$set": {"last_message_at": msg["created_at"], "last_message_preview": preview[:80]}},
    )

    async with AsyncSessionLocal() as pg_db:

        sender_user = await UserService.get_user(
            pg_db,
            current["id"]
        )

    sender = None

    if sender_user:
        sender = {
            "id": sender_user.id,
            "username": sender_user.username,
            "name": sender_user.name,
            "avatar_url": sender_user.avatar_url,
        }
        
    payload = {"type": "group_message", "data": {**msg, "sender": sender}}
    await _broadcast_to_group(g, payload, exclude_user=None)
    return payload["data"]


@router.post("/groups/{group_id}/messages/{message_id}/react")
async def react_message(group_id: str, message_id: str, data: ReactionIn,
                        current=Depends(get_current_user)):
    g = await _require_member(group_id, current["id"])
    msg = await db.group_messages.find_one({"id": message_id, "group_id": group_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    reactions = msg.get("reactions") or {}
    # toggle: if user already reacted with this emoji, remove; else add (and remove their other reactions)
    for emo, users in list(reactions.items()):
        if current["id"] in users:
            reactions[emo] = [u for u in users if u != current["id"]]
            if not reactions[emo]:
                reactions.pop(emo)
    if data.emoji not in (msg.get("reactions") or {}) or current["id"] not in msg["reactions"].get(data.emoji, []):
        reactions.setdefault(data.emoji, []).append(current["id"])
    await db.group_messages.update_one(
        {"id": message_id}, {"$set": {"reactions": reactions}},
    )
    payload = {
        "type": "group_reaction",
        "data": {"group_id": group_id, "message_id": message_id, "reactions": reactions},
    }
    await _broadcast_to_group(g, payload)
    return payload["data"]


@router.post("/groups/{group_id}/read")
async def mark_read(group_id: str, body: Optional[dict] = None,
                    current=Depends(get_current_user)):
    g = await _require_member(group_id, current["id"])
    body = body or {}
    upto = body.get("upto_created_at")
    q = {"group_id": group_id, "read_by": {"$ne": current["id"]}}
    if upto:
        q["created_at"] = {"$lte": upto}
    await db.group_messages.update_many(q, {"$addToSet": {"read_by": current["id"]}})
    payload = {
        "type": "group_read",
        "data": {"group_id": group_id, "user_id": current["id"], "upto": upto},
    }
    await _broadcast_to_group(g, payload, exclude_user=current["id"])
    return {"ok": True}
@router.post("/groups/{group_id}/typing")
async def typing(group_id: str, body: Optional[dict] = None,
                 current=Depends(get_current_user)):
    g = await _require_member(group_id, current["id"])
    is_typing = bool((body or {}).get("typing", True))
    payload = {
        "type": "group_typing",
        "data": {"group_id": group_id, "user_id": current["id"],
                 "username": current.get("username"), "typing": is_typing},
    }
    await _broadcast_to_group(g, payload, exclude_user=current["id"])
    return {"ok": True}


# ---------- Helpers ----------
async def _enriched_group(g: dict, viewer_id: str) -> dict:
    out = {k: v for k, v in g.items() if k != "_id"}
    members = await _user_summary(out.get("members", []))
    out["member_objs"] = list(members.values())
    if out.get("is_dm"):
        other = next((m for mid, m in members.items() if mid != viewer_id), None)
        if other:
            out["display_name"] = other.get("name") or other.get("username")
            out["display_avatar"] = other.get("avatar_url")
        else:
            out["display_name"] = out.get("name", "DM")
            out["display_avatar"] = out.get("avatar_url", "")
    else:
        out["display_name"] = out.get("name", "Group")
        out["display_avatar"] = out.get("avatar_url", "")
    # unread count for viewer
    unread = await db.group_messages.count_documents({
        "group_id": out["id"], "read_by": {"$ne": viewer_id},
        "sender_id": {"$ne": viewer_id},
    })
    out["unread"] = unread
    return out
