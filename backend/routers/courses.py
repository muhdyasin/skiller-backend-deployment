"""Courses CRUD + enrollment."""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from core import db, now_iso, get_current_user, award_xp, CourseCreate, CourseUpdate

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("")
async def list_courses():
    return await db.courses.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.get("/{course_id}")
async def get_course(course_id: str):
    c = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return c


@router.post("")
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


@router.patch("/{course_id}")
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


@router.delete("/{course_id}")
async def delete_course(course_id: str, current=Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.get("owner_id") != current["id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    await db.courses.delete_one({"id": course_id})
    return {"ok": True}


@router.post("/{course_id}/enroll")
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
