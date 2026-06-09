"""Cotizaciones: el taller propone costo/tiempo y el cliente compara y selecciona.

Flujo:
1. Cliente crea solicitud → motor asigna talleres candidatos (scoring).
2. Cada taller candidato puede emitir UNA `Cotizacion` (POST por taller).
3. Cliente compara cotizaciones (GET por solicitud) y selecciona una
   (POST `/seleccionar`) → solicitud queda `ASIGNADA` al taller dueño.

WebSocket: emite `cotizacion.nueva` a la sala `solicitud:{id}` cuando llega
una cotización nueva para que la UI del cliente actualice la lista en vivo.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    Cotizacion,
    CotizacionCreate,
    CotizacionRead,
    EstadoCandidato,
    EstadoCotizacion,
    EstadoSolicitud,
    Solicitud,
    SolicitudCandidato,
    Taller,
    TipoNotificacion,
    Vehiculo,
)
from app.models.user import User, UserRole
from app.services.audit import registrar_auditoria, registrar_historial_solicitud
from app.services.notificaciones import crear_notificacion
from app.services.realtime import manager as realtime_manager, solicitud_room


router = APIRouter()


def _emit_solicitud(solicitud_id: int, event: str, payload: dict) -> None:
    async def _emit() -> None:
        await realtime_manager.broadcast_room(solicitud_room(solicitud_id), event, payload)

    try:
        anyio.from_thread.run(_emit)
    except RuntimeError:
        pass


def _taller_del_usuario(session: Session, user: User) -> Taller:
    if user.role != UserRole.WORKSHOP:
        raise HTTPException(status_code=403, detail="Solo el taller puede cotizar.")
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == user.id)
    ).first()
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado.")
    return taller


def _read(session: Session, cotizacion: Cotizacion) -> CotizacionRead:
    data = CotizacionRead.model_validate(cotizacion)
    taller = session.get(Taller, cotizacion.taller_id)
    return data.model_copy(update={
        "taller_nombre": taller.nombre_comercial if taller else None,
        "taller_calificacion": taller.calificacion_promedio if taller else None,
    })


def _taller_puede_cotizar_solicitud(
    session: Session,
    taller: Taller,
    solicitud: Solicitud,
) -> bool:
    """Permite cotizar solicitudes de marketplace antes de asignar tenant.

    En el flujo SaaS, el cliente puede vivir en un tenant distinto al taller.
    La solicitud se transfiere al tenant del taller recien cuando el cliente
    selecciona una cotizacion o el taller acepta la asistencia.
    """
    if solicitud.taller_id is not None:
        return solicitud.taller_id == taller.id

    if solicitud.estado not in {EstadoSolicitud.PENDIENTE, EstadoSolicitud.BUSCANDO_TALLER}:
        return False

    candidatos = session.exec(
        select(SolicitudCandidato)
        .where(SolicitudCandidato.solicitud_id == solicitud.id)
    ).all()
    if candidatos:
        return any(
            item.taller_id == taller.id
            and item.estado not in {EstadoCandidato.RECHAZADO, EstadoCandidato.EXPIRADO}
            for item in candidatos
        )

    return solicitud.tenant_id == taller.tenant_id or solicitud.taller_id is None


@router.post(
    "/solicitudes/{solicitud_id}",
    response_model=CotizacionRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_cotizacion(
    solicitud_id: int,
    payload: CotizacionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    taller = _taller_del_usuario(session, current_user)

    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if not _taller_puede_cotizar_solicitud(session, taller, solicitud):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este taller no puede cotizar esta solicitud.",
        )
    if solicitud.estado not in {EstadoSolicitud.PENDIENTE, EstadoSolicitud.BUSCANDO_TALLER}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede cotizar mientras la solicitud está pendiente/buscando taller.",
        )
    if payload.costo_estimado <= 0 or payload.eta_llegada_minutos <= 0 or payload.tiempo_reparacion_horas <= 0:
        raise HTTPException(status_code=400, detail="Valores numéricos deben ser positivos.")

    # Una sola cotización viva por taller por solicitud: si existía una en estado
    # ENVIADA la reemplazamos para que el cliente vea siempre la última oferta.
    existente = session.exec(
        select(Cotizacion)
        .where(Cotizacion.solicitud_id == solicitud_id)
        .where(Cotizacion.taller_id == taller.id)
        .where(Cotizacion.estado == EstadoCotizacion.ENVIADA)
    ).first()
    if existente:
        existente.estado = EstadoCotizacion.EXPIRADA
        session.add(existente)

    cotizacion = Cotizacion(
        solicitud_id=solicitud_id,
        taller_id=taller.id or 0,
        tenant_id=taller.tenant_id,
        costo_estimado=round(payload.costo_estimado, 2),
        tiempo_reparacion_horas=round(payload.tiempo_reparacion_horas, 2),
        eta_llegada_minutos=payload.eta_llegada_minutos,
        descripcion=(payload.descripcion or "").strip() or None,
        incluye_repuestos=payload.incluye_repuestos,
        garantia_dias=max(0, payload.garantia_dias),
    )
    session.add(cotizacion)
    session.flush()

    registrar_auditoria(
        session,
        actor=current_user,
        accion="cotizacion_enviada",
        entidad="solicitud",
        entidad_id=solicitud_id,
        detalle=(
            f"taller={taller.id} costo={cotizacion.costo_estimado} "
            f"eta={cotizacion.eta_llegada_minutos}min "
            f"reparacion={cotizacion.tiempo_reparacion_horas}h"
        ),
    )

    # Notificar al cliente dueño del vehículo.
    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if vehiculo and vehiculo.propietario_id:
            crear_notificacion(
                session,
                destinatario_id=vehiculo.propietario_id,
                tipo=TipoNotificacion.COTIZACION_ENVIADA,
                titulo="Nueva cotización recibida",
                mensaje=(
                    f"{taller.nombre_comercial} cotizó tu solicitud por "
                    f"{cotizacion.costo_estimado:.2f} (ETA {cotizacion.eta_llegada_minutos} min)."
                ),
                solicitud_id=solicitud_id,
                accion_url="/cliente",
            )

    session.commit()
    session.refresh(cotizacion)
    payload_ws = _read(session, cotizacion).model_dump()
    _emit_solicitud(solicitud_id, "cotizacion.nueva", payload_ws)
    return _read(session, cotizacion)


@router.get(
    "/solicitudes/{solicitud_id}",
    response_model=List[CotizacionRead],
)
def listar_cotizaciones(
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Listar cotizaciones de una solicitud.

    Cliente: solo si es dueño del vehículo. Taller: solo si es dueño de
    alguna cotización o candidato. Admin: todo.
    """
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

    if current_user.role == UserRole.DRIVER and solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if not vehiculo or vehiculo.propietario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No tienes acceso a esta solicitud.")
    elif current_user.role == UserRole.WORKSHOP:
        taller = _taller_del_usuario(session, current_user)
        cotizacion_propia = session.exec(
            select(Cotizacion)
            .where(Cotizacion.solicitud_id == solicitud_id)
            .where(Cotizacion.taller_id == taller.id)
        ).first()
        if not cotizacion_propia and not _taller_puede_cotizar_solicitud(session, taller, solicitud):
            raise HTTPException(status_code=403, detail="Solicitud fuera de tu tenant.")

    cotizaciones = session.exec(
        select(Cotizacion)
        .where(Cotizacion.solicitud_id == solicitud_id)
        .order_by(Cotizacion.costo_estimado.asc())
    ).all()
    return [_read(session, item) for item in cotizaciones]


