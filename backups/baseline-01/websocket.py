
from fastapi import WebSocket
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()

        # Replace an existing connection for the same user.
        old_connection = self.active_connections.get(user_id)

        self.active_connections[user_id] = websocket

        logger.info("User connected: %s", user_id)

        if old_connection and old_connection is not websocket:
            await old_connection.close(
                code=4001,
                reason="Connected from another session"
            )

    def disconnect(self, user_id: str, websocket: WebSocket):
        # Avoid removing a newer connection accidentally.
        if self.active_connections.get(user_id) is websocket:
            self.active_connections.pop(user_id, None)
            logger.info("User disconnected: %s", user_id)

    async def send_message(self, receiver_id: str, message: dict):
        websocket = self.active_connections.get(receiver_id)

        if websocket is None:
            return False

        await websocket.send_json(message)
        return True

    def is_connected(self, user_id: str) -> bool:
        return user_id in self.active_connections


manager = ConnectionManager()
