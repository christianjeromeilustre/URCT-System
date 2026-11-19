
from datetime import datetime, timezone
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.websocket import manager

from pydantic import BaseModel

from fastapi import HTTPException

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException

from pydantic import BaseModel

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




class TranslationRequest(BaseModel):
    text: str
    target_language: str


DEMO_TRANSLATIONS = {
    ("안녕하세요.", "en"): "Hello.",
    ("만나서 반갑습니다.", "en"): "Nice to meet you.",
    ("오늘 기분이 어떻습니까?", "en"):
        "How are you feeling today?",
    ("Hello.", "ko"): "안녕하세요.",
    ("Nice to meet you.", "ko"): "만나서 반갑습니다."
}


@app.post("/translate")
async def translate(request: TranslationRequest):
    text = request.text.strip()
    target = request.target_language

    if not text:
        raise HTTPException(400, "Text is required.")

    if target not in ("ko", "en"):
        raise HTTPException(400, "Unsupported language.")

    translated = DEMO_TRANSLATIONS.get((text, target))

    return {
        "original_text": text,
        "translated_text": translated,
        "target_language": target,
        "engine": "demo",
        "translation_success": translated is not None
    }
    
    
from app.language_manager import (
    language_manager,
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE
)


@app.get("/languages")
async def get_languages():
    return {
        "source_language": DEFAULT_SOURCE_LANGUAGE,
        "default_target_language": DEFAULT_TARGET_LANGUAGE,
        "installed_languages": (
            language_manager.get_installed_languages()
        )
    }


@app.get("/languages/{code}")
async def get_language(code: str):
    language = language_manager.get_language(code)

    if language is None:
        raise HTTPException(
            status_code=404,
            detail="Language module not installed"
        )

    return language