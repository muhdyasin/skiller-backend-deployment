"""Ads."""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from core import db, now_iso, get_current_user, AdCreate, AdStatus

router = APIRouter(prefix="/api/ads", tags=["ads"])


@router.post("")
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


@router.get("/mine")
async def my_ads(current=Depends(get_current_user)):
    return await db.ad_campaigns.find({"owner_id": current["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


@router.get("/active")
async def active_ads(limit: int = 3):
    ads = await db.ad_campaigns.find({"status": "active"}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    if ads:
        await db.ad_campaigns.update_many(
            {"id": {"$in": [a["id"] for a in ads]}},
            {"$inc": {"impressions": 1}}
        )
    return ads


@router.post("/{ad_id}/click")
async def ad_click(ad_id: str):
    ad = await db.ad_campaigns.find_one({"id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    await db.ad_campaigns.update_one(
        {"id": ad_id}, {"$inc": {"clicks": 1, "spend": 8}}
    )
    return {"ok": True}


@router.patch("/{ad_id}/status")
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


@router.delete("/{ad_id}")
async def delete_ad(ad_id: str, current=Depends(get_current_user)):
    ad = await db.ad_campaigns.find_one({"id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    if ad["owner_id"] != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.ad_campaigns.delete_one({"id": ad_id})
    return {"ok": True}
