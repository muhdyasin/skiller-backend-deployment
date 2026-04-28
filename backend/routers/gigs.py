"""Gigs."""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from core import db, now_iso, get_current_user, award_xp, GigApply

router = APIRouter(prefix="/api/gigs", tags=["gigs"])


@router.get("")
async def list_gigs():
    return await db.gigs.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("/{gig_id}/apply")
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
