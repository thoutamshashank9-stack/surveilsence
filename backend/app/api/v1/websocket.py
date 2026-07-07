from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.api.deps import get_event_bus
from app.api.websocket.manager import ConnectionManager
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Share single connection manager across endpoints via app.state
@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    manager: ConnectionManager = websocket.app.state.websocket_manager
    await manager.connect(websocket)
    logger.info("New WebSocket connection established", client=str(websocket.client))
    
    try:
        while True:
            # Keep connection open and listen for client messages (heartbeats, etc)
            data = await websocket.receive_text()
            # Echo back for heartbeat check
            await manager.send_personal_message({"type": "pong"}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket connection disconnected", client=str(websocket.client))
    except Exception as e:
        manager.disconnect(websocket)
        logger.error("Error in WebSocket connection session", client=str(websocket.client), error=str(e))
