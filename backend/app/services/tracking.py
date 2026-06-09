"""Servicio de tracking en tiempo real estilo Uber/Yango.

Centraliza el cálculo de ETA dinámico y el broadcast por WebSocket de cada
ping de ubicación del técnico. Se separa del router para que pueda invocarse
también desde el flujo de reasignación o desde un job programado.
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Optional

import anyio
from sqlmodel import select
from sqlmodel import Session

from app.models.domain import (
    Notificacion,
    Solicitud,
    Tecnico,
    TrackingPing,
    TipoNotificacion,
    Vehiculo,
)
from app.services.assignment import eta_desde_distancia, haversine_km
from app.services.notificaciones import crear_notificacion
from app.services.realtime import manager as realtime_manager, solicitud_room, taller_room


NEAR_ARRIVAL_TITLE = "El mecanico esta a punto de llegar"


def _near_arrival_threshold_km() -> float:
    try:
        return float(os.getenv("TRACKING_NEAR_ARRIVAL_KM", "0.35"))
    except ValueError:
        return 0.35


def _notificar_cliente_si_mecanico_cerca(
    session: Session,
    *,
    solicitud: Solicitud,
    tecnico: Tecnico,
    distancia_km: Optional[float],
) -> None:
    if distancia_km is None or distancia_km > _near_arrival_threshold_km():
        return
    if not solicitud.id or not solicitud.vehiculo_id:
        return

    vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
    if not vehiculo or not vehiculo.propietario_id:
        return

    ya_notificado = session.exec(
        select(Notificacion)
        .where(Notificacion.destinatario_id == vehiculo.propietario_id)
        .where(Notificacion.solicitud_id == solicitud.id)
        .where(Notificacion.titulo == NEAR_ARRIVAL_TITLE)
    ).first()
    if ya_notificado:
        return

    distancia_m = max(0, int(round(distancia_km * 1000)))
    mensaje = (
        f"{tecnico.nombre} esta cerca del punto de auxilio "
        f"(aprox. {distancia_m} m). Preparate para recibirlo."
    )
    crear_notificacion(
        session,
        destinatario_id=vehiculo.propietario_id,
        tipo=TipoNotificacion.TECNICO_EN_CAMINO,
        titulo=NEAR_ARRIVAL_TITLE,
        mensaje=mensaje,
        solicitud_id=solicitud.id,
        accion_url="/cliente/solicitudes",
        tenant_id=solicitud.tenant_id,
    )


def registrar_ping(
    session: Session,
    *,
    solicitud: Solicitud,
    tecnico: Tecnico,
    latitud: float,
    longitud: float,
    velocidad_kmh: Optional[float] = None,
    rumbo_grados: Optional[float] = None,
) -> TrackingPing:
    """Persiste el ping, actualiza la posición viva del técnico y recalcula ETA.

    El recálculo de ETA usa la distancia Haversine en línea recta multiplicada
    por un factor empírico (≈ velocidad media urbana). No reemplaza un motor
    de routing tipo OSRM, pero es suficiente para el MVP.
    """
    if solicitud.latitud is None or solicitud.longitud is None:
        # Sin coordenadas del incidente no se puede calcular ETA; persistimos
        # solo el ping crudo para auditoría.
        distancia = None
        eta = None
    else:
        distancia = haversine_km(latitud, longitud, solicitud.latitud, solicitud.longitud)
        if velocidad_kmh and velocidad_kmh > 5:
            # Si el técnico reporta velocidad real, usamos t = d / v (en min).
            eta = max(1, int(math.ceil((distancia / velocidad_kmh) * 60)))
        else:
            eta = eta_desde_distancia(distancia)

    ping = TrackingPing(
        solicitud_id=solicitud.id or 0,
        tecnico_id=tecnico.id or 0,
        tenant_id=solicitud.tenant_id,
        latitud=latitud,
        longitud=longitud,
        velocidad_kmh=velocidad_kmh,
        rumbo_grados=rumbo_grados,
        distancia_restante_km=round(distancia, 2) if distancia is not None else None,
        eta_minutos=eta,
    )
    session.add(ping)

    tecnico.latitud_actual = latitud
    tecnico.longitud_actual = longitud
    tecnico.ultima_actualizacion_ubicacion = datetime.utcnow()
    session.add(tecnico)

    if eta is not None:
        solicitud.tiempo_estimado_minutos = eta
    if distancia is not None:
        solicitud.distancia_estimada_km = round(distancia, 2)
    session.add(solicitud)

    _notificar_cliente_si_mecanico_cerca(
        session,
        solicitud=solicitud,
        tecnico=tecnico,
        distancia_km=distancia,
    )

    session.flush()
    return ping


def broadcast_ping(ping: TrackingPing, taller_id: Optional[int]) -> None:
    """Emite el ping a la sala de la solicitud y a la sala del taller dueño.

    Usa `anyio.from_thread.run` para que la función pueda invocarse desde el
    handler síncrono de FastAPI sin bloquear el loop.
    """
    payload = {
        "solicitud_id": ping.solicitud_id,
        "tecnico_id": ping.tecnico_id,
        "latitud": ping.latitud,
        "longitud": ping.longitud,
        "velocidad_kmh": ping.velocidad_kmh,
        "rumbo_grados": ping.rumbo_grados,
        "distancia_restante_km": ping.distancia_restante_km,
        "eta_minutos": ping.eta_minutos,
        "fecha": ping.fecha_creacion.isoformat() if ping.fecha_creacion else None,
    }

    async def _emit() -> None:
        await realtime_manager.broadcast_room(
            solicitud_room(ping.solicitud_id), "tracking.update", payload
        )
        if taller_id:
            await realtime_manager.broadcast_room(
                taller_room(taller_id), "tracking.update", payload
            )

    try:
        anyio.from_thread.run(_emit)
    except RuntimeError:
        # Si no estamos dentro de un loop (tests, scripts), ignoramos.
        pass
