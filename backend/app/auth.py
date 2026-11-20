import os
import secrets
import jwt

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated
from dotenv import load_dotenv
from fastapi import (APIRouter, Depends, HTTPException, status)
from fastapi.security import (OAuth2PasswordBearer, OAuth2PasswordRequestForm)
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from app.ws_auth import (create_ws_ticket, TICKET_TTL_SECONDS)
from pydantic import BaseModel, Field


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(ENV_PATH)

ADMIN_USER = os.getenv("URCT_ADMIN_USER")
ADMIN_HASH = os.getenv("URCT_ADMIN_PASSWORD_HASH")
JWT_SECRET = os.getenv("URCT_JWT_SECRET")

if not all([ADMIN_USER, ADMIN_HASH, JWT_SECRET]):
    raise RuntimeError(
        "URCT authentication is not configured. "
        "Run setup_auth.py first."
    )

ALGORITHM = "HS256"
ISSUER = "urct-local"
AUDIENCE = "urct-api"
TOKEN_MINUTES = 30

password_hash = PasswordHash.recommended()
dummy_hash = password_hash.hash("dummy-password")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token"
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def invalid_credentials():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )


def verify_login(username: str, password: str) -> bool:
    valid_user = secrets.compare_digest(
        username,
        ADMIN_USER
    )

    stored_hash = (
        ADMIN_HASH if valid_user else dummy_hash
    )

    valid_password = password_hash.verify(
        password,
        stored_hash
    )

    return valid_user and valid_password


def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": username,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_MINUTES)
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=ALGORITHM
    )


def require_owner(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> str:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "require": [
                    "sub", "iss", "aud",
                    "iat", "exp"
                ]
            }
        )

        username = payload["sub"]

        if not secrets.compare_digest(
            username,
            ADMIN_USER
        ):
            raise invalid_credentials()

        return username

    except InvalidTokenError:
        raise invalid_credentials()


@router.post("/token", response_model=TokenResponse)
def login(
    form: Annotated[
        OAuth2PasswordRequestForm,
        Depends()
    ]
):
    if not verify_login(
        form.username,
        form.password
    ):
        raise invalid_credentials()

    return TokenResponse(
        access_token=create_access_token(
            form.username
        )
    )


@router.get("/me")
def get_my_profile(
    username: Annotated[str, Depends(require_owner)]
):
    return {
        "username": username,
        "role": "owner",
        "authenticated": True
    }



class WebSocketTicketRequest(BaseModel):
    user_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$"
    )


@router.post("/ws-ticket")
def issue_websocket_ticket(
    data: WebSocketTicketRequest,
    username: Annotated[str, Depends(require_owner)]
):
    ticket = create_ws_ticket(data.user_id)

    return {
        "ticket": ticket,
        "user_id": data.user_id,
        "expires_in": TICKET_TTL_SECONDS,
        "token_type": "websocket_ticket"
    }