import math
import unicodedata
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    EstadoSolicitud,
    Evidencia,
    Solicitud,
    SolicitudCreate,
    SolicitudRead,
    Taller,
    Tecnico,
    TipoNotificacion,
    TipoEvidencia,
    Vehiculo,
)
from app.models.user import User, UserRole
from app.services.ai import analyze_incident, summarize_audio_file
from app.services.notificaciones import crear_notificacion, crear_notificaciones_para_usuarios
from app.services.storage import save_upload_file, url_to_path

router = APIRouter()

RADIO_TALLERES_CANDIDATOS_KM = 25.0
MAX_TALLERES_CANDIDATOS = 12


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
        return False

    return any(
        palabra_clave in especialidad
        for especialidad in especialidades
        for palabra_clave in palabras_clave
    )


def obtener_talleres_candidatos_para_notificar(
    session: Session,
    solicitud: Solicitud,
) -> list[Taller]:
    talleres = session.exec(select(Taller)).all()
    candidatos: list[tuple[float, Taller]] = []

    for taller in talleres:
        if not taller_es_compatible_con_solicitud(taller, solicitud):
            continue

        distancia = distancia_taller_solicitud(solicitud, taller)
        if distancia > RADIO_TALLERES_CANDIDATOS_KM:
            continue

        candidatos.append((distancia, taller))

    candidatos.sort(key=lambda item: item[0])
    return [taller for _, taller in candidatos[:MAX_TALLERES_CANDIDATOS]]


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


def build_solicitud_read(session: Session, solicitud: Solicitud) -> SolicitudRead:
    data = SolicitudRead.model_validate(solicitud)
    taller_nombre = None
    taller_latitud = None
    taller_longitud = None
    tecnico_nombre = None
    tecnico_especialidad = None
    tecnico_latitud = None
    tecnico_longitud = None
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
            tecnico_latitud = tecnico.latitud
            tecnico_longitud = tecnico.longitud
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
            "vehiculo_placa": vehiculo_placa,
            "vehiculo_descripcion": vehiculo_descripcion,
            "audio_url": audio_url,
            "audio_resumen_ia": audio_resumen_ia,
            "ruta_recomendada_ia": ruta_recomendada_ia,
        }
    )


def ensure_request_visible_to_user(session: Session, solicitud: Solicitud, current_user: User) -> None:
    if current_user.role == UserRole.ADMIN:
        return

    if current_user.role == UserRole.WORKSHOP:
        taller = obtener_taller_del_usuario(session, current_user)
        solicitud_asignada_al_taller = taller and solicitud.taller_id == taller.id
        solicitud_pendiente_candidata = (
            taller
            and solicitud.taller_id is None
            and solicitud.estado == EstadoSolicitud.PENDIENTE
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
    tecnicos = session.exec(select(Tecnico).where(Tecnico.disponible == True)).all()
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
    talleres = session.exec(select(Taller)).all()
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
    if was_resolved or solicitud.estado != EstadoSolicitud.RESUELTA or not solicitud.taller_id:
        return

    taller = session.get(Taller, solicitud.taller_id)
    if not taller:
        return

    taller.total_servicios_completados += 1
    session.add(taller)


@router.post("/", response_model=SolicitudRead)
def crear_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_in: SolicitudCreate,
    current_user: User = Depends(get_current_user),
):
    solicitud = Solicitud.model_validate(solicitud_in)
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
    solicitud.tiempo_estimado_minutos = None

    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    notificar_talleres_candidatos(session, solicitud)
    session.commit()
    return build_solicitud_read(session, solicitud)


