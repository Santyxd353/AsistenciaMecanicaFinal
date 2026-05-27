"""Chat REST entre cliente, taller y técnico vinculado a una solicitud.

El WS de chat vive en `app.api.realtime` (sala `chat:{solicitud_id}`).
Este router solo expone REST para crear/listar mensajes con permisos.
"""

from __future__ import annotations

from typing import List

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    ChatMensaje,
    ChatMensajeCreate,
    ChatMensajeRead,
    Solicitud,
    Taller,
    Tecnico,
    Vehiculo,
)
from app.models.user import User, UserRole
from app.services.realtime import manager as realtime_manager


router = APIRouter()


def _chat_room(solicitud_id: int) -> str:
    return f"chat:{solicitud_id}"


def _puede_chatear(session: Session, solicitud: Solicitud, current_user: User) -> bool:
    if (
        current_user.tenant_id is not None
        and solicitud.tenant_id is not None
        and current_user.tenant_id != solicitud.tenant_id
    ):
        return False

    if current_user.role == UserRole.ADMIN:
        return True

    if current_user.role == UserRole.WORKSHOP:
        taller = session.exec(
            select(Taller)
            .where(Taller.propietario_id == current_user.id)
            .where(Taller.tenant_id == current_user.tenant_id)
        ).first()
        return bool(taller and solicitud.taller_id == taller.id)

    if current_user.role == UserRole.TECNICO:
        tecnico = session.exec(
            select(Tecnico)
            .where(Tecnico.id_usuario == current_user.id)
            .where(Tecnico.tenant_id == current_user.tenant_id)
        ).first()
        return bool(tecnico and solicitud.tecnico_id == tecnico.id)

    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        return bool(vehiculo and vehiculo.propietario_id == current_user.id)

    return False


def _emit_chat(payload: dict, solicitud_id: int) -> None:
    async def _emit() -> None:
        await realtime_manager.broadcast_room(
            _chat_room(solicitud_id), "chat.mensaje", payload
        )

    try:
        anyio.from_thread.run(_emit)
    except RuntimeError:
        pass


@router.post(
    "/solicitudes/{solicitud_id}/mensajes",
    response_model=ChatMensajeRead,
    status_code=status.HTTP_201_CREATED,
)
def enviar_mensaje(
    solicitud_id: int,
    payload: ChatMensajeCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

    if not _puede_chatear(session, solicitud, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No participas en esta solicitud.",
        )

    mensaje_texto = (payload.mensaje or "").strip()
    if not mensaje_texto:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")
    if len(mensaje_texto) > 2000:
        raise HTTPException(status_code=400, detail="Mensaje demasiado largo (máx 2000).")

    mensaje = ChatMensaje(
        solicitud_id=solicitud_id,
        remitente_id=current_user.id or 0,
        tenant_id=solicitud.tenant_id,
        mensaje=mensaje_texto,
    )
    session.add(mensaje)
    session.commit()
    session.refresh(mensaje)

    payload_ws = ChatMensajeRead.model_validate(mensaje).model_dump()
    payload_ws["fecha_creacion"] = (
        mensaje.fecha_creacion.isoformat() if mensaje.fecha_creacion else None
    )
    _emit_chat(payload_ws, solicitud_id)
    return ChatMensajeRead.model_validate(mensaje)


@router.get(
    "/solicitudes/{solicitud_id}/mensajes",
    response_model=List[ChatMensajeRead],
)
def listar_mensajes(
    solicitud_id: int,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if not _puede_chatear(session, solicitud, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No participas en esta solicitud.",
        )

    mensajes = session.exec(
        select(ChatMensaje)
        .where(ChatMensaje.solicitud_id == solicitud_id)
        .where(ChatMensaje.tenant_id == solicitud.tenant_id)
        .order_by(ChatMensaje.fecha_creacion.asc())
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 500))
    ).all()
    return [ChatMensajeRead.model_validate(item) for item in mensajes]


@router.post(
    "/solicitudes/{solicitud_id}/mensajes/marcar-leidos",
    status_code=status.HTTP_204_NO_CONTENT,
)
def marcar_leidos(
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Marca como leídos todos los mensajes ajenos al usuario en esta solicitud."""
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if not _puede_chatear(session, solicitud, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No participas en esta solicitud.",
        )

    mensajes = session.exec(
        select(ChatMensaje)
        .where(ChatMensaje.solicitud_id == solicitud_id)
        .where(ChatMensaje.tenant_id == solicitud.tenant_id)
        .where(ChatMensaje.remitente_id != current_user.id)
        .where(ChatMensaje.leido == False)  # noqa: E712 SQLModel column comparison
    ).all()
    for mensaje in mensajes:
        mensaje.leido = True
        session.add(mensaje)
    session.commit()
    return None
