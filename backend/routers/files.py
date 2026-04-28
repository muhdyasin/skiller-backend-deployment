"""Object storage upload + serve."""
import uuid
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from starlette.responses import Response as StarletteResponse
from core import db, now_iso, get_current_user, APP_NAME, put_object, get_object

router = APIRouter(prefix="/api", tags=["files"])

ALLOWED_MIME = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/webm", "video/quicktime",
}


@router.post("/upload")
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


@router.get("/files/{path:path}")
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
