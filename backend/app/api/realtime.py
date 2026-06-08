"""Endpoints WebSocket para tracking, chat y eventos de solicitud.

Autenticación: el cliente debe pasar `?token=<jwt-access>` al abrir la conexión.
Se rechaza el handshake con 4401 si el token no es válido. Usamos códigos del
rango 4xxx (reservado para apps) en lugar de 401 porque el RFC 6455 no permite
respuestas HTTP convencionales tras el handshake.

Salas disponibles:
* `solicitud:{id}`  — eventos genéricos de la solicitud (estado, tracking).
* `taller:{id}`     — eventos para el panel operativo del taller.
* `tecnico:{id}`    — eventos dirigidos a un técnico concreto.
* `chat:{solicitud_id}` — mensajería entre cliente / taller / técnico.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.security import ALGORITHM, SECRET_KEY
from app.db.session import engine
from app.models.domain import (
    Cotizacion,
    EstadoCandidato,
    EstadoSolicitud,
    Solicitud,
    SolicitudCandidato,
    Taller,
    Tecnico,
    Vehiculo,
)
from app.models.user import User, UserRole
from app.services.realtime import manager as realtime_manager


router = APIRouter()


WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_FORBIDDEN = 4403
WS_CLOSE_BAD_REQUEST = 4400


async def _resolver_usuario(token: str) -> Optional[User]:
    """Decodifica el JWT y devuelve el `User` o `None` si es inválido."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    with Session(engine) as session:
        return session.get(User, user_id)


def _puede_unirse_a_solicitud(session: Session, user: User, solicitud_id: int) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        return False
    if user.role == UserRole.WORKSHOP:
        taller = session.exec(
            select(Taller).where(Taller.propietario_id == user.id)
        ).first()
        if not taller:
            return False
        if solicitud.taller_id == taller.id:
            return True

        # Taller candidato aun antes de asignacion: necesita la sala para ver
        # cambios en vivo mientras cotiza o espera seleccion del cliente.
        candidato = session.exec(
            select(SolicitudCandidato)
            .where(SolicitudCandidato.solicitud_id == solicitud.id)
            .where(SolicitudCandidato.taller_id == taller.id)
            .where(SolicitudCandidato.estado.notin_([
                EstadoCandidato.RECHAZADO,
                EstadoCandidato.EXPIRADO,
            ]))
        ).first()
        if (
            candidato
            and solicitud.taller_id is None
            and solicitud.estado in {EstadoSolicitud.PENDIENTE, EstadoSolicitud.BUSCANDO_TALLER}
        ):
            return True

        cotizacion = session.exec(
            select(Cotizacion)
            .where(Cotizacion.solicitud_id == solicitud.id)
            .where(Cotizacion.taller_id == taller.id)
        ).first()
        return bool(cotizacion)
    if user.role == UserRole.TECNICO:
        tecnico = session.exec(
            select(Tecnico).where(Tecnico.id_usuario == user.id)
        ).first()
        return bool(tecnico and solicitud.tecnico_id == tecnico.id)
    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        return bool(vehiculo and vehiculo.propietario_id == user.id)
    return False


def _puede_unirse_a_taller(session: Session, user: User, taller_id: int) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.WORKSHOP:
        taller = session.get(Taller, taller_id)
        return bool(taller and taller.propietario_id == user.id)
    if user.role == UserRole.TECNICO:
        tecnico = session.exec(
            select(Tecnico).where(Tecnico.id_usuario == user.id)
        ).first()
        return bool(tecnico and tecnico.taller_id == taller_id)
    return False


def _puede_unirse_a_tecnico(session: Session, user: User, tecnico_id: int) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.TECNICO:
        tecnico = session.get(Tecnico, tecnico_id)
        return bool(tecnico and tecnico.id_usuario == user.id)
    if user.role == UserRole.WORKSHOP:
        tecnico = session.get(Tecnico, tecnico_id)
        if not tecnico:
            return False
        taller = session.exec(
            select(Taller).where(Taller.propietario_id == user.id)
        ).first()
        return bool(taller and tecnico.taller_id == taller.id)
    return False


