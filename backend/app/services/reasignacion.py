"""Lógica de reasignación automática estilo Uber/Yango.

Cuando un taller rechaza una solicitud (o expira el timeout sin responder),
saltamos al siguiente candidato de la lista calculada por el motor de scoring.
Si se acaba la lista, se intenta regenerarla; si tampoco hay nadie, la
solicitud vuelve a `PENDIENTE` y queda visible para otros talleres compatibles
en el próximo refresh del panel.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.models.domain import (
    EstadoCandidato,
    EstadoSolicitud,
    Solicitud,
    SolicitudCandidato,
    Taller,
    TipoNotificacion,
)
from app.models.user import User
from app.services.assignment import generar_candidatos, marcar_candidato, siguiente_candidato
from app.services.audit import registrar_historial_solicitud
from app.services.notificaciones import crear_notificacion


def rechazar_y_reasignar(
    session: Session,
    *,
    solicitud: Solicitud,
    taller_actual_id: int,
    actor: Optional[User],
    razon: str = "El taller rechazó la solicitud.",
) -> Optional[Taller]:
    """Marca el candidato actual como `RECHAZADO` y notifica al siguiente.

    Devuelve el `Taller` del nuevo candidato si se encontró, o `None` si la
    solicitud queda sin candidatos disponibles (vuelve a `PENDIENTE`).
    """
    marcar_candidato(
        session,
        solicitud,
        taller_id=taller_actual_id,
        estado=EstadoCandidato.RECHAZADO,
        razon=razon,
    )

    siguiente = siguiente_candidato(session, solicitud)
    if siguiente is None:
        # Intentamos regenerar la lista por si entró nueva oferta desde el
        # último cálculo (talleres que volvieron a `activo`, técnicos que se
        # liberaron, etc).
        generar_candidatos(session, solicitud)
        siguiente = siguiente_candidato(session, solicitud)

    if siguiente is None:
        solicitud.taller_id = None
        solicitud.estado = EstadoSolicitud.PENDIENTE
        session.add(solicitud)
        registrar_historial_solicitud(
            session,
            solicitud_id=solicitud.id or 0,
            estado_anterior=EstadoSolicitud.BUSCANDO_TALLER.value,
            estado_nuevo=EstadoSolicitud.PENDIENTE.value,
            actor=actor,
            comentario="Sin candidatos disponibles tras el rechazo.",
        )
        session.flush()
        return None

    siguiente.estado = EstadoCandidato.NOTIFICADO
    session.add(siguiente)

    taller_siguiente = session.get(Taller, siguiente.taller_id)
    if taller_siguiente and taller_siguiente.propietario_id:
        crear_notificacion(
            session,
            destinatario_id=taller_siguiente.propietario_id,
            tipo=TipoNotificacion.NUEVA_SOLICITUD_TALLER,
            titulo="Nueva solicitud reasignada",
            mensaje=(
                "Se te asignó como siguiente candidato para una solicitud que "
                "otro taller rechazó."
            ),
            solicitud_id=solicitud.id,
            accion_url="/taller/solicitudes",
        )

    solicitud.estado = EstadoSolicitud.BUSCANDO_TALLER
    session.add(solicitud)
    registrar_historial_solicitud(
        session,
        solicitud_id=solicitud.id or 0,
        estado_anterior=EstadoSolicitud.BUSCANDO_TALLER.value,
        estado_nuevo=EstadoSolicitud.BUSCANDO_TALLER.value,
        actor=actor,
        comentario=f"Rechazo de taller {taller_actual_id}: reasignado a {siguiente.taller_id}.",
    )
    session.flush()
    return taller_siguiente


def expirar_candidatos_sin_respuesta(
    session: Session,
    *,
    solicitud: Solicitud,
    timeout_segundos: int = 90,
) -> Optional[Taller]:
    """Expira candidatos `NOTIFICADO` que no respondieron en `timeout_segundos`.

    Pensado para ser invocado por un job periódico (cron / background task).
    Devuelve el `Taller` del nuevo candidato si hubo reasignación.
    """
    from datetime import datetime, timedelta

    umbral = datetime.utcnow() - timedelta(seconds=timeout_segundos)
    pendientes = session.exec(
        select(SolicitudCandidato)
        .where(SolicitudCandidato.solicitud_id == solicitud.id)
        .where(SolicitudCandidato.estado == EstadoCandidato.NOTIFICADO)
        .where(SolicitudCandidato.fecha_creacion <= umbral)
    ).all()

    if not pendientes:
        return None

    for candidato in pendientes:
        candidato.estado = EstadoCandidato.EXPIRADO
        candidato.razon = "Sin respuesta en el plazo permitido."
        session.add(candidato)
    session.flush()

    # Avanzamos al siguiente.
    return rechazar_y_reasignar(
        session,
        solicitud=solicitud,
        taller_actual_id=pendientes[-1].taller_id,
        actor=None,
        razon="Tiempo de respuesta agotado.",
    )
