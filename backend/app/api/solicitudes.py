import logging
import math
import unicodedata
from datetime import datetime
from typing import List, Optional

import anyio
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    AnalisisIA,
    CalificacionCreate,
    CalificacionRead,
    CalificacionServicio,
    ChatMensaje,
    ChatMensajeCreate,
    ChatMensajeRead,
    EstadoCandidato,
    EstadoSolicitud,
    Evidencia,
    Pago,
    PagoRead,
    Solicitud,
    SolicitudCandidato,
    SolicitudCandidatoRead,
    SolicitudCreate,
    SolicitudHistorial,
    SolicitudHistorialRead,
    SolicitudRead,
    Taller,
    Tecnico,
    TipoNotificacion,
    TipoEvidencia,
    Vehiculo,
    VehiculoHistorialReparacion,
)
from app.models.user import User, UserRole
from app.services.ai import analyze_incident, summarize_audio_file
from app.services.assignment import generar_candidatos, marcar_candidato, siguiente_candidato
from app.services.audit import registrar_auditoria, registrar_historial_solicitud
from app.services.notificaciones import crear_notificacion, crear_notificaciones_para_usuarios
from app.services.realtime import manager as realtime_manager, solicitud_room, taller_room
from app.services.storage import save_upload_file, url_to_path

router = APIRouter()
logger = logging.getLogger(__name__)

RADIO_TALLERES_CANDIDATOS_KM = 25.0
MAX_TALLERES_CANDIDATOS = 12

ESTADOS_CERRADOS = {
    EstadoSolicitud.RESUELTA,
    EstadoSolicitud.CANCELADA,
    EstadoSolicitud.FINALIZADO,
    EstadoSolicitud.CANCELADO,
}

ESTADOS_PENDIENTES_TALLER = {
    EstadoSolicitud.PENDIENTE,
    EstadoSolicitud.BUSCANDO_TALLER,
}

ESTADO_ALIASES = {
    "en_progreso": EstadoSolicitud.TECNICO_EN_CAMINO,
    "llegada": EstadoSolicitud.TECNICO_LLEGO,
    "resuelta": EstadoSolicitud.FINALIZADO,
    "cancelada": EstadoSolicitud.CANCELADO,
}


def normalizar_estado_operativo(estado: str | EstadoSolicitud) -> EstadoSolicitud:
    if isinstance(estado, EstadoSolicitud):
        return ESTADO_ALIASES.get(estado.value, estado)
    estado_normalizado = estado.strip()
    if estado_normalizado in ESTADO_ALIASES:
        return ESTADO_ALIASES[estado_normalizado]
    try:
        return EstadoSolicitud(estado_normalizado)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado invalido. Estados validos: {[item.value for item in EstadoSolicitud]}",
        ) from exc


def estado_es_cerrado(estado: EstadoSolicitud) -> bool:
    return estado in ESTADOS_CERRADOS


async def _broadcast_solicitud_update(solicitud_id: int, payload: dict) -> None:
    await realtime_manager.broadcast_room(
        solicitud_room(solicitud_id),
        "solicitud.actualizada",
        payload,
    )


def emitir_solicitud_update(solicitud_id: int, payload: dict) -> None:
    try:
        anyio.from_thread.run(_broadcast_solicitud_update, solicitud_id, payload)
    except RuntimeError:
        pass


async def _broadcast_talleres_update(taller_ids: list[int], payload: dict) -> None:
    for taller_id in taller_ids:
        await realtime_manager.broadcast_room(
            taller_room(taller_id),
            "taller.solicitud_actualizada",
            payload,
        )


def emitir_talleres_update(session: Session, solicitud: Solicitud, payload: dict) -> None:
    talleres = obtener_talleres_candidatos_para_notificar(session, solicitud)
    taller_ids = {
        taller.id
        for taller in talleres
        if taller.id is not None
    }
    if solicitud.taller_id is not None:
        taller_ids.add(solicitud.taller_id)

    if not taller_ids:
        return

    try:
        anyio.from_thread.run(_broadcast_talleres_update, sorted(taller_ids), payload)
    except RuntimeError:
        pass


def _obtener_taller_actual(session: Session, current_user: User) -> Taller:
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un taller vinculado a este usuario.",
        )

    return taller


def _obtener_tecnico_actual(session: Session, current_user: User) -> Tecnico:
    tecnico = session.exec(
        select(Tecnico).where(Tecnico.id_usuario == current_user.id)
    ).first()

    if not tecnico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un perfil tecnico vinculado a este usuario.",
        )

    return tecnico

class PagoPayload(BaseModel):
    monto: Optional[float] = None
    metodo: Optional[str] = "tarjeta"


class CostoPayload(BaseModel):
    monto: float


def simular_procesamiento_ia(descripcion: str):
    clasificacion = "General"
    prioridad = "Baja"
    resumen = "El cliente reporta un problema no clasificado."

    desc_eval = descripcion.lower()

    if "no enciende" in desc_eval or "bateria" in desc_eval or "batería" in desc_eval or "click click" in desc_eval or "arranca" in desc_eval:
        clasificacion = "Problema de Bateria / Electrico"
        prioridad = "Media"
        resumen = "El vehiculo no responde al arranque, posible descarga de bateria o falla en el alternador. Requiere auxilio electrico."
    elif "pinchada" in desc_eval or "llanta" in desc_eval:
        clasificacion = "Neumaticos"
        prioridad = "Baja"
        resumen = "Vehiculo inmovilizado por llanta pinchada. Requiere taller movil o grua para cambio."
    elif "humo" in desc_eval or "recalentado" in desc_eval:
        clasificacion = "Problema de Motor / Recalentamiento"
        prioridad = "Alta"
        resumen = "Alerta critica: posible fuga de refrigerante o problema grave de motor. Riesgo de dano permanente."

    return clasificacion, prioridad, resumen


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def normalizar_texto_busqueda(texto: Optional[str]) -> str:
    if not texto:
        return ""

    texto_ascii = unicodedata.normalize("NFKD", texto)
    texto_ascii = "".join(caracter for caracter in texto_ascii if not unicodedata.combining(caracter))
    return " ".join(texto_ascii.casefold().split())


def palabras_clave_para_solicitud(solicitud: Solicitud) -> list[str]:
    texto = normalizar_texto_busqueda(
        f"{solicitud.clasificacion_ia or ''} {solicitud.descripcion or ''}"
    )

    if any(palabra in texto for palabra in ["bateria", "electrico", "electricidad", "arranque", "alternador"]):
        return ["bateria", "electrico", "electricidad", "arranque", "alternador"]

    if any(palabra in texto for palabra in ["llanta", "neumatico", "rueda", "pinchada", "pinchado"]):
        return ["llanta", "neumatico", "rueda", "pinchada", "vulcanizacion"]

    if any(palabra in texto for palabra in ["motor", "recalentamiento", "humo", "radiador", "refrigerante"]):
        return ["motor", "recalentamiento", "radiador", "mecanica", "refrigerante"]

    if any(palabra in texto for palabra in ["cerrajeria", "llave", "cerradura", "bloqueo"]):
        return ["cerrajeria", "llave", "cerradura", "bloqueo"]

    return ["general", "mecanica", "auxilio", "emergencia"]


def distancia_taller_solicitud(solicitud: Solicitud, taller: Taller) -> float:
    if taller.latitud is None or taller.longitud is None:
        return float("inf")

    return haversine_km(solicitud.latitud, solicitud.longitud, taller.latitud, taller.longitud)


def taller_es_compatible_con_solicitud(taller: Taller, solicitud: Solicitud) -> bool:
    if not taller.notificaciones_push or not taller.notificaciones_nuevas_asignaciones:
        return False

    palabras_clave = palabras_clave_para_solicitud(solicitud)
    especialidades = [
        normalizar_texto_busqueda(especialidad.nombre)
        for especialidad in taller.especialidades
    ]

    if not especialidades:
        return True

    return any(
        palabra_clave in especialidad
        for especialidad in especialidades
        for palabra_clave in palabras_clave
    ) or any(especialidad in {"general", "mecanica", "mecanica general"} for especialidad in especialidades)


def obtener_talleres_candidatos_para_notificar(
    session: Session,
    solicitud: Solicitud,
) -> list[Taller]:
    candidatos = session.exec(
        select(SolicitudCandidato)
        .where(SolicitudCandidato.solicitud_id == solicitud.id)
        .order_by(SolicitudCandidato.posicion)
    ).all()
    if not candidatos:
        return []

    talleres_por_id = {
        taller.id: taller
        for taller in session.exec(
            select(Taller).where(Taller.id.in_([item.taller_id for item in candidatos]))
        ).all()
        if taller.id is not None and taller.activo
    }
    return [
        talleres_por_id[item.taller_id]
        for item in candidatos
        if item.taller_id in talleres_por_id
    ]


