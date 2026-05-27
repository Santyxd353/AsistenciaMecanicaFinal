"""Endpoints REST para el módulo de tracking en vivo.

Flujo:

1. El técnico (rol TECNICO) hace `POST /solicitudes/{id}/ping` periódicamente
   con su lat/lon. Se persiste en `tracking_ping`, se actualiza la posición
   viva en `tecnico` y se recalcula ETA + distancia restante.
2. El servidor emite por WebSocket `tracking.update` a:
   * la sala `solicitud:{id}` (cliente la escucha)
   * la sala `taller:{id}` (operativo del taller la escucha)
3. Cliente y taller pueden recuperar el último ping con `GET .../ultimo` y
   el histórico con `GET .../historial` para reconstruir la ruta.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    EstadoSolicitud,
    Solicitud,
    Taller,
    Tecnico,
    TrackingPing,
    TrackingPingCreate,
    TrackingPingRead,
)
from app.models.user import User, UserRole
from app.services.tracking import broadcast_ping, registrar_ping


router = APIRouter()


ESTADOS_TRACKING_PERMITIDO = {
    EstadoSolicitud.ASIGNADA,
    EstadoSolicitud.TECNICO_EN_CAMINO,
    EstadoSolicitud.TECNICO_LLEGO,
    EstadoSolicitud.EN_PROCESO,
}


def _tecnico_de_usuario(session: Session, current_user: User) -> Tecnico:
    tecnico = session.exec(
        select(Tecnico).where(Tecnico.id_usuario == current_user.id)
    ).first()
    if not tecnico:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este usuario no tiene perfil de técnico.",
        )
    return tecnico


def _solicitud_visible(
    session: Session, solicitud_id: int, current_user: User
) -> Solicitud:
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada.",
        )
    if (
        current_user.tenant_id is not None
        and solicitud.tenant_id is not None
        and current_user.tenant_id != solicitud.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solicitud fuera de tu tenant.",
        )

    if current_user.role == UserRole.ADMIN:
        return solicitud

    if current_user.role == UserRole.TECNICO:
        tecnico = _tecnico_de_usuario(session, current_user)
        if solicitud.tecnico_id != tecnico.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La solicitud no está asignada a este técnico.",
            )
        return solicitud

    if current_user.role == UserRole.WORKSHOP:
        taller = session.exec(
            select(Taller).where(Taller.propietario_id == current_user.id)
        ).first()
        if not taller or solicitud.taller_id != taller.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La solicitud no pertenece a este taller.",
            )
        return solicitud

    # Conductor: la solicitud debe ser de un vehículo de su propiedad.
    if solicitud.vehiculo_id:
        from app.models.domain import Vehiculo

        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if vehiculo and vehiculo.propietario_id == current_user.id:
            return solicitud

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos sobre esta solicitud.",
    )


@router.post(
    "/solicitudes/{solicitud_id}/ping",
    response_model=TrackingPingRead,
    status_code=status.HTTP_201_CREATED,
)
def enviar_ping(
    solicitud_id: int,
    payload: TrackingPingCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Registra una nueva posición del técnico y emite tracking.update por WS."""
    if current_user.role != UserRole.TECNICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los técnicos pueden reportar ubicación.",
        )

    tecnico = _tecnico_de_usuario(session, current_user)
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada.",
        )
    if solicitud.tenant_id != tecnico.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solicitud fuera de tu tenant.",
        )
    if solicitud.tecnico_id != tecnico.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La solicitud no está asignada a este técnico.",
        )
    if solicitud.estado not in ESTADOS_TRACKING_PERMITIDO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Solo se pueden enviar pings cuando la solicitud está "
                "asignada o en curso."
            ),
        )

    ping = registrar_ping(
        session,
        solicitud=solicitud,
        tecnico=tecnico,
        latitud=payload.latitud,
        longitud=payload.longitud,
        velocidad_kmh=payload.velocidad_kmh,
        rumbo_grados=payload.rumbo_grados,
    )
    session.commit()
    session.refresh(ping)
    broadcast_ping(ping, taller_id=solicitud.taller_id)
    return TrackingPingRead.model_validate(ping)


@router.get(
    "/solicitudes/{solicitud_id}/ultimo",
    response_model=TrackingPingRead | None,
)
def ultimo_ping(
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el último ping conocido (None si nunca hubo)."""
    _solicitud_visible(session, solicitud_id, current_user)
    ping = session.exec(
        select(TrackingPing)
        .where(TrackingPing.solicitud_id == solicitud_id)
        .order_by(TrackingPing.fecha_creacion.desc())
    ).first()
    return TrackingPingRead.model_validate(ping) if ping else None


@router.get(
    "/solicitudes/{solicitud_id}/historial",
    response_model=List[TrackingPingRead],
)
def historial(
    solicitud_id: int,
    limit: int = 200,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el histórico de pings ordenado cronológicamente."""
    _solicitud_visible(session, solicitud_id, current_user)
    pings = session.exec(
        select(TrackingPing)
        .where(TrackingPing.solicitud_id == solicitud_id)
        .order_by(TrackingPing.fecha_creacion.asc())
        .limit(min(max(limit, 1), 1000))
    ).all()
    return [TrackingPingRead.model_validate(ping) for ping in pings]
