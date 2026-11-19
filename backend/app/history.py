from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Conversation, Message, get_db


router = APIRouter(
    prefix="/history",
    tags=["Conversation History"]
)

DB = Annotated[Session, Depends(get_db)]


class ConversationCreate(BaseModel):
    platform: str = Field(min_length=1, max_length=100)
    contact_name: str = Field(min_length=1, max_length=200)
    language: str = "en"
    mode: str = "auto"


class MessageCreate(BaseModel):
    direction: Literal["incoming", "outgoing"]
    original_text: str = Field(min_length=1)
    translated_text: str | None = None
    source_language: str
    target_language: str
    engine_name: str = "unknown"


@router.post("/conversations", status_code=201)
def create_conversation(data: ConversationCreate, db: DB):
    conversation = Conversation(**data.model_dump())

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return {
        "id": conversation.id,
        "platform": conversation.platform,
        "contact_name": conversation.contact_name,
        "language": conversation.language,
        "mode": conversation.mode
    }


@router.get("/conversations")
def list_conversations(db: DB):
    conversations = db.scalars(
        select(Conversation).order_by(Conversation.id.desc())
    ).all()

    return [
        {
            "id": c.id,
            "platform": c.platform,
            "contact_name": c.contact_name,
            "language": c.language,
            "mode": c.mode
        }
        for c in conversations
    ]


@router.post(
    "/conversations/{conversation_id}/messages",
    status_code=201
)
def add_message(
    conversation_id: int,
    data: MessageCreate,
    db: DB
):
    conversation = db.get(Conversation, conversation_id)

    if conversation is None:
        raise HTTPException(404, "Conversation not found")

    message = Message(
        conversation_id=conversation_id,
        **data.model_dump()
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "original_text": message.original_text,
        "translated_text": message.translated_text
    }


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, db: DB):
    conversation = db.get(Conversation, conversation_id)

    if conversation is None:
        raise HTTPException(404, "Conversation not found")

    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    ).all()

    return [
        {
            "id": m.id,
            "direction": m.direction,
            "original_text": m.original_text,
            "translated_text": m.translated_text,
            "source_language": m.source_language,
            "target_language": m.target_language
        }
        for m in messages
    ]


@router.delete("/messages/{message_id}")
def delete_message(message_id: int, db: DB):
    message = db.get(Message, message_id)

    if message is None:
        raise HTTPException(404, "Message not found")

    db.delete(message)
    db.commit()

    return {"deleted": True, "message_id": message_id}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: DB):
    conversation = db.get(Conversation, conversation_id)

    if conversation is None:
        raise HTTPException(404, "Conversation not found")

    db.delete(conversation)
    db.commit()

    return {
        "deleted": True,
        "conversation_id": conversation_id
    }