def taller_es_candidato_para_solicitud(
    session: Session,
    taller: Taller,
    solicitud: Solicitud,
) -> bool:
    return any(
        candidato.id == taller.id
        for candidato in obtener_talleres_candidatos_para_notificar(session, solicitud)
    )


def notificar_talleres_candidatos(session: Session, solicitud: Solicitud) -> None:
    talleres_candidatos = obtener_talleres_candidatos_para_notificar(session, solicitud)
    destinatario_ids = [
        taller.propietario_id
        for taller in talleres_candidatos
        if taller.propietario_id is not None
    ]

    if not destinatario_ids:
        return

    titulo = "Nueva solicitud de auxilio"
    clasificacion = solicitud.clasificacion_ia or "Servicio mecanico"
    mensaje = (
        f"Hay una nueva solicitud compatible cerca de tu taller: {clasificacion}. "
        "Revisa los detalles para aceptarla."
    )

    crear_notificaciones_para_usuarios(
        session,
        destinatario_ids=destinatario_ids,
        tipo=TipoNotificacion.NUEVA_SOLICITUD_TALLER,
        titulo=titulo,
        mensaje=mensaje,
        solicitud_id=solicitud.id,
        accion_url="/taller/solicitudes",
    )


def notificar_cancelacion_conductor_a_talleres(
    session: Session,
    solicitud: Solicitud,
) -> None:
    talleres_destino: list[Taller] = []

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller:
            talleres_destino = [taller]
    else:
        talleres_destino = obtener_talleres_candidatos_para_notificar(session, solicitud)

    destinatario_ids = [
        taller.propietario_id
        for taller in talleres_destino
        if taller.propietario_id is not None
    ]

    if not destinatario_ids:
        return

    crear_notificaciones_para_usuarios(
        session,
        destinatario_ids=destinatario_ids,
        tipo=TipoNotificacion.SOLICITUD_CANCELADA_CONDUCTOR,
        titulo="Solicitud cancelada por el conductor",
        mensaje="El conductor cancelo la solicitud de auxilio.",
        solicitud_id=solicitud.id,
        accion_url="/taller/solicitudes",
    )


def notificar_cancelacion_taller_a_conductor(
    session: Session,
    solicitud: Solicitud,
    taller: Taller,
) -> None:
    vehiculo = request_vehicle(session, solicitud)
    if not vehiculo or vehiculo.propietario_id is None:
        return

    crear_notificacion(
        session,
        destinatario_id=vehiculo.propietario_id,
        tipo=TipoNotificacion.SOLICITUD_CANCELADA_TALLER,
        titulo="Solicitud cancelada por el taller",
        mensaje=(
            f"{taller.nombre_comercial} cancelo la atencion de tu solicitud. "
            "Puedes crear una nueva solicitud si todavia necesitas auxilio."
        ),
        solicitud_id=solicitud.id,
        accion_url="/cliente",
    )


def notificar_solicitud_aceptada_conductor(
    session: Session,
    solicitud: Solicitud,
    taller: Taller,
) -> None:
    vehiculo = request_vehicle(session, solicitud)
    if not vehiculo or vehiculo.propietario_id is None:
        return

    crear_notificacion(
        session,
        destinatario_id=vehiculo.propietario_id,
        tipo=TipoNotificacion.SOLICITUD_ACEPTADA_CONDUCTOR,
        titulo="Solicitud aceptada",
        mensaje=(
            f"{taller.nombre_comercial} acepto tu solicitud de auxilio. "
            "Pronto recibiras la informacion del tecnico asignado."
        ),
        solicitud_id=solicitud.id,
        accion_url="/cliente",
    )


def notificar_tecnico_asignado(
    session: Session,
    solicitud: Solicitud,
    tecnico: Tecnico,
) -> None:
    if tecnico.id_usuario is None:
        return

    crear_notificacion(
        session,
        destinatario_id=tecnico.id_usuario,
        tipo=TipoNotificacion.TECNICO_ASIGNADO,
        titulo="Nueva solicitud asignada",
        mensaje=(
            "Se te asigno una solicitud de auxilio mecanico. "
            "Revisa los detalles para iniciar la atencion."
        ),
        solicitud_id=solicitud.id,
        accion_url="/tecnico",
    )


def notificar_tecnico_en_camino_conductor(
    session: Session,
    solicitud: Solicitud,
    tecnico: Tecnico,
) -> None:
    vehiculo = request_vehicle(session, solicitud)
    if not vehiculo or vehiculo.propietario_id is None:
        return

    mensaje = f"{tecnico.nombre} esta en camino para atender tu solicitud."
    if solicitud.tiempo_estimado_minutos:
        mensaje += f" Tiempo estimado: {solicitud.tiempo_estimado_minutos} minutos."

    crear_notificacion(
        session,
        destinatario_id=vehiculo.propietario_id,
        tipo=TipoNotificacion.TECNICO_EN_CAMINO,
        titulo="Tecnico en camino",
        mensaje=mensaje,
        solicitud_id=solicitud.id,
        accion_url="/cliente",
    )


def notificar_tecnico_en_camino_taller(
    session: Session,
    solicitud: Solicitud,
    tecnico: Tecnico,
) -> None:
    if not solicitud.taller_id:
        return

    taller = session.get(Taller, solicitud.taller_id)
    if not taller or taller.propietario_id is None:
        return

    crear_notificacion(
        session,
        destinatario_id=taller.propietario_id,
        tipo=TipoNotificacion.TECNICO_EN_CAMINO,
        titulo="Mecanico en camino",
        mensaje=f"{tecnico.nombre} salio rumbo al incidente de la solicitud #{solicitud.id}.",
        solicitud_id=solicitud.id,
        accion_url="/taller/solicitudes",
    )


def notificar_llegada_mecanico(
    session: Session,
    solicitud: Solicitud,
    tecnico: Tecnico,
) -> None:
    destinatarios: list[int] = []
    vehiculo = request_vehicle(session, solicitud)
    if vehiculo and vehiculo.propietario_id is not None:
        destinatarios.append(vehiculo.propietario_id)

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller and taller.propietario_id is not None:
            destinatarios.append(taller.propietario_id)

    crear_notificaciones_para_usuarios(
        session,
        destinatario_ids=destinatarios,
        tipo=TipoNotificacion.TECNICO_LLEGO,
        titulo="Mecanico llego al incidente",
        mensaje=f"{tecnico.nombre} llego al punto de asistencia de la solicitud #{solicitud.id}.",
        solicitud_id=solicitud.id,
        accion_url="/solicitudes",
    )


def notificar_servicio_terminado(
    session: Session,
    solicitud: Solicitud,
    tecnico: Optional[Tecnico] = None,
) -> None:
    destinatarios: list[int] = []
    vehiculo = request_vehicle(session, solicitud)
    if vehiculo and vehiculo.propietario_id is not None:
        destinatarios.append(vehiculo.propietario_id)

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller and taller.propietario_id is not None:
            destinatarios.append(taller.propietario_id)

    nombre = tecnico.nombre if tecnico else "El mecanico"
    crear_notificaciones_para_usuarios(
        session,
        destinatario_ids=destinatarios,
        tipo=TipoNotificacion.SERVICIO_TERMINADO,
        titulo="Servicio finalizado",
        mensaje=f"{nombre} marco como finalizado el servicio de la solicitud #{solicitud.id}.",
        solicitud_id=solicitud.id,
        accion_url="/solicitudes",
    )


def notificar_pago_confirmado_taller(
    session: Session,
    solicitud: Solicitud,
) -> None:
    if not solicitud.taller_id:
        return

    taller = session.get(Taller, solicitud.taller_id)
    if not taller or taller.propietario_id is None:
        return

    monto = solicitud.precio_cobrado or 0
    crear_notificacion(
        session,
        destinatario_id=taller.propietario_id,
        tipo=TipoNotificacion.SERVICIO_CONCLUIDO_PAGO,
        titulo="Pago confirmado",
        mensaje=f"Cliente pago Bs {monto:.2f} por la solicitud #{solicitud.id}.",
        solicitud_id=solicitud.id,
        accion_url="/taller/solicitudes",
    )


def notificar_cancelacion_a_mecanico(
    session: Session,
    solicitud: Solicitud,
) -> None:
    if not solicitud.tecnico_id:
        return

    tecnico = session.get(Tecnico, solicitud.tecnico_id)
    if not tecnico or tecnico.id_usuario is None:
        return

    crear_notificacion(
        session,
        destinatario_id=tecnico.id_usuario,
        tipo=TipoNotificacion.SOLICITUD_CANCELADA_MECANICO,
        titulo="Solicitud cancelada",
        mensaje=f"La solicitud #{solicitud.id} fue cancelada.",
        solicitud_id=solicitud.id,
        accion_url="/tecnico",
    )


