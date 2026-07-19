"""Gigs — list, apply, plus creator CRUD + applicants management."""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from core import (
    db, now_iso, get_current_user, require_creator, award_xp,
    GigApply, GigCreate, GigUpdate, ApplicationStatusIn,
)
from notifications_service import create_notification

from sqlalchemy.ext.asyncio import AsyncSession

from db.dependencies import get_db
from services.gig_service import GigService
from services.application_service import ApplicationService


router = APIRouter(prefix="/api/gigs", tags=["gigs"])


@router.get("")
async def list_gigs(
    pg_db: AsyncSession = Depends(get_db)
):
    return await GigService.list_gigs(
        pg_db
    )
    

@router.get("/mine")
async def my_gigs(
    current=Depends(require_creator),
    pg_db: AsyncSession = Depends(get_db)
):
    return await GigService.get_creator_gigs_with_counts(
        pg_db,
        current["id"]
    )


@router.post("")
async def create_gig(
    data: GigCreate,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    gig = await GigService.create_gig(
        db=pg_db,
        owner_id=current["id"],
        owner_username=current["username"],
        owner_name=current["name"],
        title=data.title,
        description=data.description,
        budget=data.budget,
        currency="INR",
        location=data.location,
        category=data.category,
        skills=data.skills
    )

    return gig


@router.patch("/{gig_id}")
async def update_gig(
    gig_id: str,
    data: GigUpdate,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    gig = await GigService.get_gig(
        pg_db,
        gig_id
    )

    if not gig:
        raise HTTPException(
            status_code=404,
            detail="Gig not found"
        )

    if (
        gig.owner_id != current["id"]
        and current.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    updates = {
        k: v
        for k, v in data.model_dump().items()
        if v is not None
    }

    return await GigService.update_gig(
        pg_db,
        gig,
        updates
    )

@router.delete("/{gig_id}")
async def delete_gig(
    gig_id: str,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    gig = await GigService.get_gig(
        pg_db,
        gig_id
    )

    if not gig:
        raise HTTPException(
            status_code=404,
            detail="Gig not found"
        )

    if (
        gig.owner_id != current["id"]
        and current.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    await GigService.delete_gig(
        pg_db,
        gig
    )

    return {"ok": True}


@router.post("/{gig_id}/apply")
async def apply_gig(
    gig_id: str,
    data: GigApply,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    gig = await GigService.get_gig(
        pg_db,
        gig_id
    )

    if not gig:
        raise HTTPException(
            status_code=404,
            detail="Gig not found"
        )

    existing = await ApplicationService.get_user_application(
        pg_db,
        gig_id,
        current["id"]
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Already applied"
        )

    application = await ApplicationService.create_application(
        db=pg_db,
        gig_id=gig_id,
        user_id=current["id"],
        username=current["username"],
        name=current["name"],
        email=current["email"],
        avatar_url=current.get("avatar_url", ""),
        message=data.message,
        status="pending"
    )

    if gig.owner_id:
        await create_notification(
            gig.owner_id,
            "gig_application",
            f"@{current['username']} applied to your gig",
            actor_id=current["id"],
            meta={"gig_id": gig_id},
        )

    return {
        "ok": True,
        "application_id": application.id
    }

@router.get("/{gig_id}/applicants")
async def list_applicants(
    gig_id: str,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    gig = await GigService.get_gig(
        pg_db,
        gig_id
    )

    if not gig:
        raise HTTPException(
            status_code=404,
            detail="Gig not found"
        )

    if (
        gig.owner_id != current["id"]
        and current.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    applications = (
        await ApplicationService
        .get_gig_applications(
            pg_db,
            gig_id
        )
    )

    return {
        "gig": {
            "id": gig.id,
            "title": gig.title
        },
        "applications": applications
    }
    

@router.patch("/applications/{app_id}/status")
async def set_application_status(
    app_id: str,
    data: ApplicationStatusIn,
    current=Depends(get_current_user),
    pg_db: AsyncSession = Depends(get_db)
):
    application = (
        await ApplicationService
        .get_application_by_id(
            pg_db,
            app_id
        )
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    gig = await GigService.get_gig(
        pg_db,
        application.gig_id
    )

    if not gig:
        raise HTTPException(
            status_code=404,
            detail="Gig not found"
        )

    if (
        gig.owner_id != current["id"]
        and current.get("role") != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    application = (
        await ApplicationService
        .update_status(
            pg_db,
            application,
            data.status
        )
    )

    if (
        data.status in
        ["shortlisted", "hired", "rejected"]
    ):
        await create_notification(
            application.user_id,
            "application_status",
            f"Your application for '{gig.title}' was {data.status}",
            meta={"gig_id": gig.id}
        )

    return {
        "ok": True,
        "status": application.status
    }
