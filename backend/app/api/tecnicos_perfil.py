"""Perfil público + sistema de calificaciones del mecánico.

Endpoints:

  GET  /api/v1/tecnicos/{id}/perfil
       Datos públicos del mecánico: nombre, foto, taller, especialidades,
       calificación promedio, total de servicios. Cualquier usuario autenticado
       puede consultarlo (clientes que están considerando aceptar una
       asignación, dashboards del taller, etc).

  GET  /api/v1/tecnicos/{id}/calificaciones?skip=&limit=
       Lista paginada de calificaciones recibidas por el mecánico, ordenada
       de más reciente a más antigua, incluyendo nombre del cliente.

  POST /api/v1/tecnicos/{id}/calificaciones
       Cliente que tuvo una solicitud FINALIZADA con este mecánico crea una
       calificación (1-5 + comentario opcional). Una calificación por
       (cliente, solicitud, mecánico). Tras guardar, el promedio y el contador
       en `tecnico` se recalculan en el mismo commit.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    CalificacionMecanico,
    CalificacionMecanicoCreate,
    CalificacionMecanicoRead,
    EspecialidadRead,
    EstadoSolicitud,
    Solicitud,
    Taller,
    Tecnico,
    TecnicoPerfilPublicoRead,
    Vehiculo,
)
from app.models.user import User, UserRole
from app.services.audit import registrar_auditoria


router = APIRouter()


def _recalcular_reputacion_tecnico(session: Session, tecnico_id: int) -> None:
    """Recalcula y persiste el promedio + total de calificaciones del mecánico.

    Lo dejamos denormalizado en `tecnico.calificacion_promedio` y
    `tecnico.total_calificaciones` para que los listados / motor de asignación
    puedan ordenar por reputación sin un GROUP BY por mecánico cada vez.
    """
    calificaciones = session.exec(
        select(CalificacionMecanico).where(CalificacionMecanico.tecnico_id == tecnico_id)
    ).all()
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        return
    if not calificaciones:
        tecnico.calificacion_promedio = 0.0
        tecnico.total_calificaciones = 0
    else:
        suma = sum(item.puntaje for item in calificaciones)
        tecnico.calificacion_promedio = round(suma / len(calificaciones), 2)
        tecnico.total_calificaciones = len(calificaciones)
    session.add(tecnico)


def _read_calificacion(session: Session, item: CalificacionMecanico) -> CalificacionMecanicoRead:
    cliente = session.get(User, item.cliente_id)
    return CalificacionMecanicoRead(
        id=item.id or 0,
        tecnico_id=item.tecnico_id,
        cliente_id=item.cliente_id,
        solicitud_id=item.solicitud_id,
        puntaje=item.puntaje,
        comentario=item.comentario,
        fecha_creacion=item.fecha_creacion,
        # Nombre amistoso si lo hay; si no, fallback al username.
        cliente_nombre=(cliente.full_name or cliente.username) if cliente else None,
    )


def _tecnico_visible(session: Session, tecnico_id: int, current_user: User) -> Tecnico:
    """El mecánico debe existir y pertenecer al tenant del usuario.

    El admin global (tenant_id=None) tiene acceso a todos los tenants. Los
    DRIVER / WORKSHOP / TECNICO ven solo los del propio tenant.
    """
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="Mecánico no encontrado.")
    if (
        current_user.tenant_id is not None
        and tecnico.tenant_id is not None
        and tecnico.tenant_id != current_user.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este mecánico pertenece a otro taller.",
        )
    return tecnico


@router.get("/{tecnico_id}/perfil", response_model=TecnicoPerfilPublicoRead)
def perfil_publico_tecnico(
    tecnico_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tecnico = _tecnico_visible(session, tecnico_id, current_user)

    taller = session.get(Taller, tecnico.taller_id) if tecnico.taller_id else None

    # Foto pública: si el mecánico tiene un usuario interno con foto_url, la
    # exponemos; en otro caso queda None y el front muestra un avatar genérico.
    foto_url = None
    telefono = None
    if tecnico.id_usuario:
        usuario = session.get(User, tecnico.id_usuario)
        foto_url = getattr(usuario, "foto_url", None)
        telefono = getattr(usuario, "telefono", None)

    finalizadas = session.exec(
        select(Solicitud)
        .where(Solicitud.tecnico_id == tecnico_id)
        .where(Solicitud.estado == EstadoSolicitud.FINALIZADO)
    ).all()

    return TecnicoPerfilPublicoRead(
        id=tecnico.id or 0,
        nombre=tecnico.nombre,
        foto_url=foto_url,
        telefono=telefono,
        taller_id=tecnico.taller_id,
        taller_nombre=taller.nombre_comercial if taller else None,
        disponible=tecnico.disponible,
        activo=tecnico.activo,
        especialidades=[
            EspecialidadRead(id=esp.id or 0, nombre=esp.nombre)
            for esp in (tecnico.especialidades or [])
        ],
        calificacion_promedio=tecnico.calificacion_promedio or 0.0,
        total_calificaciones=tecnico.total_calificaciones or 0,
        total_servicios_finalizados=len(finalizadas),
    )


@router.get(
    "/{tecnico_id}/calificaciones",
    response_model=List[CalificacionMecanicoRead],
)
def listar_calificaciones_tecnico(
    tecnico_id: int,
    skip: int = 0,
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _tecnico_visible(session, tecnico_id, current_user)
    items = session.exec(
        select(CalificacionMecanico)
        .where(CalificacionMecanico.tecnico_id == tecnico_id)
        .order_by(CalificacionMecanico.fecha_creacion.desc())
        .offset(max(skip, 0))
        .limit(limit)
    ).all()
    return [_read_calificacion(session, item) for item in items]


@router.post(
    "/{tecnico_id}/calificaciones",
    response_model=CalificacionMecanicoRead,
    status_code=status.HTTP_201_CREATED,
)
def calificar_tecnico(
    tecnico_id: int,
    solicitud_id: int = Query(..., description="Solicitud finalizada que el cliente está calificando."),
    payload: CalificacionMecanicoCreate = ...,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el cliente puede calificar al mecánico.",
        )
    if payload.puntaje < 1 or payload.puntaje > 5:
        raise HTTPException(status_code=400, detail="El puntaje debe estar entre 1 y 5.")

    tecnico = _tecnico_visible(session, tecnico_id, current_user)

    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if solicitud.tecnico_id != tecnico.id:
        raise HTTPException(
            status_code=400,
            detail="Esta solicitud no fue atendida por ese mecánico.",
        )
    if solicitud.estado != EstadoSolicitud.FINALIZADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede calificar después de finalizar el servicio.",
        )
    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if not vehiculo or vehiculo.propietario_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes calificar una solicitud ajena.",
            )

    existente = session.exec(
        select(CalificacionMecanico)
        .where(CalificacionMecanico.tecnico_id == tecnico_id)
        .where(CalificacionMecanico.solicitud_id == solicitud_id)
        .where(CalificacionMecanico.cliente_id == current_user.id)
    ).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya calificaste a este mecánico por esta solicitud.",
        )

    calificacion = CalificacionMecanico(
        tecnico_id=tecnico_id,
        cliente_id=current_user.id or 0,
        solicitud_id=solicitud_id,
        tenant_id=tecnico.tenant_id,
        puntaje=payload.puntaje,
        comentario=(payload.comentario or "").strip() or None,
    )
    session.add(calificacion)
    session.flush()

    _recalcular_reputacion_tecnico(session, tecnico_id)
    registrar_auditoria(
        session,
        actor=current_user,
        accion="calificacion_mecanico_creada",
        entidad="tecnico",
        entidad_id=tecnico_id,
        detalle=f"puntaje={payload.puntaje} solicitud={solicitud_id}",
    )

    session.commit()
    session.refresh(calificacion)
    return _read_calificacion(session, calificacion)