def notificar_cancelacion_mecanico_a_taller_y_conductor(
    session: Session,
    solicitud: Solicitud,
    tecnico: Tecnico,
) -> None:
    destinatarios: list[int] = []
    vehiculo = request_vehicle(session, solicitud)
    if vehiculo and vehiculo.propietario_id is not None:
        destinatarios.append(vehiculo.propietario_id)

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller and taller.propietario_id is not None:
            destinatarios.append(taller.propietario_id)

    crear_notificaciones_para_usuarios(
        session,
        destinatario_ids=destinatarios,
        tipo=TipoNotificacion.SOLICITUD_CANCELADA_MECANICO,
        titulo="Solicitud cancelada por el mecanico",
        mensaje=f"{tecnico.nombre} cancelo la atencion de la solicitud #{solicitud.id}.",
        solicitud_id=solicitud.id,
        accion_url="/solicitudes",
    )


def estimate_eta_minutes(solicitud: Solicitud, tecnico: Optional[Tecnico], taller: Optional[Taller]) -> int:
    if tecnico and tecnico.latitud is not None and tecnico.longitud is not None:
        distance_km = haversine_km(solicitud.latitud, solicitud.longitud, tecnico.latitud, tecnico.longitud)
        return max(8, min(90, int(round(distance_km * 2.6 + 8))))

    if taller and taller.latitud is not None and taller.longitud is not None:
        distance_km = haversine_km(solicitud.latitud, solicitud.longitud, taller.latitud, taller.longitud)
        return max(12, min(110, int(round(distance_km * 3 + 10))))

    return 30


def estimate_pricing(clasificacion: Optional[str], prioridad: Optional[str]) -> tuple[float, float]:
    base_amount = 120.0

    if clasificacion == "Problema de Bateria / Electrico":
        base_amount = 150.0
    elif clasificacion == "Neumaticos":
        base_amount = 110.0
    elif clasificacion == "Problema de Motor / Recalentamiento":
        base_amount = 220.0

    if prioridad == "Alta":
        base_amount += 70.0
    elif prioridad == "Media":
        base_amount += 30.0

    platform_fee = round(base_amount * 0.10, 2)
    return round(base_amount, 2), platform_fee


def obtener_taller_del_usuario(session: Session, current_user: User) -> Taller | None:
    return session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()


def request_vehicle(session: Session, solicitud: Solicitud) -> Optional[Vehiculo]:
    if not solicitud.vehiculo_id:
        return None
    return session.get(Vehiculo, solicitud.vehiculo_id)


def registrar_historial_vehiculo_desde_solicitud(
    session: Session,
    solicitud: Solicitud,
    *,
    tecnico: Optional[Tecnico] = None,
    observaciones: Optional[str] = None,
) -> None:
    vehiculo = request_vehicle(session, solicitud)
    if not vehiculo or vehiculo.id is None:
        return

    existente = None
    if solicitud.id is not None:
        existente = session.exec(
            select(VehiculoHistorialReparacion)
            .where(VehiculoHistorialReparacion.solicitud_id == solicitud.id)
            .where(VehiculoHistorialReparacion.vehiculo_id == vehiculo.id)
        ).first()

    tecnico_actual = tecnico
    if tecnico_actual is None and solicitud.tecnico_id:
        tecnico_actual = session.get(Tecnico, solicitud.tecnico_id)

    titulo = solicitud.clasificacion_ia or "Atencion de auxilio vehicular"
    diagnostico = solicitud.resumen_ia or solicitud.descripcion
    acciones = (
        "Servicio marcado como finalizado por el mecanico asignado. "
        "Usar esta ficha como antecedente tecnico del vehiculo."
    )

    item = existente or VehiculoHistorialReparacion(
        vehiculo_id=vehiculo.id,
        solicitud_id=solicitud.id,
        tenant_id=solicitud.tenant_id,
        fecha_servicio=solicitud.fecha_finalizado or datetime.utcnow(),
    )
    item.taller_id = solicitud.taller_id
    item.tecnico_id = solicitud.tecnico_id or (tecnico_actual.id if tecnico_actual else None)
    item.tenant_id = solicitud.tenant_id
    item.titulo = titulo
    item.diagnostico = diagnostico
    item.acciones_realizadas = acciones
    item.categoria = solicitud.clasificacion_ia
    item.prioridad = solicitud.prioridad_ia
    item.costo = solicitud.precio_cobrado
    item.estado_pago = solicitud.estado_pago or "pendiente"
    item.observaciones = observaciones
    item.fecha_servicio = solicitud.fecha_finalizado or item.fecha_servicio or datetime.utcnow()
    item.fecha_actualizacion = datetime.utcnow()
    session.add(item)


def build_solicitud_read(session: Session, solicitud: Solicitud) -> SolicitudRead:
    data = SolicitudRead.model_validate(solicitud)
    taller_nombre = None
    taller_latitud = None
    taller_longitud = None
    tecnico_nombre = None
    tecnico_especialidad = None
    tecnico_latitud = None
    tecnico_longitud = None
    distancia_tecnico_km = None
    vehiculo_placa = None
    vehiculo_descripcion = None
    audio_url = None
    audio_resumen_ia = None
    ruta_recomendada_ia = None

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller:
            taller_nombre = taller.nombre_comercial
            taller_latitud = taller.latitud
            taller_longitud = taller.longitud

    if solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico_nombre = tecnico.nombre
            # Tracking live: preferimos la posicion actualizada por los pings
            # del mecanico. Si aun no existe, usamos la ubicacion base.
            tecnico_latitud = tecnico.latitud_actual if tecnico.latitud_actual is not None else tecnico.latitud
            tecnico_longitud = tecnico.longitud_actual if tecnico.longitud_actual is not None else tecnico.longitud
            if tecnico_latitud is not None and tecnico_longitud is not None:
                distancia_tecnico_km = round(
                    haversine_km(solicitud.latitud, solicitud.longitud, tecnico_latitud, tecnico_longitud),
                    2,
                )
            if tecnico.especialidades:
                tecnico_especialidad = ", ".join(
                    especialidad.nombre for especialidad in tecnico.especialidades
                )

    vehiculo = request_vehicle(session, solicitud)
    if vehiculo:
        vehiculo_placa = vehiculo.placa
        vehiculo_descripcion = f"{vehiculo.marca} {vehiculo.modelo}".strip()

    audio = session.exec(
        select(Evidencia)
        .where(Evidencia.solicitud_id == solicitud.id)
        .where(Evidencia.tipo_evidencia == TipoEvidencia.AUDIO)
        .order_by(Evidencia.fecha_subida.desc())
    ).first()
    if audio:
        audio_url = audio.ruta_archivo

    if solicitud.resumen_ia and "Resumen del audio:" in solicitud.resumen_ia:
        audio_resumen_ia = solicitud.resumen_ia.split("Resumen del audio:", 1)[1].strip()

    if solicitud.latitud is not None and solicitud.longitud is not None:
        origin_lat = tecnico_latitud if tecnico_latitud is not None else taller_latitud
        origin_lng = tecnico_longitud if tecnico_longitud is not None else taller_longitud
        if origin_lat is not None and origin_lng is not None:
            ruta_recomendada_ia = (
                "Ruta sugerida: salir desde el punto asignado del taller/mecanico y usar la via mas rapida "
                f"hacia {solicitud.latitud:.6f}, {solicitud.longitud:.6f}. "
                f"ETA estimado: {solicitud.tiempo_estimado_minutos or estimate_eta_minutes(solicitud, None, None)} minutos."
            )

    return data.model_copy(
        update={
            "taller_nombre": taller_nombre,
            "taller_latitud": taller_latitud,
            "taller_longitud": taller_longitud,
            "tecnico_nombre": tecnico_nombre,
            "tecnico_especialidad": tecnico_especialidad,
            "tecnico_latitud": tecnico_latitud,
            "tecnico_longitud": tecnico_longitud,
            "distancia_tecnico_km": distancia_tecnico_km,
            "vehiculo_placa": vehiculo_placa,
            "vehiculo_descripcion": vehiculo_descripcion,
            "audio_url": audio_url,
            "audio_resumen_ia": audio_resumen_ia,
            "ruta_recomendada_ia": ruta_recomendada_ia,
        }
    )


