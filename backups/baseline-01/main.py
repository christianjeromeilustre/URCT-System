
from datetime import datetime, timezone
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.websocket import manager

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="URCT - Universal Real-Time Chat Translator",
    description="Real-time multilingual communication platform",
    version="1.1.0"
)


@app.get("/")
async def home():
    return {
        "project": "URCT",
        "name": "Universal Real-Time Chat Translator",
        "version": "1.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):

    await manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            receiver_id = data.get("receiver_id")
            message_text = data.get("message")

            if not isinstance(receiver_id, str) or not receiver_id:
                await websocket.send_json({
                    "type": "error",
                    "message": "receiver_id is required."
                })
                continue

            if not isinstance(message_text, str) or not message_text.strip():
                await websocket.send_json({
                    "type": "error",
                    "message": "message must be a non-empty string."
                })
                continue

            chat_message = {
                "type": "chat_message",
                "sender_id": user_id,
                "receiver_id": receiver_id,
                "original_text": message_text,
                "translated_text": None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            delivered = await manager.send_message(
                receiver_id,
                chat_message
            )

            if not delivered:
                await websocket.send_json({
                    "type": "delivery_error",
                    "receiver_id": receiver_id,
                    "message": "Receiver is not connected."
                })

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected: %s", user_id)

    except Exception:
        logging.exception("WebSocket error for user: %s", user_id)

    finally:
        manager.disconnect(user_id, websocket)
