from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from app.models.domain import AuditLog, SolicitudHistorial
from app.models.user import User


def registrar_auditoria(
    session: Session,
    *,
    actor: Optional[User],
    accion: str,
    entidad: str,
    entidad_id: Optional[int],
    detalle: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> AuditLog:
    effective_tenant_id = tenant_id if tenant_id is not None else (actor.tenant_id if actor else None)
    log = AuditLog(
        actor_id=actor.id if actor else None,
        actor_rol=actor.role.value if actor else None,
        tenant_id=effective_tenant_id,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=detalle,
    )
    session.add(log)
    session.flush()
    return log


def registrar_historial_solicitud(
    session: Session,
    *,
    solicitud_id: int,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    actor: Optional[User],
    comentario: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> SolicitudHistorial:
    effective_tenant_id = tenant_id if tenant_id is not None else (actor.tenant_id if actor else None)
    item = SolicitudHistorial(
        solicitud_id=solicitud_id,
        tenant_id=effective_tenant_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        actor_id=actor.id if actor else None,
        actor_rol=actor.role.value if actor else None,
        comentario=comentario,
    )
    session.add(item)
    registrar_auditoria(
        session,
        actor=actor,
        accion="cambio_estado_solicitud",
        entidad="solicitud",
        entidad_id=solicitud_id,
        detalle=f"{estado_anterior or 'inicio'} -> {estado_nuevo}: {comentario or ''}".strip(),
        tenant_id=effective_tenant_id,
    )
    session.flush()
    return item
