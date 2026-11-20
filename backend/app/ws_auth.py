import secrets
import time

from threading import Lock


TICKET_TTL_SECONDS = 30

_tickets = {}
_ticket_lock = Lock()


def create_ws_ticket(user_id: str) -> str:
    ticket = secrets.token_urlsafe(32)

    expires_at = (
        time.monotonic() + TICKET_TTL_SECONDS
    )

    with _ticket_lock:
        now = time.monotonic()

        # Remove expired tickets
        for key, value in list(_tickets.items()):
            if value["expires_at"] <= now:
                del _tickets[key]

        _tickets[ticket] = {
            "user_id": user_id,
            "expires_at": expires_at
        }

    return ticket


def consume_ws_ticket(
    ticket: str,
    user_id: str
) -> bool:

    if not ticket:
        return False

    with _ticket_lock:
        # Pop makes the ticket single-use
        data = _tickets.pop(ticket, None)

    if data is None:
        return False

    if time.monotonic() >= data["expires_at"]:
        return False

    return secrets.compare_digest(
        data["user_id"],
        user_id
    )