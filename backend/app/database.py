from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine,
    ForeignKey,
    String,
    Text,
    DateTime,
    event
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker
)


# ----------------------------------------
# 1. Database location
# ----------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

DATABASE_FILE = DATA_DIR / "urct.db"


# ----------------------------------------
# 2. SQLite engine
# ----------------------------------------

engine = create_engine(
    f"sqlite:///{DATABASE_FILE.as_posix()}",
    connect_args={
        "check_same_thread": False
    }
)


@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ----------------------------------------
# 3. Database session
# ----------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)


def utc_now():
    return datetime.now(timezone.utc)


# ----------------------------------------
# 4. Base model
# ----------------------------------------

class Base(DeclarativeBase):
    pass


# ----------------------------------------
# 5. Conversation table
# ----------------------------------------

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )
    
    
    contact_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "contacts.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )


    platform: Mapped[str] = mapped_column(
        String(100)
    )

    contact_name: Mapped[str] = mapped_column(
        String(200)
    )

    language: Mapped[str] = mapped_column(
        String(20),
        default="en"
    )

    mode: Mapped[str] = mapped_column(
        String(50),
        default="social"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan"
    )


# ----------------------------------------
# 6. Message table
# ----------------------------------------

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE"
        ),
        index=True
    )

    direction: Mapped[str] = mapped_column(
        String(10)
    )

    original_text: Mapped[str] = mapped_column(
        Text
    )

    translated_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    source_language: Mapped[str] = mapped_column(
        String(20)
    )

    target_language: Mapped[str] = mapped_column(
        String(20)
    )

    engine_name: Mapped[str] = mapped_column(
        String(50),
        default="unknown"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages"
    )


# ----------------------------------------
# 7. Database initialization
# ----------------------------------------

def init_database():
    Base.metadata.create_all(bind=engine)


# ----------------------------------------
# 8. Database dependency
# ----------------------------------------

def get_db():
    with SessionLocal() as session:
        yield session