@router.post("/{cotizacion_id}/seleccionar", response_model=CotizacionRead)
def seleccionar_cotizacion(
    cotizacion_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Cliente acepta una cotización. La solicitud se asigna al taller dueño."""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Solo el cliente puede seleccionar cotizaciones.")

    cotizacion = session.get(Cotizacion, cotizacion_id)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada.")
    if cotizacion.estado != EstadoCotizacion.ENVIADA:
        raise HTTPException(status_code=409, detail="Esta cotización ya no está disponible.")

    solicitud = session.get(Solicitud, cotizacion.solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if not vehiculo or vehiculo.propietario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No eres dueño de esta solicitud.")
    if solicitud.estado not in {EstadoSolicitud.PENDIENTE, EstadoSolicitud.BUSCANDO_TALLER}:
        raise HTTPException(status_code=409, detail="La solicitud ya está en curso.")

    # Marcar la elegida como aceptada y el resto como rechazada/expirada.
    otras = session.exec(
        select(Cotizacion)
        .where(Cotizacion.solicitud_id == solicitud.id)
        .where(Cotizacion.id != cotizacion.id)
    ).all()
    for otra in otras:
        if otra.estado == EstadoCotizacion.ENVIADA:
            otra.estado = EstadoCotizacion.RECHAZADA
            session.add(otra)

    cotizacion.estado = EstadoCotizacion.ACEPTADA
    cotizacion.fecha_seleccion = datetime.utcnow()
    session.add(cotizacion)

    estado_anterior = solicitud.estado
    taller = session.get(Taller, cotizacion.taller_id)
    solicitud.taller_id = cotizacion.taller_id
    if taller:
        solicitud.tenant_id = taller.tenant_id
    solicitud.estado = EstadoSolicitud.ASIGNADA
    solicitud.cotizacion_seleccionada_id = cotizacion.id
    solicitud.precio_cobrado = cotizacion.costo_estimado
    solicitud.comision_plataforma = round(cotizacion.costo_estimado * 0.10, 2)
    solicitud.tiempo_estimado_minutos = cotizacion.eta_llegada_minutos
    solicitud.fecha_taller_asignado = datetime.utcnow()
    session.add(solicitud)

    registrar_historial_solicitud(
        session,
        solicitud_id=solicitud.id or 0,
        estado_anterior=estado_anterior.value if estado_anterior else None,
        estado_nuevo=EstadoSolicitud.ASIGNADA.value,
        actor=current_user,
        comentario=(
            f"Cliente seleccionó cotización del taller {cotizacion.taller_id} "
            f"por {cotizacion.costo_estimado:.2f}."
        ),
    )

    if taller and taller.propietario_id:
        crear_notificacion(
            session,
            destinatario_id=taller.propietario_id,
            tipo=TipoNotificacion.SOLICITUD_ACEPTADA_CONDUCTOR,
            titulo="Cotización aceptada",
            mensaje=(
                f"El cliente aceptó tu cotización para la solicitud "
                f"#{solicitud.id}. Asigna un técnico."
            ),
            solicitud_id=solicitud.id,
            accion_url="/taller/solicitudes",
        )

    session.commit()
    session.refresh(cotizacion)
    payload_ws = _read(session, cotizacion).model_dump()
    _emit_solicitud(solicitud.id or 0, "cotizacion.aceptada", payload_ws)
    return _read(session, cotizacion)


@router.get("/taller", response_model=List[CotizacionRead])
def cotizaciones_del_taller(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Cotizaciones emitidas por el taller del usuario actual."""
    taller = _taller_del_usuario(session, current_user)
    cotizaciones = session.exec(
        select(Cotizacion)
        .where(Cotizacion.taller_id == taller.id)
        .order_by(Cotizacion.fecha_creacion.desc())
    ).all()
    return [_read(session, item) for item in cotizaciones]
