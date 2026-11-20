
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    select
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.auth import require_owner
from app.database import (
    Base,
    Conversation,
    Message,
    SessionLocal,
    get_db
)


# -----------------------------------------
# Database models
# -----------------------------------------

class HistoryPreference(Base):
    __tablename__ = "history_preferences"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    auto_save: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )


class ArchivedMessageEvent(Base):
    __tablename__ = "archived_message_events"

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "event_id",
            name="uq_conversation_event"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False
    )

    event_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False
    )


# -----------------------------------------
# API models
# -----------------------------------------

class HistorySettingsUpdate(BaseModel):
    auto_save: bool


class ArchiveRequest(BaseModel):
    event_id: UUID
    conversation_id: int = Field(gt=0)
    contact_id: UUID

    direction: Literal["incoming", "outgoing"]

    original_text: str = Field(
        min_length=1,
        max_length=10000
    )

    translated_text: str | None = Field(
        default=None,
        max_length=20000
    )

    source_language: str = Field(
        min_length=2,
        max_length=20
    )

    target_language: str = Field(
        min_length=2,
        max_length=20
    )

    engine_name: str = Field(
        default="unknown",
        max_length=50
    )


# -----------------------------------------
# Preferences
# -----------------------------------------

def get_preference(db: Session):
    preference = db.get(HistoryPreference, 1)

    if preference is None:
        preference = HistoryPreference(
            id=1,
            auto_save=False
        )
        db.add(preference)
        db.flush()

    return preference


router = APIRouter(
    prefix="/history-settings",
    tags=["History Settings"],
    dependencies=[Depends(require_owner)]
)

DB = Annotated[Session, Depends(get_db)]


@router.get("")
def read_history_settings(db: DB):
    preference = get_preference(db)
    result = {"auto_save": preference.auto_save}
    db.commit()
    return result


@router.put("")
def update_history_settings(
    data: HistorySettingsUpdate,
    db: DB
):
    preference = get_preference(db)
    preference.auto_save = data.auto_save

    db.commit()

    return {"auto_save": preference.auto_save}


# -----------------------------------------
# Save event from authenticated WebSocket
# -----------------------------------------

def archive_message(data: ArchiveRequest):
    with SessionLocal() as db:
        try:
            preference = get_preference(db)

            if not preference.auto_save:
                db.commit()
                return {
                    "status": "disabled",
                    "event_id": str(data.event_id)
                }

            conversation = db.get(
                Conversation,
                data.conversation_id
            )

            if conversation is None:
                raise ValueError(
                    "Conversation not found"
                )

            if conversation.contact_id != str(data.contact_id):
                raise ValueError(
                    "Contact does not match conversation"
                )

            existing = db.scalar(
                select(ArchivedMessageEvent).where(
                    ArchivedMessageEvent.conversation_id
                    == data.conversation_id,
                    ArchivedMessageEvent.event_id
                    == str(data.event_id)
                )
            )

            if existing is not None:
                return {
                    "status": "duplicate",
                    "event_id": str(data.event_id),
                    "message_id": existing.message_id
                }

            message = Message(
                conversation_id=data.conversation_id,
                direction=data.direction,
                original_text=data.original_text,
                translated_text=data.translated_text,
                source_language=data.source_language,
                target_language=data.target_language,
                engine_name=data.engine_name
            )

            db.add(message)
            db.flush()

            event = ArchivedMessageEvent(
                conversation_id=data.conversation_id,
                message_id=message.id,
                event_id=str(data.event_id)
            )

            db.add(event)
            message_id = message.id

            db.commit()

            return {
                "status": "saved",
                "event_id": str(data.event_id),
                "message_id": message_id
            }

        except IntegrityError:
            db.rollback()

            existing = db.scalar(
                select(ArchivedMessageEvent).where(
                    ArchivedMessageEvent.conversation_id
                    == data.conversation_id,
                    ArchivedMessageEvent.event_id
                    == str(data.event_id)
                )
            )

            if existing is None:
                raise

            return {
                "status": "duplicate",
                "event_id": str(data.event_id),
                "message_id": existing.message_id
            }
