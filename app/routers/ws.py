from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json(
                {"event": "ping", "message": "connection alive"}
            )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)