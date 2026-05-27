"""Calificaciones del cliente al servicio recibido.

Cada solicitud puede tener UNA calificación del cliente que la creó. Al guardar,
se recalcula la `calificacion_promedio` del taller (denormalizada) para que el
motor de asignación pueda ponderar reputación sin un GROUP BY por solicitud.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    CalificacionCreate,
    CalificacionRead,
    CalificacionServicio,
    EstadoSolicitud,
    Solicitud,
    Taller,
    Vehiculo,
)
from app.models.user import User, UserRole
from app.services.audit import registrar_auditoria


router = APIRouter()


def _recalcular_reputacion(session: Session, taller_id: int, tenant_id: int | None) -> None:
    calificaciones = session.exec(
        select(CalificacionServicio)
        .where(CalificacionServicio.taller_id == taller_id)
        .where(CalificacionServicio.tenant_id == tenant_id)
    ).all()
    if not calificaciones:
        return
    promedio = sum(item.puntaje for item in calificaciones) / len(calificaciones)
    taller = session.get(Taller, taller_id)
    if taller:
        taller.calificacion_promedio = round(promedio, 2)
        session.add(taller)


@router.post(
    "/solicitudes/{solicitud_id}",
    response_model=CalificacionRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_calificacion(
    solicitud_id: int,
    payload: CalificacionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el cliente puede calificar.",
        )
    if payload.puntaje < 1 or payload.puntaje > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El puntaje debe estar entre 1 y 5.",
        )

    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if solicitud.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solicitud fuera de tu tenant.")

    if solicitud.estado != EstadoSolicitud.FINALIZADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede calificar una solicitud finalizada.",
        )

    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if not vehiculo or vehiculo.propietario_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes calificar una solicitud ajena.",
            )

    existente = session.exec(
        select(CalificacionServicio)
        .where(CalificacionServicio.solicitud_id == solicitud_id)
        .where(CalificacionServicio.tenant_id == solicitud.tenant_id)
    ).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta solicitud ya fue calificada.",
        )

    calificacion = CalificacionServicio(
        solicitud_id=solicitud_id,
        taller_id=solicitud.taller_id,
        cliente_id=current_user.id or 0,
        tenant_id=solicitud.tenant_id,
        puntaje=payload.puntaje,
        comentario=(payload.comentario or "").strip() or None,
    )
    session.add(calificacion)
    session.flush()

    if solicitud.taller_id:
        _recalcular_reputacion(session, solicitud.taller_id, solicitud.tenant_id)

    registrar_auditoria(
        session,
        actor=current_user,
        accion="calificacion_creada",
        entidad="solicitud",
        entidad_id=solicitud_id,
        detalle=f"puntaje={payload.puntaje}",
    )
    session.commit()
    session.refresh(calificacion)
    return CalificacionRead.model_validate(calificacion)


@router.get("/solicitudes/{solicitud_id}", response_model=CalificacionRead | None)
def obtener_calificacion(
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(CalificacionServicio).where(CalificacionServicio.solicitud_id == solicitud_id)
    if current_user.tenant_id is not None:
        stmt = stmt.where(CalificacionServicio.tenant_id == current_user.tenant_id)
    cal = session.exec(stmt).first()
    if not cal:
        return None

    # Permisos: cliente dueño, taller calificado o admin.
    if current_user.role == UserRole.ADMIN or cal.cliente_id == current_user.id:
        return CalificacionRead.model_validate(cal)
    if current_user.role == UserRole.WORKSHOP:
        taller = session.exec(
            select(Taller)
            .where(Taller.propietario_id == current_user.id)
            .where(Taller.tenant_id == current_user.tenant_id)
        ).first()
        if taller and cal.taller_id == taller.id:
            return CalificacionRead.model_validate(cal)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos sobre esta calificación.",
    )


@router.get("/taller/{taller_id}", response_model=List[CalificacionRead])
def listar_calificaciones_taller(
    taller_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Lista pública (autenticada) de calificaciones de un taller, para detalle."""
    calificaciones = session.exec(
        select(CalificacionServicio)
        .where(CalificacionServicio.taller_id == taller_id)
        .where(CalificacionServicio.tenant_id == current_user.tenant_id)
        .order_by(CalificacionServicio.fecha_creacion.desc())
    ).all()
    return [CalificacionRead.model_validate(item) for item in calificaciones]
