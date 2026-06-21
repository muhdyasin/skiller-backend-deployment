"""WebSocket — token-authenticated, registers in ws_manager."""
import logging
import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from db.session import AsyncSessionLocal
from services.user_service import UserService

from core import db, ws_manager, JWT_SECRET, JWT_ALG

router = APIRouter()
logger = logging.getLogger("skiller")


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = payload["sub"]
        async with AsyncSessionLocal() as pg_db:

            user = await UserService.get_user(
                pg_db,
                user_id
            )

            if not user:
                await websocket.close(code=4401)
                return
    except Exception:
        await websocket.close(code=4401)
        return

    async with ws_manager.lock:
        ws_manager.connections.setdefault(user_id, set()).add(websocket)
    try:
        await websocket.send_json({"type": "connected", "user_id": user_id})
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WS error: {e}")
    finally:
        await ws_manager.disconnect(user_id, websocket)