async def _atender_websocket(
    websocket: WebSocket,
    *,
    room: str,
    user: User,
) -> None:
    """Conexión WS persistente con heartbeat aplicación.

    Protocolo:
    * Cliente puede enviar `"ping"` en cualquier momento → el servidor
      responde `{"event":"pong","payload":{...}}`. Esto sirve para detectar
      half-open connections desde el lado del cliente.
    * Servidor envía proactivamente `{"event":"server.ping","payload":{}}` cada
      `WS_HEARTBEAT_SECONDS` segundos (default 25). Si el cliente está vivo
      mantiene la TCP keep-alive y proxies intermedios (nginx, cloudflare)
      no cierran la conexión por inactividad (~60s por defecto).
    """
    import asyncio
    import os
    from datetime import datetime

    heartbeat_seconds = float(os.getenv("WS_HEARTBEAT_SECONDS", "25"))

    await realtime_manager.connect(websocket, room=room, user_id=user.id or 0)

    async def _recv_loop() -> None:
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_json({
                    "event": "pong",
                    "payload": {"ts": datetime.utcnow().isoformat()},
                })

    async def _heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(heartbeat_seconds)
            try:
                await websocket.send_json({
                    "event": "server.ping",
                    "payload": {"ts": datetime.utcnow().isoformat()},
                })
            except Exception:  # noqa: BLE001
                return

    recv_task = asyncio.create_task(_recv_loop())
    hb_task = asyncio.create_task(_heartbeat_loop())
    try:
        done, _pending = await asyncio.wait(
            {recv_task, hb_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            # Si la tarea murió por excepción la elevamos solo para tracing.
            exc = task.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                print(f"WS task error en sala {room}: {exc}")
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        for task in (recv_task, hb_task):
            if not task.done():
                task.cancel()
        realtime_manager.disconnect(websocket, room=room, user_id=user.id or 0)


@router.websocket("/solicitudes/{solicitud_id}")
async def ws_solicitud(websocket: WebSocket, solicitud_id: int, token: str = Query(...)):
    user = await _resolver_usuario(token)
    if not user:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return
    with Session(engine) as session:
        if not _puede_unirse_a_solicitud(session, user, solicitud_id):
            await websocket.close(code=WS_CLOSE_FORBIDDEN)
            return
    await _atender_websocket(websocket, room=f"solicitud:{solicitud_id}", user=user)


@router.websocket("/talleres/{taller_id}")
async def ws_taller(websocket: WebSocket, taller_id: int, token: str = Query(...)):
    user = await _resolver_usuario(token)
    if not user:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return
    with Session(engine) as session:
        if not _puede_unirse_a_taller(session, user, taller_id):
            await websocket.close(code=WS_CLOSE_FORBIDDEN)
            return
    await _atender_websocket(websocket, room=f"taller:{taller_id}", user=user)


@router.websocket("/tecnicos/{tecnico_id}")
async def ws_tecnico(websocket: WebSocket, tecnico_id: int, token: str = Query(...)):
    user = await _resolver_usuario(token)
    if not user:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return
    with Session(engine) as session:
        if not _puede_unirse_a_tecnico(session, user, tecnico_id):
            await websocket.close(code=WS_CLOSE_FORBIDDEN)
            return
    await _atender_websocket(websocket, room=f"tecnico:{tecnico_id}", user=user)


@router.websocket("/chat/{solicitud_id}")
async def ws_chat(websocket: WebSocket, solicitud_id: int, token: str = Query(...)):
    user = await _resolver_usuario(token)
    if not user:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return
    with Session(engine) as session:
        if not _puede_unirse_a_solicitud(session, user, solicitud_id):
            await websocket.close(code=WS_CLOSE_FORBIDDEN)
            return
    await _atender_websocket(websocket, room=f"chat:{solicitud_id}", user=user)
