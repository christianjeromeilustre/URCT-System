
import uuid

from typing import Annotated

from fastapi import (APIRouter, Depends, HTTPException)
from pydantic import BaseModel, Field
from sqlalchemy import (String, Boolean, ForeignKey, select, delete)
from sqlalchemy.orm import (Mapped, mapped_column, relationship,Session)

from app.auth import require_owner
from app.database import Base, get_db
from app.conversation_settings import (ConversationSetting, SettingsUpdate)
# from app.conversation_settings import ConversationSetting
from datetime import datetime, timezone


# Initial supported plugin manifests.
# These are registrations, not live site integrations.

SITE_CATALOG = {
    "knot": {
        "id": "knot",
        "name": "Knot.chat",
        "domain": "knot.chat",
        "version": "0.1.0"
    },
    "anonchat": {
        "id": "anonchat",
        "name": "AnonChat",
        "domain": "anonchat.com",
        "version": "0.1.0"
    }
}


class SitePlugin(Base):
    __tablename__ = "site_plugins"

    id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True
    )

    name: Mapped[str] = mapped_column(String(150))
    domain: Mapped[str] = mapped_column(String(250))
    version: Mapped[str] = mapped_column(String(30))

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan"
    )


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True
    )

    site_id: Mapped[str] = mapped_column(
        ForeignKey("site_plugins.id"),
        index=True
    )

    display_name: Mapped[str] = mapped_column(
        String(200)
    )

    recipient_language: Mapped[str] = mapped_column(
        String(20),
        default="en"
    )

    mode: Mapped[str] = mapped_column(
        String(30),
        default="auto"
    )

    site: Mapped["SitePlugin"] = relationship(
        back_populates="contacts"
    )


class ContactCreate(BaseModel):
    display_name: str = Field(
        min_length=1,
        max_length=200
    )
    recipient_language: str = "en"
    mode: str = "auto"


class PluginUpdate(BaseModel):
    enabled: bool


router = APIRouter(
    prefix="/sites",
    tags=["Site Plugins & Contacts"],
    dependencies=[Depends(require_owner)]
)

DB = Annotated[Session, Depends(get_db)]


def serialize_contact(contact):
    return {
        "id": contact.id,
        "site_id": contact.site_id,
        "display_name": contact.display_name,
        "recipient_language": contact.recipient_language,
        "mode": contact.mode
    }


def initialize_site_plugins(db: Session):
    for site_id, data in SITE_CATALOG.items():
        if db.get(SitePlugin, site_id) is None:
            db.add(SitePlugin(**data, enabled=True))

    db.commit()


@router.get("")
def list_sites(db: DB):
    return [
        {
            "id": site.id,
            "name": site.name,
            "domain": site.domain,
            "enabled": site.enabled
        }
        for site in db.scalars(
            select(SitePlugin).order_by(SitePlugin.name)
        ).all()
    ]


@router.get("/tree")
def get_contact_tree(db: DB):
    sites = db.scalars(
        select(SitePlugin).order_by(SitePlugin.name)
    ).all()

    result = []

    for site in sites:
        contacts = db.scalars(
            select(Contact)
            .where(Contact.site_id == site.id)
            .order_by(Contact.display_name)
        ).all()

        result.append({
            "site_id": site.id,
            "site_name": site.name,
            "enabled": site.enabled,
            "contacts": [
                serialize_contact(c) for c in contacts
            ]
        })

    return result


@router.put("/{site_id}")
def update_plugin(
    site_id: str,
    data: PluginUpdate,
    db: DB
):
    site = db.get(SitePlugin, site_id)

    if site is None:
        raise HTTPException(404, "Site not found")

    site.enabled = data.enabled
    db.commit()

    return {
        "site_id": site.id,
        "enabled": site.enabled
    }


@router.post("/{site_id}/contacts", status_code=201)
def add_contact(
    site_id: str,
    data: ContactCreate,
    db: DB
):
    from app.language_manager import language_manager

    site = db.get(SitePlugin, site_id)

    if site is None or not site.enabled:
        raise HTTPException(
            404, "Site not found or disabled"
        )

    if data.recipient_language != "ko" and not (
        language_manager.is_supported(
            data.recipient_language
        )
    ):
        raise HTTPException(
            400, "Language plugin not installed"
        )

    if data.mode not in {
        "auto", "social", "professional",
        "interview", "technical"
    }:
        raise HTTPException(400, "Invalid mode")

    contact = Contact(
        id=str(uuid.uuid4()),
        site_id=site_id,
        **data.model_dump()
    )

    db.add(contact)
    db.commit()
    db.refresh(contact)

    return serialize_contact(contact)


@router.delete("/{site_id}/contacts/{contact_id}")
def delete_contact(
    site_id: str,
    contact_id: str,
    db: DB
):
    contact = db.get(Contact, contact_id)

    if contact is None or contact.site_id != site_id:
        raise HTTPException(404, "Contact not found")

    # Remove settings belonging to this contact.
    db.execute(
        delete(ConversationSetting).where(
            ConversationSetting.site_id == site_id,
            ConversationSetting.contact_id == contact_id
        )
    )

    db.delete(contact)
    db.commit()

    return {
        "deleted": True,
        "contact_id": contact_id,
        "history_deleted": False
    }

# -----------------------------------------
# Contact Detail Manager
# -----------------------------------------

def get_contact_or_404(
    db: Session,
    site_id: str,
    contact_id: str
) -> Contact:

    contact = db.get(Contact, contact_id)

    if contact is None or contact.site_id != site_id:
        raise HTTPException(
            status_code=404,
            detail="Contact not found"
        )

    return contact


def find_contact_settings(
    db: Session,
    site_id: str,
    contact_id: str
):
    return db.scalar(
        select(ConversationSetting).where(
            ConversationSetting.site_id == site_id,
            ConversationSetting.contact_id == contact_id
        )
    )


@router.get("/{site_id}/contacts/{contact_id}")
def get_contact_details(
    site_id: str,
    contact_id: str,
    db: DB
):
    contact = get_contact_or_404(
        db, site_id, contact_id
    )

    settings = find_contact_settings(
        db, site_id, contact_id
    )

    return {
        **serialize_contact(contact),
        "settings": {
            "recipient_language": (
                settings.recipient_language
                if settings else contact.recipient_language
            ),
            "language_confirmed": (
                settings.language_confirmed
                if settings else False
            ),
            "mode": (
                settings.mode if settings else contact.mode
            ),
            "translation_style": (
                settings.translation_style
                if settings else "natural"
            ),
            "auto_detect": (
                settings.auto_detect
                if settings else True
            )
        }
    }


@router.put("/{site_id}/contacts/{contact_id}")
def update_contact_details(
    site_id: str,
    contact_id: str,
    data: SettingsUpdate,
    db: DB
):
    from app.language_manager import language_manager

    contact = get_contact_or_404(
        db, site_id, contact_id
    )

    if (
        data.recipient_language != "ko"
        and not language_manager.is_supported(
            data.recipient_language
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Language plugin not installed"
        )

    settings = find_contact_settings(
        db, site_id, contact_id
    )

    if settings is None:
        settings = ConversationSetting(
            site_id=site_id,
            contact_id=contact_id
        )
        db.add(settings)

    for key, value in data.model_dump().items():
        setattr(settings, key, value)

    # Keep Contact Tree fields synchronized.
    contact.recipient_language = data.recipient_language
    contact.mode = data.mode

    settings.updated_at = datetime.now(timezone.utc)

    db.commit()

    return get_contact_details(
        site_id,
        contact_id,
        db
    )