def reanalizar_solicitud_con_evidencias(session: Session, solicitud: Solicitud) -> None:
    evidencias = session.exec(
        select(Evidencia).where(Evidencia.solicitud_id == solicitud.id)
    ).all()
    image_paths: list[str] = []
    audio_paths: list[str] = []

    for evidencia in evidencias:
        local_path = url_to_path(evidencia.ruta_archivo)
        if not local_path:
            continue
        if evidencia.tipo_evidencia == TipoEvidencia.IMAGEN:
            image_paths.append(str(local_path))
        elif evidencia.tipo_evidencia == TipoEvidencia.AUDIO:
            audio_paths.append(str(local_path))

    analysis = analyze_incident(
        descripcion=solicitud.descripcion,
        image_paths=image_paths,
        audio_paths=audio_paths[:1],
    )
    audio_summary = None
    if solicitud.resumen_ia and "Resumen del audio:" in solicitud.resumen_ia:
        audio_summary = solicitud.resumen_ia.split("Resumen del audio:", 1)[1].strip()

    solicitud.clasificacion_ia = analysis.clasificacion
    solicitud.prioridad_ia = analysis.prioridad
    solicitud.resumen_ia = analysis.resumen
    solicitud.especialidad_requerida_ia = analysis.especialidad_requerida
    solicitud.especialidad_requerida_ia = analysis.especialidad_requerida
    if audio_summary:
        solicitud.resumen_ia = f"{solicitud.resumen_ia}\nResumen del audio: {audio_summary}".strip()
    solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(
        solicitud.clasificacion_ia,
        solicitud.prioridad_ia,
    )
    session.add(
        AnalisisIA(
            solicitud_id=solicitud.id or 0,
            tenant_id=solicitud.tenant_id,
            modalidad="multimodal",
            clasificacion=analysis.clasificacion,
            prioridad=analysis.prioridad,
            resumen=analysis.resumen,
            especialidad_requerida=analysis.especialidad_requerida,
            proveedor="gemini-o-fallback",
        )
    )
    generar_candidatos(session, solicitud)
    session.add(solicitud)


def notificar_reporte_actualizado(
    session: Session,
    solicitud: Solicitud,
    detalle: str,
) -> None:
    destinatarios: list[int] = []
    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller and taller.propietario_id is not None:
            destinatarios.append(taller.propietario_id)
    else:
        destinatarios.extend(
            taller.propietario_id
            for taller in obtener_talleres_candidatos_para_notificar(session, solicitud)
            if taller.propietario_id is not None
        )

    if not destinatarios:
        return

    crear_notificaciones_para_usuarios(
        session,
        destinatario_ids=destinatarios,
        tipo=TipoNotificacion.GENERAL,
        titulo="Reporte actualizado",
        mensaje=f"La solicitud #{solicitud.id} se actualizo con {detalle}.",
        solicitud_id=solicitud.id,
        accion_url="/taller/solicitudes",
    )


def ensure_request_visible_to_user(session: Session, solicitud: Solicitud, current_user: User) -> None:
    if current_user.role == UserRole.ADMIN:
        if (
            current_user.tenant_id is not None
            and solicitud.tenant_id is not None
            and current_user.tenant_id != solicitud.tenant_id
        ):
            raise HTTPException(status_code=403, detail="Solicitud fuera de tu tenant")
        return

    if current_user.role == UserRole.WORKSHOP:
        taller = obtener_taller_del_usuario(session, current_user)
        solicitud_asignada_al_taller = taller and solicitud.taller_id == taller.id
        solicitud_pendiente_candidata = (
            taller
            and solicitud.taller_id in {None, taller.id}
            and solicitud.estado in ESTADOS_PENDIENTES_TALLER
            and taller_es_candidato_para_solicitud(session, taller, solicitud)
        )

        if not solicitud_asignada_al_taller and not solicitud_pendiente_candidata:
            raise HTTPException(status_code=403, detail="No tienes permisos para ver esta solicitud")
        return

    if current_user.role == UserRole.TECNICO:
        tecnico = session.exec(
            select(Tecnico).where(Tecnico.id_usuario == current_user.id)
        ).first()
        if not tecnico or solicitud.tecnico_id != tecnico.id:
            raise HTTPException(status_code=403, detail="No tienes permisos para ver esta solicitud")
        return

    vehiculo = request_vehicle(session, solicitud)
    if not vehiculo or vehiculo.propietario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver esta solicitud")


def assign_best_technician(session: Session, solicitud: Solicitud) -> tuple[Optional[Tecnico], Optional[Taller]]:
    statement = select(Tecnico).where(Tecnico.disponible == True)
    if solicitud.tenant_id is not None:
        statement = statement.where(Tecnico.tenant_id == solicitud.tenant_id)
    tecnicos = session.exec(statement).all()
    if not tecnicos:
        return None, None

    best_tecnico: Optional[Tecnico] = None
    best_distance = float("inf")

    for tecnico in tecnicos:
        if tecnico.latitud is None or tecnico.longitud is None:
            distance = 35.0
        else:
            distance = haversine_km(solicitud.latitud, solicitud.longitud, tecnico.latitud, tecnico.longitud)

        if distance < best_distance:
            best_distance = distance
            best_tecnico = tecnico

    if not best_tecnico:
        return None, None

    taller = session.get(Taller, best_tecnico.taller_id) if best_tecnico.taller_id else None
    return best_tecnico, taller


def assign_best_workshop(session: Session, solicitud: Solicitud) -> Optional[Taller]:
    statement = select(Taller)
    if solicitud.tenant_id is not None:
        statement = statement.where(Taller.tenant_id == solicitud.tenant_id)
    talleres = session.exec(statement).all()
    if not talleres:
        return None

    best_taller: Optional[Taller] = None
    best_distance = float("inf")

    for taller in talleres:
        if taller.latitud is None or taller.longitud is None:
            distance = 40.0
        else:
            distance = haversine_km(solicitud.latitud, solicitud.longitud, taller.latitud, taller.longitud)

        if distance < best_distance:
            best_distance = distance
            best_taller = taller

    return best_taller


def update_service_totals(session: Session, solicitud: Solicitud, was_resolved: bool) -> None:
    if was_resolved or solicitud.estado not in {EstadoSolicitud.RESUELTA, EstadoSolicitud.FINALIZADO} or not solicitud.taller_id:
        return

    taller = session.get(Taller, solicitud.taller_id)
    if not taller:
        return

    taller.total_servicios_completados += 1
    session.add(taller)


