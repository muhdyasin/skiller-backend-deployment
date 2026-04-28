"""Gigs — list, apply, plus creator CRUD + applicants management."""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from core import (
    db, now_iso, get_current_user, require_creator, award_xp,
    GigApply, GigCreate, GigUpdate, ApplicationStatusIn,
)
from notifications_service import create_notification

router = APIRouter(prefix="/api/gigs", tags=["gigs"])


@router.get("")
async def list_gigs():
    return await db.gigs.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.get("/mine")
async def my_gigs(current=Depends(require_creator)):
    gigs = await db.gigs.find({"owner_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for g in gigs:
        g["application_count"] = await db.applications.count_documents({"gig_id": g["id"]})
    return gigs


@router.post("")
async def create_gig(data: GigCreate, current=Depends(require_creator)):
    gig = {
        "id": str(uuid.uuid4()),
        "owner_id": current["id"],
        "owner_username": current["username"],
        "owner_name": current["name"],
        "title": data.title,
        "description": data.description,
        "budget": data.budget,
        "currency": "INR",
        "location": data.location,
        "category": data.category,
        "skills": data.skills,
        "created_at": now_iso(),
    }
    await db.gigs.insert_one(gig.copy())
    return gig


@router.patch("/{gig_id}")
async def update_gig(gig_id: str, data: GigUpdate, current=Depends(get_current_user)):
    gig = await db.gigs.find_one({"id": gig_id})
    if not gig:
        raise HTTPException(status_code=404, detail="Gig not found")
    if gig.get("owner_id") != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.gigs.update_one({"id": gig_id}, {"$set": updates})
    return await db.gigs.find_one({"id": gig_id}, {"_id": 0})


@router.delete("/{gig_id}")
async def delete_gig(gig_id: str, current=Depends(get_current_user)):
    gig = await db.gigs.find_one({"id": gig_id})
    if not gig:
        raise HTTPException(status_code=404, detail="Gig not found")
    if gig.get("owner_id") != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.gigs.delete_one({"id": gig_id})
    await db.applications.delete_many({"gig_id": gig_id})
    return {"ok": True}


@router.post("/{gig_id}/apply")
async def apply_gig(gig_id: str, data: GigApply, current=Depends(get_current_user)):
    gig = await db.gigs.find_one({"id": gig_id})
    if not gig:
        raise HTTPException(status_code=404, detail="Gig not found")
    application = {
        "id": str(uuid.uuid4()),
        "gig_id": gig_id,
        "user_id": current["id"],
        "username": current["username"],
        "name": current["name"],
        "email": current["email"],
        "avatar_url": current.get("avatar_url", ""),
        "message": data.message,
        "status": "pending",
        "created_at": now_iso(),
    }
    await db.applications.insert_one(application.copy())
    await award_xp(current["id"], "gig_apply")
    if gig.get("owner_id"):
        await create_notification(
            gig["owner_id"], "gig_application",
            f"@{current['username']} applied to your gig",
            actor_id=current["id"], meta={"gig_id": gig_id},
        )
    return {"ok": True, "application": application}


@router.get("/{gig_id}/applicants")
async def list_applicants(gig_id: str, current=Depends(get_current_user)):
    gig = await db.gigs.find_one({"id": gig_id})
    if not gig:
        raise HTTPException(status_code=404, detail="Gig not found")
    if gig.get("owner_id") != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    apps = await db.applications.find(
        {"gig_id": gig_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return {"gig": {k: gig[k] for k in gig if k != "_id"}, "applications": apps}


@router.patch("/applications/{app_id}/status")
async def set_application_status(app_id: str, data: ApplicationStatusIn, current=Depends(get_current_user)):
    app_doc = await db.applications.find_one({"id": app_id})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Application not found")
    gig = await db.gigs.find_one({"id": app_doc["gig_id"]})
    if not gig:
        raise HTTPException(status_code=404, detail="Gig not found")
    if gig.get("owner_id") != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.applications.update_one({"id": app_id}, {"$set": {"status": data.status}})
    if data.status in ("shortlisted", "hired", "rejected") and app_doc.get("user_id"):
        await create_notification(
            app_doc["user_id"], "application_status",
            f"Your application for '{gig.get('title','a gig')}' was {data.status}",
            meta={"gig_id": gig["id"]},
        )
    return {"ok": True}
