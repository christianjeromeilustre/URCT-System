from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    UniqueConstraint,
    select
)
from sqlalchemy.orm import (
    Session,
    Mapped,
    mapped_column
)

from app.database import Base, get_db


# ---------------------------------------
# Database model
# ---------------------------------------

class ConversationSetting(Base):
    __tablename__ = "conversation_settings"

    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "contact_id",
            name="uq_site_contact_settings"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    site_id: Mapped[str] = mapped_column(String(100))
    contact_id: Mapped[str] = mapped_column(String(200))

    recipient_language: Mapped[str] = mapped_column(
        String(20),
        default="en"
    )

    language_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    mode: Mapped[str] = mapped_column(
        String(30),
        default="auto"
    )

    translation_style: Mapped[str] = mapped_column(
        String(30),
        default="natural"
    )

    auto_detect: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------
# Request schema
# ---------------------------------------

class SettingsUpdate(BaseModel):
    recipient_language: str = "en"
    language_confirmed: bool = False

    mode: Literal[
        "auto",
        "social",
        "professional",
        "interview",
        "technical"
    ] = "auto"

    translation_style: Literal[
        "natural",
        "literal",
        "cultural"
    ] = "natural"

    auto_detect: bool = True


DEFAULT_SETTINGS = SettingsUpdate()

router = APIRouter(
    prefix="/conversation-settings",
    tags=["Conversation Settings"]
)

DB = Annotated[Session, Depends(get_db)]


def serialize(setting):
    return {
        "site_id": setting.site_id,
        "contact_id": setting.contact_id,
        "recipient_language": setting.recipient_language,
        "language_confirmed": setting.language_confirmed,
        "mode": setting.mode,
        "translation_style": setting.translation_style,
        "auto_detect": setting.auto_detect
    }


def find_setting(db, site_id, contact_id):
    return db.scalar(
        select(ConversationSetting).where(
            ConversationSetting.site_id == site_id,
            ConversationSetting.contact_id == contact_id
        )
    )


# ---------------------------------------
# Read current settings
# ---------------------------------------

@router.get("/{site_id}/{contact_id}")
def get_settings(
    site_id: str,
    contact_id: str,
    db: DB
):
    setting = find_setting(db, site_id, contact_id)

    if setting is None:
        return {
            "site_id": site_id,
            "contact_id": contact_id,
            **DEFAULT_SETTINGS.model_dump(),
            "saved": False
        }

    return {
        **serialize(setting),
        "saved": True
    }


# ---------------------------------------
# Save or update settings
# ---------------------------------------

@router.put("/{site_id}/{contact_id}")
def update_settings(
    site_id: str,
    contact_id: str,
    data: SettingsUpdate,
    db: DB
):
    from app.language_manager import language_manager

    if (
        data.recipient_language != "ko"
        and not language_manager.is_supported(
            data.recipient_language
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Recipient language module not installed"
        )

    setting = find_setting(db, site_id, contact_id)

    if setting is None:
        setting = ConversationSetting(
            site_id=site_id,
            contact_id=contact_id
        )
        db.add(setting)

    for key, value in data.model_dump().items():
        setattr(setting, key, value)

    setting.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(setting)

    return serialize(setting)


# ---------------------------------------
# List settings belonging to a site
# ---------------------------------------

@router.get("/site/{site_id}/contacts")
def get_site_contacts(site_id: str, db: DB):
    settings = db.scalars(
        select(ConversationSetting)
        .where(ConversationSetting.site_id == site_id)
        .order_by(ConversationSetting.contact_id)
    ).all()

    return {
        "site_id": site_id,
        "contacts": [serialize(s) for s in settings]
    }