@router.post("/", response_model=SolicitudRead)
def crear_solicitud(
    *,
    request: Request,
    session: Session = Depends(get_session),
    solicitud_in: SolicitudCreate,
    current_user: User = Depends(get_current_user),
):
    solicitud = Solicitud.model_validate(solicitud_in)
    cliente_sync_id = (
        solicitud_in.cliente_sync_id
        or request.headers.get("X-Idempotency-Key")
        or ""
    ).strip() or None

    if cliente_sync_id:
        existing_statement = (
            select(Solicitud)
            .where(Solicitud.cliente_sync_id == cliente_sync_id)
        )
        if current_user.role == UserRole.DRIVER:
            existing_statement = (
                existing_statement
                .join(Vehiculo)
                .where(Vehiculo.propietario_id == current_user.id)
            )
        existente = session.exec(existing_statement).first()
        if existente:
            return build_solicitud_read(session, existente)

    analysis = analyze_incident(descripcion=solicitud.descripcion)
    solicitud.clasificacion_ia = analysis.clasificacion
    solicitud.prioridad_ia = analysis.prioridad
    solicitud.resumen_ia = analysis.resumen
    solicitud.estado_pago = "pendiente"
    solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(
        solicitud.clasificacion_ia,
        solicitud.prioridad_ia,
    )

    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
        if current_user.role == UserRole.DRIVER and vehiculo.propietario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No puedes reportar con un vehiculo de otro usuario")

    solicitud.estado = EstadoSolicitud.PENDIENTE
    solicitud.taller_id = None
    solicitud.tecnico_id = None
    solicitud.cliente_sync_id = cliente_sync_id
    solicitud.tiempo_estimado_minutos = None
    # Multi-tenant: la solicitud hereda el tenant del cliente. Si el cliente
    # es admin global sin tenant la solicitud se crea sin tenant (no es un
    # caso esperado en producción).
    solicitud.tenant_id = current_user.tenant_id

    session.add(solicitud)
    session.flush()
    session.add(
        AnalisisIA(
            solicitud_id=solicitud.id or 0,
            modalidad="texto",
            clasificacion=solicitud.clasificacion_ia or "Incidente general",
            prioridad=solicitud.prioridad_ia or "Baja",
            resumen=solicitud.resumen_ia or "",
            especialidad_requerida=solicitud.especialidad_requerida_ia,
            proveedor="gemini-o-fallback",
            tenant_id=solicitud.tenant_id,
        )
    )
    registrar_historial_solicitud(
        session,
        solicitud_id=solicitud.id or 0,
        estado_anterior=None,
        estado_nuevo=EstadoSolicitud.PENDIENTE.value,
        actor=current_user,
        comentario="Solicitud creada por el cliente.",
    )
    candidatos = generar_candidatos(session, solicitud)
    if solicitud.estado == EstadoSolicitud.BUSCANDO_TALLER:
        registrar_historial_solicitud(
            session,
            solicitud_id=solicitud.id or 0,
            estado_anterior=EstadoSolicitud.PENDIENTE.value,
            estado_nuevo=EstadoSolicitud.BUSCANDO_TALLER.value,
            actor=current_user,
            comentario="Motor de asignacion genero talleres candidatos.",
        )
    elif not candidatos:
        comentario_alerta = (
            "Alerta interna: la solicitud quedo sin candidatos tras el matching "
            "automatico. Revisar cobertura, capacidad o configuracion de talleres."
        )
        registrar_historial_solicitud(
            session,
            solicitud_id=solicitud.id or 0,
            estado_anterior=EstadoSolicitud.PENDIENTE.value,
            estado_nuevo=EstadoSolicitud.PENDIENTE.value,
            actor=current_user,
            comentario=comentario_alerta,
        )
        logger.warning(
            "Solicitud %s creada sin candidatos. tenant=%s lat=%s lon=%s clasificacion=%s descripcion=%s",
            solicitud.id,
            solicitud.tenant_id,
            solicitud.latitud,
            solicitud.longitud,
            solicitud.clasificacion_ia,
            solicitud.descripcion,
        )
    session.commit()
    session.refresh(solicitud)
    notificar_talleres_candidatos(session, solicitud)
    session.commit()
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.get("/", response_model=List[SolicitudRead])
def listar_solicitudes(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(Solicitud).offset(skip).limit(limit)
    if current_user.tenant_id is not None:
        statement = statement.where(Solicitud.tenant_id == current_user.tenant_id)

    if current_user.role == UserRole.ADMIN:
        solicitudes = session.exec(statement).all()
    elif current_user.role == UserRole.WORKSHOP:
        taller = obtener_taller_del_usuario(session, current_user)
        if not taller:
            return []
        solicitudes = session.exec(
            select(Solicitud)
            .where(Solicitud.taller_id == taller.id)
            .where(Solicitud.tenant_id == taller.tenant_id)
            .offset(skip)
            .limit(limit)
        ).all()
    else:
        solicitudes = session.exec(
            select(Solicitud)
            .join(Vehiculo)
            .where(Vehiculo.propietario_id == current_user.id)
            .order_by(Solicitud.fecha_creacion.desc())
            .offset(skip)
            .limit(limit)
        ).all()

    return [build_solicitud_read(session, solicitud) for solicitud in solicitudes]

@router.get("/taller/pendientes", response_model=List[SolicitudRead])
def listar_solicitudes_pendientes_taller(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.WORKSHOP:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los talleres pueden consultar solicitudes pendientes.",
        )

    taller = _obtener_taller_actual(session, current_user)

    candidato_rows = session.exec(
        select(SolicitudCandidato)
        .where(SolicitudCandidato.taller_id == taller.id)
        .where(SolicitudCandidato.estado.in_([EstadoCandidato.NOTIFICADO, EstadoCandidato.PENDIENTE]))
        .order_by(SolicitudCandidato.fecha_creacion.desc())
    ).all()

    solicitud_ids = list(dict.fromkeys(item.solicitud_id for item in candidato_rows))
    if not solicitud_ids:
        return []

    solicitudes = session.exec(
        select(Solicitud)
        .where(Solicitud.id.in_(solicitud_ids))
        .where(or_(Solicitud.taller_id.is_(None), Solicitud.taller_id == taller.id))
        .where(Solicitud.estado.in_(list(ESTADOS_PENDIENTES_TALLER)))
        .order_by(Solicitud.fecha_creacion.desc())
    ).all()

    solicitudes_candidatas = [
        solicitud
        for solicitud in solicitudes
        if taller_es_candidato_para_solicitud(session, taller, solicitud)
    ]

    solicitudes_paginadas = solicitudes_candidatas[skip:skip + limit]
    return [build_solicitud_read(session, solicitud) for solicitud in solicitudes_paginadas]


@router.get("/taller/mis-solicitudes", response_model=List[SolicitudRead])
def listar_mis_solicitudes_taller(    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ADMIN:
        statement = select(Solicitud).offset(skip).limit(limit)
        if current_user.tenant_id is not None:
            statement = statement.where(Solicitud.tenant_id == current_user.tenant_id)
        solicitudes = session.exec(statement).all()
        return [build_solicitud_read(session, solicitud) for solicitud in solicitudes]

    taller = obtener_taller_del_usuario(session, current_user)
    if not taller:
        return []

    solicitudes = session.exec(
        select(Solicitud)
        .where(Solicitud.taller_id == taller.id)
        .where(Solicitud.tenant_id == taller.tenant_id)
        .offset(skip)
        .limit(limit)
    ).all()
    return [build_solicitud_read(session, solicitud) for solicitud in solicitudes]


@router.get("/mis-reportes", response_model=List[SolicitudRead])
def listar_reportes_cliente(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.WORKSHOP:
        taller = _obtener_taller_actual(session, current_user)
        solicitudes = session.exec(
            select(Solicitud)
            .where(Solicitud.taller_id == taller.id)
            .where(Solicitud.tenant_id == taller.tenant_id)
            .order_by(Solicitud.fecha_creacion.desc())
            .offset(skip)
            .limit(limit)
        ).all()
        return [build_solicitud_read(session, solicitud) for solicitud in solicitudes]

    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el cliente puede consultar sus reportes.",
        )

    solicitudes = session.exec(
        select(Solicitud)
        .join(Vehiculo)
        .where(Vehiculo.propietario_id == current_user.id)
        .order_by(Solicitud.fecha_creacion.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return [build_solicitud_read(session, solicitud) for solicitud in solicitudes]


@router.get("/mis-asignaciones", response_model=List[SolicitudRead])
def listar_mis_asignaciones(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.TECNICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios tecnicos pueden consultar sus asignaciones.",
        )

    tecnico = _obtener_tecnico_actual(session, current_user)

    solicitudes = session.exec(
        select(Solicitud)
        .where(Solicitud.tecnico_id == tecnico.id)
        .where(Solicitud.tenant_id == tecnico.tenant_id)
        .order_by(Solicitud.fecha_creacion.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return [build_solicitud_read(session, solicitud) for solicitud in solicitudes]


@router.patch("/mis-asignaciones/{solicitud_id}/estado", response_model=SolicitudRead)
def actualizar_mi_asignacion_estado(
    *,
    solicitud_id: int,
    estado: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.TECNICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios tecnicos pueden actualizar sus asignaciones.",
        )

    tecnico = _obtener_tecnico_actual(session, current_user)
    solicitud = session.get(Solicitud, solicitud_id)

    if not solicitud or solicitud.tecnico_id != tecnico.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La asignacion no existe o no pertenece a este tecnico.",
        )

    nuevo_estado = normalizar_estado_operativo(estado)

    if nuevo_estado not in {
        EstadoSolicitud.TECNICO_EN_CAMINO,
        EstadoSolicitud.TECNICO_LLEGO,
        EstadoSolicitud.EN_PROCESO,
        EstadoSolicitud.FINALIZADO,
        EstadoSolicitud.CANCELADO,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El mecanico solo puede marcar la asignacion como tecnico_en_camino, tecnico_llego, en_proceso, finalizado o cancelado.",
        )

    estado_anterior = solicitud.estado
    solicitud.estado = nuevo_estado

    if nuevo_estado in {EstadoSolicitud.FINALIZADO, EstadoSolicitud.CANCELADO}:
        tecnico.disponible = True
        session.add(tecnico)

    if nuevo_estado == EstadoSolicitud.TECNICO_EN_CAMINO:
        tecnico.disponible = False
        solicitud.tiempo_estimado_minutos = estimate_eta_minutes(solicitud, tecnico, None)
        session.add(tecnico)
        notificar_tecnico_en_camino_conductor(session, solicitud, tecnico)
        notificar_tecnico_en_camino_taller(session, solicitud, tecnico)
    elif nuevo_estado == EstadoSolicitud.TECNICO_LLEGO:
        tecnico.disponible = False
        solicitud.tiempo_estimado_minutos = 0
        solicitud.fecha_tecnico_llego = datetime.utcnow()  # KPI: tiempo de llegada
        session.add(tecnico)
        notificar_llegada_mecanico(session, solicitud, tecnico)
    elif nuevo_estado == EstadoSolicitud.EN_PROCESO:
        tecnico.disponible = False
        solicitud.tiempo_estimado_minutos = 0
        session.add(tecnico)
    elif nuevo_estado == EstadoSolicitud.FINALIZADO:
        solicitud.fecha_finalizado = datetime.utcnow()  # KPI: cumplimiento SLA
        if not solicitud.precio_cobrado or not solicitud.comision_plataforma:
            solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(
                solicitud.clasificacion_ia,
                solicitud.prioridad_ia,
            )
        registrar_historial_vehiculo_desde_solicitud(
            session,
            solicitud,
            tecnico=tecnico,
            observaciones="Ficha creada automaticamente al finalizar la atencion.",
        )
        notificar_servicio_terminado(session, solicitud, tecnico)
    elif nuevo_estado == EstadoSolicitud.CANCELADO:
        notificar_cancelacion_mecanico_a_taller_y_conductor(session, solicitud, tecnico)

    session.add(solicitud)
    registrar_historial_solicitud(
        session,
        solicitud_id=solicitud.id or 0,
        estado_anterior=estado_anterior.value if isinstance(estado_anterior, EstadoSolicitud) else str(estado_anterior),
        estado_nuevo=nuevo_estado.value,
        actor=current_user,
        comentario="Estado actualizado desde el panel del tecnico.",
    )
    session.commit()
    session.refresh(solicitud)
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.patch("/{solicitud_id}/aceptar", response_model=SolicitudRead)
def aceptar_solicitud_taller(
    *,
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.WORKSHOP:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los talleres pueden aceptar solicitudes.",
        )

    taller = _obtener_taller_actual(session, current_user)
    solicitud = session.get(Solicitud, solicitud_id)

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.taller_id is not None and solicitud.taller_id != taller.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La solicitud ya fue tomada por otro taller.",
        )

    if solicitud.estado not in ESTADOS_PENDIENTES_TALLER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden aceptar solicitudes pendientes o en busqueda de taller.",
        )

    if not taller_es_candidato_para_solicitud(session, taller, solicitud):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu taller no es candidato para esta solicitud.",
        )

    solicitud.taller_id = taller.id
    solicitud.tenant_id = taller.tenant_id
    solicitud.estado = EstadoSolicitud.ASIGNADA
    solicitud.tiempo_estimado_minutos = estimate_eta_minutes(solicitud, None, taller)
    # KPI: timestamp del momento exacto en que el taller aceptó. Sirve para
    # calcular `tiempo_promedio_asignacion` y `sla_cumplimiento` desde DB.
    solicitud.fecha_taller_asignado = datetime.utcnow()
    marcar_candidato(session, solicitud, taller.id or 0, EstadoCandidato.ACEPTADO, "Aceptado por el taller.")
    registrar_historial_solicitud(
        session,
        solicitud_id=solicitud.id or 0,
        estado_anterior=EstadoSolicitud.BUSCANDO_TALLER.value,
        estado_nuevo=EstadoSolicitud.ASIGNADA.value,
        actor=current_user,
        comentario=f"Taller {taller.nombre_comercial} acepto la solicitud.",
    )
    session.add(solicitud)
    notificar_solicitud_aceptada_conductor(session, solicitud, taller)
    session.commit()
    session.refresh(solicitud)
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.patch("/{solicitud_id}/asignar-tecnico", response_model=SolicitudRead)
def asignar_tecnico_solicitud(
    *,
    solicitud_id: int,
    tecnico_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.WORKSHOP:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los talleres pueden asignar tecnicos.",
        )

    taller = _obtener_taller_actual(session, current_user)
    solicitud = session.get(Solicitud, solicitud_id)

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if solicitud.tenant_id != taller.tenant_id:
        raise HTTPException(status_code=403, detail="Solicitud fuera de tu tenant.")

    if solicitud.taller_id != taller.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes aceptar la solicitud antes de asignar un tecnico.",
        )

    nuevo_tecnico = session.get(Tecnico, tecnico_id)
    if not nuevo_tecnico or nuevo_tecnico.taller_id != taller.id or nuevo_tecnico.tenant_id != taller.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El técnico no pertenece a tu taller",
        )

    tecnico_actual = session.get(Tecnico, solicitud.tecnico_id) if solicitud.tecnico_id else None
    if tecnico_actual and tecnico_actual.id != nuevo_tecnico.id:
        tecnico_actual.disponible = True
        session.add(tecnico_actual)

    solicitud.tecnico_id = nuevo_tecnico.id
    solicitud.estado = EstadoSolicitud.ASIGNADA
    solicitud.tiempo_estimado_minutos = estimate_eta_minutes(solicitud, nuevo_tecnico, taller)
    nuevo_tecnico.disponible = False
    session.add(nuevo_tecnico)
    session.add(solicitud)
    registrar_historial_solicitud(
        session,
        solicitud_id=solicitud.id or 0,
        estado_anterior=EstadoSolicitud.ASIGNADA.value,
        estado_nuevo=EstadoSolicitud.ASIGNADA.value,
        actor=current_user,
        comentario=f"Tecnico {nuevo_tecnico.nombre} asignado.",
    )
    notificar_tecnico_asignado(session, solicitud, nuevo_tecnico)
    session.commit()
    session.refresh(solicitud)
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.patch("/{solicitud_id}/rechazar", response_model=SolicitudRead)
def rechazar_solicitud_taller(
    *,
    solicitud_id: int,
    motivo: str = "Rechazada por el taller.",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.WORKSHOP:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los talleres pueden rechazar solicitudes.",
        )

    taller = _obtener_taller_actual(session, current_user)
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.taller_id and solicitud.taller_id != taller.id:
        raise HTTPException(status_code=403, detail="No puedes rechazar una solicitud de otro taller.")

    marcar_candidato(session, solicitud, taller.id or 0, EstadoCandidato.RECHAZADO, motivo)
    if solicitud.taller_id == taller.id:
        solicitud.taller_id = None
        solicitud.tecnico_id = None
    solicitud.estado = EstadoSolicitud.BUSCANDO_TALLER

    proximo = siguiente_candidato(session, solicitud)
    if proximo:
        proximo.estado = EstadoCandidato.NOTIFICADO
        solicitud.tiempo_estimado_minutos = proximo.eta_minutos
        solicitud.distancia_estimada_km = proximo.distancia_km
        solicitud.asignacion_score = proximo.score
        session.add(proximo)
    else:
        # Si se agotan los candidatos, se regenera el ranking con el estado actual de capacidad.
        generar_candidatos(session, solicitud)

    registrar_historial_solicitud(
        session,
        solicitud_id=solicitud.id or 0,
        estado_anterior=EstadoSolicitud.ASIGNADA.value,
        estado_nuevo=EstadoSolicitud.BUSCANDO_TALLER.value,
        actor=current_user,
        comentario=motivo,
    )
    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.get("/{solicitud_id}/candidatos", response_model=list[SolicitudCandidatoRead])
