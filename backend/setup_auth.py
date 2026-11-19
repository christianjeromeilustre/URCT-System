import getpass
import secrets
from pathlib import Path

from dotenv import set_key
from pwdlib import PasswordHash


BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"

password_hash = PasswordHash.recommended()

print("URCT Administrator Setup")

username = "owner"

password = getpass.getpass(
    "Create a NEW URCT password: "
)

confirm = getpass.getpass(
    "Confirm URCT password: "
)

if len(password) < 12:
    raise SystemExit(
        "Password must contain at least 12 characters."
    )

if password != confirm:
    raise SystemExit("Passwords do not match.")

if ENV_FILE.exists() and any(
    line.startswith("URCT_JWT_SECRET=")
    for line in ENV_FILE.read_text(
        encoding="utf-8"
    ).splitlines()
):
    raise SystemExit(
        "Authentication already configured. "
        "Existing secret was not replaced."
    )

secret = secrets.token_hex(32)
hashed_password = password_hash.hash(password)

set_key(str(ENV_FILE), "URCT_ADMIN_USER", username)
set_key(
    str(ENV_FILE),
    "URCT_ADMIN_PASSWORD_HASH",
    hashed_password
)
set_key(
    str(ENV_FILE),
    "URCT_JWT_SECRET",
    secret
)

print("Administrator configured successfully.")
print("Username:", username)
print("Credentials saved in backend/.env")