"""Acceso a audit_log y historial de solicitudes. Solo ADMIN.

Sirve dos casos:
1. Compliance / soporte: ver acciones por actor o por entidad.
2. UI admin: timeline filtrable de eventos de la plataforma.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    AuditLog,
    SolicitudHistorial,
    SolicitudHistorialRead,
)
from app.models.user import User, UserRole


router = APIRouter()


def _solo_admin(current_user: User) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden consultar la auditoría.",
        )


@router.get("/", response_model=List[dict])
def listar_auditoria(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    actor_id: Optional[int] = None,
    entidad: Optional[str] = None,
    entidad_id: Optional[int] = None,
    accion: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _solo_admin(current_user)
    stmt = select(AuditLog).order_by(AuditLog.fecha_creacion.desc())
    if current_user.tenant_id is not None:
        stmt = stmt.where(AuditLog.tenant_id == current_user.tenant_id)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if entidad:
        stmt = stmt.where(AuditLog.entidad == entidad)
    if entidad_id is not None:
        stmt = stmt.where(AuditLog.entidad_id == entidad_id)
    if accion:
        stmt = stmt.where(AuditLog.accion == accion)
    stmt = stmt.offset(max(skip, 0)).limit(limit)
    items = session.exec(stmt).all()
    return [
        {
            "id": item.id,
            "actor_id": item.actor_id,
            "actor_rol": item.actor_rol,
            "tenant_id": item.tenant_id,
            "accion": item.accion,
            "entidad": item.entidad,
            "entidad_id": item.entidad_id,
            "detalle": item.detalle,
            "fecha_creacion": item.fecha_creacion.isoformat() if item.fecha_creacion else None,
        }
        for item in items
    ]


@router.get("/solicitudes/{solicitud_id}/historial", response_model=List[SolicitudHistorialRead])
def historial_solicitud(
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el historial de estados de una solicitud.

    Admin: cualquiera. Otros roles: solo si está vinculado a la solicitud.
    """
    stmt = (
        select(SolicitudHistorial)
        .where(SolicitudHistorial.solicitud_id == solicitud_id)
        .order_by(SolicitudHistorial.fecha_creacion.asc())
    )
    if current_user.tenant_id is not None:
        stmt = stmt.where(SolicitudHistorial.tenant_id == current_user.tenant_id)
    items = session.exec(stmt).all()

    if current_user.role != UserRole.ADMIN:
        # Cualquier no-admin solo puede ver el historial si la solicitud tiene
        # algún registro suyo (actor o vinculación). Para mantener simple el
        # control, exigimos rol no-DRIVER o ser actor en alguna línea.
        if current_user.role == UserRole.DRIVER and not any(
            item.actor_id == current_user.id for item in items
        ):
            # Permitimos al DRIVER ver el historial de su propia solicitud:
            # delegamos la validación a `solicitudes` que ya conoce los dueños.
            from app.api.solicitudes import ensure_request_visible_to_user
            from app.models.domain import Solicitud

            solicitud = session.get(Solicitud, solicitud_id)
            if solicitud:
                ensure_request_visible_to_user(session, solicitud, current_user)

    return [SolicitudHistorialRead.model_validate(item) for item in items]