@router.get("/", response_model=List[SolicitudRead])
def listar_solicitudes(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(Solicitud).offset(skip).limit(limit)

    if current_user.role == UserRole.ADMIN:
        solicitudes = session.exec(statement).all()
    elif current_user.role == UserRole.WORKSHOP:
        taller = obtener_taller_del_usuario(session, current_user)
        if not taller:
            return []
        solicitudes = session.exec(
            select(Solicitud)
            .where(Solicitud.taller_id == taller.id)
            .offset(skip)
            .limit(limit)
        ).all()
    else:
        solicitudes = session.exec(
            select(Solicitud)
            .join(Vehiculo)
            .where(Vehiculo.propietario_id == current_user.id)
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

    solicitudes = session.exec(
        select(Solicitud)
        .where(or_(Solicitud.taller_id.is_(None), Solicitud.taller_id == taller.id))
        .where(Solicitud.estado == EstadoSolicitud.PENDIENTE)
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
        solicitudes = session.exec(select(Solicitud).offset(skip).limit(limit)).all()
        return [build_solicitud_read(session, solicitud) for solicitud in solicitudes]

    taller = obtener_taller_del_usuario(session, current_user)
    if not taller:
        return []

    solicitudes = session.exec(
        select(Solicitud).where(Solicitud.taller_id == taller.id).offset(skip).limit(limit)
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

    try:
        nuevo_estado = EstadoSolicitud(estado)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Estados válidos: {[e.value for e in EstadoSolicitud]}",
        )

    if nuevo_estado not in {
        EstadoSolicitud.EN_PROGRESO,
        EstadoSolicitud.RESUELTA,
        EstadoSolicitud.CANCELADA,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tecnico solo puede marcar la asignacion como en progreso, resuelta o cancelada.",
        )

    solicitud.estado = nuevo_estado

    if nuevo_estado in {EstadoSolicitud.RESUELTA, EstadoSolicitud.CANCELADA}:
        tecnico.disponible = True
        session.add(tecnico)

    if nuevo_estado == EstadoSolicitud.EN_PROGRESO:
        tecnico.disponible = False
        session.add(tecnico)
        notificar_tecnico_en_camino_conductor(session, solicitud, tecnico)

    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)


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

    if solicitud.estado != EstadoSolicitud.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden aceptar solicitudes pendientes.",
        )

    if not taller_es_candidato_para_solicitud(session, taller, solicitud):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu taller no es candidato para esta solicitud.",
        )

    solicitud.taller_id = taller.id
    solicitud.tiempo_estimado_minutos = estimate_eta_minutes(solicitud, None, taller)
    session.add(solicitud)
    notificar_solicitud_aceptada_conductor(session, solicitud, taller)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)


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

    if solicitud.taller_id != taller.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes aceptar la solicitud antes de asignar un tecnico.",
        )

    nuevo_tecnico = session.get(Tecnico, tecnico_id)
    if not nuevo_tecnico or nuevo_tecnico.taller_id != taller.id:
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
    nuevo_tecnico.disponible = False
    session.add(nuevo_tecnico)
    session.add(solicitud)
    notificar_tecnico_asignado(session, solicitud, nuevo_tecnico)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)

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

    try:
        nuevo_estado = EstadoSolicitud(estado)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Estado invalido. Estados validos: {[item.value for item in EstadoSolicitud]}",
        )

    taller = obtener_taller_del_usuario(session, current_user)
    if current_user.role != UserRole.ADMIN:
        if not taller:
            raise HTTPException(status_code=400, detail="Debes tener un taller registrado para modificar solicitudes")
        if solicitud.taller_id is not None and solicitud.taller_id != taller.id:
            raise HTTPException(status_code=403, detail="No tienes permisos para modificar esta solicitud")

    was_resolved = solicitud.estado == EstadoSolicitud.RESUELTA
    assigned_tecnico: Optional[Tecnico] = None

    if tecnico_id:
        assigned_tecnico = session.get(Tecnico, tecnico_id)
        if not assigned_tecnico:
            raise HTTPException(status_code=404, detail="Tecnico no encontrado")

        if current_user.role != UserRole.ADMIN and (not taller or assigned_tecnico.taller_id != taller.id):
            raise HTTPException(status_code=400, detail="El tecnico no pertenece a tu taller")

        solicitud.tecnico_id = tecnico_id
        solicitud.taller_id = assigned_tecnico.taller_id
        assigned_tecnico.disponible = nuevo_estado in (EstadoSolicitud.RESUELTA, EstadoSolicitud.CANCELADA)
        session.add(assigned_tecnico)
    elif solicitud.tecnico_id:
        assigned_tecnico = session.get(Tecnico, solicitud.tecnico_id)

    if nuevo_estado in (EstadoSolicitud.RESUELTA, EstadoSolicitud.CANCELADA) and solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico.disponible = True
            session.add(tecnico)

    if nuevo_estado == EstadoSolicitud.ASIGNADA:
        reference_taller = session.get(Taller, solicitud.taller_id) if solicitud.taller_id else taller
        solicitud.tiempo_estimado_minutos = estimate_eta_minutes(solicitud, assigned_tecnico, reference_taller)
    elif nuevo_estado == EstadoSolicitud.EN_PROGRESO:
        solicitud.tiempo_estimado_minutos = max(5, int((solicitud.tiempo_estimado_minutos or 20) * 0.55))
    elif nuevo_estado in (EstadoSolicitud.RESUELTA, EstadoSolicitud.CANCELADA):
        solicitud.tiempo_estimado_minutos = 0

    if not solicitud.precio_cobrado or not solicitud.comision_plataforma:
        solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(
            solicitud.clasificacion_ia,
            solicitud.prioridad_ia,
        )

    solicitud.estado = nuevo_estado
    session.add(solicitud)
    update_service_totals(session, solicitud, was_resolved)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)


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

    if solicitud.estado in (EstadoSolicitud.RESUELTA, EstadoSolicitud.CANCELADA):
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
    elif current_user.role == UserRole.DRIVER:
        ensure_request_visible_to_user(session, solicitud, current_user)
        notificar_cancelacion_conductor_a_talleres(session, solicitud)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el conductor o el taller asignado pueden cancelar la solicitud.",
        )

    solicitud.estado = EstadoSolicitud.CANCELADA
    solicitud.tiempo_estimado_minutos = 0
    if solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico.disponible = True
            session.add(tecnico)

    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)


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

    if solicitud.estado == EstadoSolicitud.CANCELADA:
        raise HTTPException(status_code=400, detail="No puedes pagar una solicitud cancelada")
    if solicitud.estado_pago == "pagado":
        raise HTTPException(status_code=400, detail="La solicitud ya fue pagada")

    if not solicitud.precio_cobrado or not solicitud.comision_plataforma:
        solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(
            solicitud.clasificacion_ia,
            solicitud.prioridad_ia,
        )

    monto = payload.monto if payload.monto is not None else solicitud.precio_cobrado
    if monto is None or monto <= 0:
        raise HTTPException(status_code=400, detail="Monto de pago invalido")

    solicitud.precio_cobrado = round(monto, 2)
    solicitud.estado_pago = "pagado"
    solicitud.fecha_pago = datetime.utcnow()
    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)
