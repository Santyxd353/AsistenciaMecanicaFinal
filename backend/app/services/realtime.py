from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class RealtimeManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._users: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, *, room: str, user_id: int) -> None:
        await websocket.accept()
        self._rooms[room].add(websocket)
        self._users[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, *, room: str, user_id: int) -> None:
        self._rooms[room].discard(websocket)
        self._users[user_id].discard(websocket)
        if not self._rooms[room]:
            self._rooms.pop(room, None)
        if not self._users[user_id]:
            self._users.pop(user_id, None)

    async def broadcast_room(self, room: str, event: str, payload: dict[str, Any]) -> None:
        await self._send_many(self._rooms.get(room, set()), event, payload)

    async def send_user(self, user_id: int, event: str, payload: dict[str, Any]) -> None:
        await self._send_many(self._users.get(user_id, set()), event, payload)

    async def _send_many(self, sockets: set[WebSocket], event: str, payload: dict[str, Any]) -> None:
        disconnected: list[WebSocket] = []
        message = json.dumps({"event": event, "payload": payload}, default=str)
        for websocket in sockets.copy():
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            for room_sockets in self._rooms.values():
                room_sockets.discard(websocket)
            for user_sockets in self._users.values():
                user_sockets.discard(websocket)


manager = RealtimeManager()


def solicitud_room(solicitud_id: int) -> str:
    return f"solicitud:{solicitud_id}"


def taller_room(taller_id: int) -> str:
    return f"taller:{taller_id}"