def listar_candidatos_solicitud(
    *,
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    ensure_request_visible_to_user(session, solicitud, current_user)
    if current_user.role not in {UserRole.ADMIN, UserRole.WORKSHOP}:
        raise HTTPException(status_code=403, detail="Solo talleres o administradores pueden ver candidatos.")

    if current_user.role == UserRole.WORKSHOP:
        taller = _obtener_taller_actual(session, current_user)
        candidatos = session.exec(
            select(SolicitudCandidato)
            .where(SolicitudCandidato.solicitud_id == solicitud_id)
            .where(SolicitudCandidato.taller_id == taller.id)
            .order_by(SolicitudCandidato.posicion)
        ).all()
    else:
        statement = (
            select(SolicitudCandidato)
            .where(SolicitudCandidato.solicitud_id == solicitud_id)
            .order_by(SolicitudCandidato.posicion)
        )
        candidatos = session.exec(statement).all()

    return [SolicitudCandidatoRead.model_validate(item) for item in candidatos]


@router.get("/{solicitud_id}/historial", response_model=list[SolicitudHistorialRead])
def listar_historial_solicitud(
    *,
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    ensure_request_visible_to_user(session, solicitud, current_user)
    historial = session.exec(
        select(SolicitudHistorial)
        .where(SolicitudHistorial.solicitud_id == solicitud_id)
        .where(SolicitudHistorial.tenant_id == solicitud.tenant_id)
        .order_by(SolicitudHistorial.fecha_creacion)
    ).all()
    return [SolicitudHistorialRead.model_validate(item) for item in historial]


@router.get("/{solicitud_id}/chat", response_model=list[ChatMensajeRead])
def listar_chat_solicitud(
    *,
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    ensure_request_visible_to_user(session, solicitud, current_user)
    mensajes = session.exec(
        select(ChatMensaje)
        .where(ChatMensaje.solicitud_id == solicitud_id)
        .where(ChatMensaje.tenant_id == solicitud.tenant_id)
        .order_by(ChatMensaje.fecha_creacion)
    ).all()
    return [ChatMensajeRead.model_validate(item) for item in mensajes]


@router.post("/{solicitud_id}/chat", response_model=ChatMensajeRead)
def enviar_chat_solicitud(
    *,
    solicitud_id: int,
    payload: ChatMensajeCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    ensure_request_visible_to_user(session, solicitud, current_user)
    mensaje_texto = payload.mensaje.strip()
    if not mensaje_texto:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacio.")

    mensaje = ChatMensaje(
        solicitud_id=solicitud_id,
        remitente_id=current_user.id or 0,
        tenant_id=solicitud.tenant_id,
        mensaje=mensaje_texto,
    )
    session.add(mensaje)
    registrar_auditoria(
        session,
        actor=current_user,
        accion="mensaje_chat",
        entidad="solicitud",
        entidad_id=solicitud_id,
        detalle="Mensaje enviado en chat operativo.",
    )
    session.commit()
    session.refresh(mensaje)
    data = ChatMensajeRead.model_validate(mensaje)
    emitir_solicitud_update(solicitud_id, {"chat": data.model_dump()})
    return data


@router.post("/{solicitud_id}/calificacion", response_model=CalificacionRead)
def calificar_servicio(
    *,
    solicitud_id: int,
    payload: CalificacionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Solo el cliente puede calificar el servicio.")
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    ensure_request_visible_to_user(session, solicitud, current_user)
    if solicitud.estado not in {EstadoSolicitud.RESUELTA, EstadoSolicitud.FINALIZADO}:
        raise HTTPException(status_code=400, detail="Solo puedes calificar servicios finalizados.")
    if payload.puntaje < 1 or payload.puntaje > 5:
        raise HTTPException(status_code=400, detail="El puntaje debe estar entre 1 y 5.")

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller:
            existentes = session.exec(
                select(CalificacionServicio).where(CalificacionServicio.taller_id == taller.id)
                .where(CalificacionServicio.tenant_id == taller.tenant_id)
            ).all()
            total = sum(item.puntaje for item in existentes) + payload.puntaje
            taller.calificacion_promedio = round(total / (len(existentes) + 1), 2)
            session.add(taller)
    calificacion = CalificacionServicio(
        solicitud_id=solicitud_id,
        taller_id=solicitud.taller_id,
        cliente_id=current_user.id or 0,
        tenant_id=solicitud.tenant_id,
        puntaje=payload.puntaje,
        comentario=payload.comentario,
    )
    session.add(calificacion)
    registrar_auditoria(
        session,
        actor=current_user,
        accion="calificacion_servicio",
        entidad="solicitud",
        entidad_id=solicitud_id,
        detalle=f"Puntaje {payload.puntaje}",
    )
    session.commit()
    session.refresh(calificacion)
    return CalificacionRead.model_validate(calificacion)

@router.get("/{solicitud_id}", response_model=SolicitudRead)
def obtener_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_id: int,
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    ensure_request_visible_to_user(session, solicitud, current_user)
    return build_solicitud_read(session, solicitud)


@router.post("/{solicitud_id}/audio", response_model=SolicitudRead)
async def subir_audio_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_id: int,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    ensure_request_visible_to_user(session, solicitud, current_user)
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Solo el cliente puede adjuntar audio a su reporte")

    relative_url = await save_upload_file(
        upload=audio,
        category="request-audio",
        prefix=f"solicitud-{solicitud_id}-audio",
    )
    local_path = url_to_path(relative_url)
    summary = summarize_audio_file(
        audio_path=str(local_path) if local_path else "",
        descripcion=solicitud.descripcion,
    )

    evidencia = Evidencia(
        solicitud_id=solicitud.id,
        tipo_evidencia=TipoEvidencia.AUDIO,
        ruta_archivo=relative_url,
    )
    base_summary = (solicitud.resumen_ia or "").split("Resumen del audio:", 1)[0].strip()
    solicitud.resumen_ia = f"{base_summary}\nResumen del audio: {summary}".strip()

    session.add(evidencia)
    session.add(solicitud)
    session.flush()
    reanalizar_solicitud_con_evidencias(session, solicitud)
    notificar_reporte_actualizado(session, solicitud, "audio descriptivo y resumen IA")
    session.commit()
    session.refresh(solicitud)
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.post("/{solicitud_id}/imagenes", response_model=SolicitudRead)
async def subir_imagenes_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_id: int,
    fotos: list[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    ensure_request_visible_to_user(session, solicitud, current_user)
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Solo el cliente puede adjuntar fotos a su reporte")
    if not fotos:
        raise HTTPException(status_code=400, detail="Debes enviar al menos una foto")

    for index, foto in enumerate(fotos[:6], start=1):
        relative_url = await save_upload_file(
            upload=foto,
            category="request-images",
            prefix=f"solicitud-{solicitud_id}-foto-{index}",
        )
        evidencia = Evidencia(
            solicitud_id=solicitud.id,
            tipo_evidencia=TipoEvidencia.IMAGEN,
            ruta_archivo=relative_url,
        )
        session.add(evidencia)

    session.flush()
    reanalizar_solicitud_con_evidencias(session, solicitud)
    notificar_reporte_actualizado(session, solicitud, "fotografias del incidente")
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)


@router.patch("/{solicitud_id}/estado", response_model=SolicitudRead)
def actualizar_estado_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_id: int,
    estado: str,
    tecnico_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    nuevo_estado = normalizar_estado_operativo(estado)

    taller = obtener_taller_del_usuario(session, current_user)
    if current_user.role != UserRole.ADMIN:
        if not taller:
            raise HTTPException(status_code=400, detail="Debes tener un taller registrado para modificar solicitudes")
        if solicitud.taller_id is not None and solicitud.taller_id != taller.id:
            raise HTTPException(status_code=403, detail="No tienes permisos para modificar esta solicitud")

    estado_anterior = solicitud.estado
    was_resolved = solicitud.estado in {EstadoSolicitud.RESUELTA, EstadoSolicitud.FINALIZADO}
    assigned_tecnico: Optional[Tecnico] = None

    if tecnico_id:
        assigned_tecnico = session.get(Tecnico, tecnico_id)
        if not assigned_tecnico:
            raise HTTPException(status_code=404, detail="Tecnico no encontrado")

        if current_user.role != UserRole.ADMIN and (not taller or assigned_tecnico.taller_id != taller.id):
            raise HTTPException(status_code=400, detail="El tecnico no pertenece a tu taller")

        solicitud.tecnico_id = tecnico_id
        solicitud.taller_id = assigned_tecnico.taller_id
        assigned_tecnico.disponible = nuevo_estado in {
            EstadoSolicitud.RESUELTA,
            EstadoSolicitud.CANCELADA,
            EstadoSolicitud.FINALIZADO,
            EstadoSolicitud.CANCELADO,
        }
        session.add(assigned_tecnico)
    elif solicitud.tecnico_id:
        assigned_tecnico = session.get(Tecnico, solicitud.tecnico_id)

    if nuevo_estado in {
        EstadoSolicitud.RESUELTA,
        EstadoSolicitud.CANCELADA,
        EstadoSolicitud.FINALIZADO,
        EstadoSolicitud.CANCELADO,
    } and solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico.disponible = True
            session.add(tecnico)

    if nuevo_estado == EstadoSolicitud.ASIGNADA:
        reference_taller = session.get(Taller, solicitud.taller_id) if solicitud.taller_id else taller
        solicitud.tiempo_estimado_minutos = estimate_eta_minutes(solicitud, assigned_tecnico, reference_taller)
    elif nuevo_estado in {EstadoSolicitud.EN_PROGRESO, EstadoSolicitud.TECNICO_EN_CAMINO}:
        solicitud.tiempo_estimado_minutos = max(5, int((solicitud.tiempo_estimado_minutos or 20) * 0.55))
    elif nuevo_estado in {EstadoSolicitud.LLEGADA, EstadoSolicitud.TECNICO_LLEGO, EstadoSolicitud.EN_PROCESO}:
        solicitud.tiempo_estimado_minutos = 0
    elif nuevo_estado in {
        EstadoSolicitud.RESUELTA,
        EstadoSolicitud.CANCELADA,
        EstadoSolicitud.FINALIZADO,
        EstadoSolicitud.CANCELADO,
    }:
        solicitud.tiempo_estimado_minutos = 0

    if not solicitud.precio_cobrado or not solicitud.comision_plataforma:
        solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(
            solicitud.clasificacion_ia,
            solicitud.prioridad_ia,
        )

    if nuevo_estado != estado_anterior:
        if nuevo_estado == EstadoSolicitud.ASIGNADA:
            if assigned_tecnico:
                notificar_tecnico_asignado(session, solicitud, assigned_tecnico)
            reference_taller = session.get(Taller, solicitud.taller_id) if solicitud.taller_id else taller
            if reference_taller:
                notificar_solicitud_aceptada_conductor(session, solicitud, reference_taller)
        elif nuevo_estado in {EstadoSolicitud.EN_PROGRESO, EstadoSolicitud.TECNICO_EN_CAMINO} and assigned_tecnico:
            notificar_tecnico_en_camino_conductor(session, solicitud, assigned_tecnico)
            notificar_tecnico_en_camino_taller(session, solicitud, assigned_tecnico)
        elif nuevo_estado in {EstadoSolicitud.LLEGADA, EstadoSolicitud.TECNICO_LLEGO} and assigned_tecnico:
            notificar_llegada_mecanico(session, solicitud, assigned_tecnico)
        elif nuevo_estado in {EstadoSolicitud.RESUELTA, EstadoSolicitud.FINALIZADO}:
            solicitud.fecha_finalizado = solicitud.fecha_finalizado or datetime.utcnow()
            registrar_historial_vehiculo_desde_solicitud(
                session,
                solicitud,
                tecnico=assigned_tecnico,
                observaciones="Ficha creada automaticamente al cerrar el servicio.",
            )
            notificar_servicio_terminado(session, solicitud, assigned_tecnico)
        elif nuevo_estado in {EstadoSolicitud.CANCELADA, EstadoSolicitud.CANCELADO}:
            if current_user.role == UserRole.WORKSHOP and taller:
                notificar_cancelacion_taller_a_conductor(session, solicitud, taller)
                notificar_cancelacion_a_mecanico(session, solicitud)
            else:
                notificar_cancelacion_a_mecanico(session, solicitud)

    solicitud.estado = nuevo_estado
    session.add(solicitud)
    if nuevo_estado != estado_anterior:
        registrar_historial_solicitud(
            session,
            solicitud_id=solicitud.id or 0,
            estado_anterior=estado_anterior.value if isinstance(estado_anterior, EstadoSolicitud) else str(estado_anterior),
            estado_nuevo=nuevo_estado.value,
            actor=current_user,
            comentario="Estado actualizado desde API operativa.",
        )
    update_service_totals(session, solicitud, was_resolved)
    session.commit()
    session.refresh(solicitud)
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.patch("/{solicitud_id}/cancelar", response_model=SolicitudRead)
def cancelar_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_id: int,
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if estado_es_cerrado(solicitud.estado):
        raise HTTPException(status_code=400, detail="La solicitud ya esta cerrada")

    taller_cancelador: Optional[Taller] = None
    if current_user.role == UserRole.WORKSHOP:
        taller_cancelador = _obtener_taller_actual(session, current_user)
        if solicitud.taller_id != taller_cancelador.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes cancelar solicitudes tomadas por tu taller.",
            )
        notificar_cancelacion_taller_a_conductor(session, solicitud, taller_cancelador)
        notificar_cancelacion_a_mecanico(session, solicitud)
    elif current_user.role == UserRole.DRIVER:
        ensure_request_visible_to_user(session, solicitud, current_user)
        notificar_cancelacion_conductor_a_talleres(session, solicitud)
        notificar_cancelacion_a_mecanico(session, solicitud)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el conductor o el taller asignado pueden cancelar la solicitud.",
        )

    estado_anterior = solicitud.estado
    solicitud.estado = EstadoSolicitud.CANCELADO
    solicitud.tiempo_estimado_minutos = 0
    if solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico.disponible = True
            session.add(tecnico)

    session.add(solicitud)
    registrar_historial_solicitud(
        session,
        solicitud_id=solicitud.id or 0,
        estado_anterior=estado_anterior.value if isinstance(estado_anterior, EstadoSolicitud) else str(estado_anterior),
        estado_nuevo=EstadoSolicitud.CANCELADO.value,
        actor=current_user,
        comentario="Solicitud cancelada.",
    )
    session.commit()
    session.refresh(solicitud)
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.patch("/{solicitud_id}/costo", response_model=SolicitudRead)
def actualizar_costo_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_id: int,
    payload: CostoPayload,
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if current_user.role not in (UserRole.WORKSHOP, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Solo el taller puede definir el monto del servicio")
    if current_user.tenant_id is not None and solicitud.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Solicitud fuera de tu tenant")

    if current_user.role == UserRole.WORKSHOP:
        taller = _obtener_taller_actual(session, current_user)
        if solicitud.taller_id != taller.id or solicitud.tenant_id != taller.tenant_id:
            raise HTTPException(status_code=403, detail="Solo puedes cobrar servicios asignados a tu taller")

    if solicitud.estado in {EstadoSolicitud.CANCELADA, EstadoSolicitud.CANCELADO}:
        raise HTTPException(status_code=400, detail="No se puede cobrar una solicitud cancelada")
    if solicitud.estado_pago == "pagado":
        raise HTTPException(status_code=400, detail="No se puede modificar un servicio ya pagado")
    if solicitud.cotizacion_seleccionada_id:
        raise HTTPException(
            status_code=400,
            detail="El monto ya fue acordado en una cotizacion aceptada y no puede cambiarse.",
        )

    monto = round(float(payload.monto), 2)
    if monto <= 0:
        raise HTTPException(status_code=400, detail="Monto de pago invalido")

    solicitud.precio_cobrado = monto
    solicitud.comision_plataforma = round(monto * 0.10, 2)
    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    payload = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload.model_dump())
    emitir_talleres_update(session, solicitud, payload.model_dump())
    return payload


@router.post("/{solicitud_id}/pago", response_model=SolicitudRead)
def pagar_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_id: int,
    payload: PagoPayload,
    current_user: User = Depends(get_current_user),
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    ensure_request_visible_to_user(session, solicitud, current_user)
    if current_user.role == UserRole.WORKSHOP:
        raise HTTPException(status_code=403, detail="El taller no puede registrar el pago del cliente")

    if solicitud.estado in {EstadoSolicitud.CANCELADA, EstadoSolicitud.CANCELADO}:
        raise HTTPException(status_code=400, detail="No puedes pagar una solicitud cancelada")
    if solicitud.estado_pago == "pagado":
        raise HTTPException(status_code=400, detail="La solicitud ya fue pagada")

    if not solicitud.precio_cobrado or not solicitud.comision_plataforma:
        solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(
            solicitud.clasificacion_ia,
            solicitud.prioridad_ia,
        )

    monto = solicitud.precio_cobrado if solicitud.cotizacion_seleccionada_id else (
        payload.monto if payload.monto is not None else solicitud.precio_cobrado
    )
    if monto is None or monto <= 0:
        raise HTTPException(status_code=400, detail="Monto de pago invalido")

    solicitud.precio_cobrado = round(monto, 2)
    solicitud.comision_plataforma = round(solicitud.precio_cobrado * 0.10, 2)
    solicitud.estado_pago = "pagado"
    solicitud.fecha_pago = datetime.utcnow()
    session.add(
        Pago(
            solicitud_id=solicitud.id or 0,
            usuario_id=current_user.id or 0,
            tenant_id=solicitud.tenant_id,
            monto=solicitud.precio_cobrado,
            comision_plataforma=solicitud.comision_plataforma or 0,
            metodo=payload.metodo or "simulado",
            estado="pagado",
            referencia=f"SIM-{solicitud.id}-{int(solicitud.fecha_pago.timestamp())}",
        )
    )
    registrar_historial_vehiculo_desde_solicitud(
        session,
        solicitud,
        observaciones="Pago confirmado por el cliente; comprobante registrado en el historial.",
    )
    notificar_pago_confirmado_taller(session, solicitud)
    session.add(solicitud)
    registrar_auditoria(
        session,
        actor=current_user,
        accion="pago_simulado_registrado",
        entidad="solicitud",
        entidad_id=solicitud.id,
        detalle=f"Monto {solicitud.precio_cobrado}",
    )
    session.commit()
    session.refresh(solicitud)
    payload_read = build_solicitud_read(session, solicitud)
    emitir_solicitud_update(solicitud.id or 0, payload_read.model_dump())
    emitir_talleres_update(session, solicitud, payload_read.model_dump())
    return payload_read
