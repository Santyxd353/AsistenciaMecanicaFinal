from __future__ import annotations

import math
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel
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
    TipoEvidencia,
    Vehiculo,
)
from app.models.user import User, UserRole
from app.services.ai import analyze_incident
from app.services.storage import save_upload_file, url_to_path

router = APIRouter()


class PagoPayload(BaseModel):
    monto: Optional[float] = None
    metodo: Optional[str] = "tarjeta"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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

    clasificacion_eval = (clasificacion or "").lower()
    if "bateria" in clasificacion_eval or "electrico" in clasificacion_eval:
        base_amount = 150.0
    elif "llanta" in clasificacion_eval or "neumatic" in clasificacion_eval:
        base_amount = 110.0
    elif "motor" in clasificacion_eval or "recalent" in clasificacion_eval:
        base_amount = 220.0
    elif "cerrajer" in clasificacion_eval:
        base_amount = 140.0
    elif "choque" in clasificacion_eval or "colision" in clasificacion_eval:
        base_amount = 260.0

    if prioridad == "Alta":
        base_amount += 70.0
    elif prioridad == "Media":
        base_amount += 30.0

    platform_fee = round(base_amount * 0.10, 2)
    return round(base_amount, 2), platform_fee


def obtener_taller_del_usuario(session: Session, current_user: User) -> Taller | None:
    return session.exec(select(Taller).where(Taller.propietario_id == current_user.id)).first()


def request_vehicle(session: Session, solicitud: Solicitud) -> Optional[Vehiculo]:
    if not solicitud.vehiculo_id:
        return None
    return session.get(Vehiculo, solicitud.vehiculo_id)


def build_solicitud_read(session: Session, solicitud: Solicitud) -> SolicitudRead:
    data = SolicitudRead.model_validate(solicitud)
    taller_nombre = None
    tecnico_nombre = None
    tecnico_especialidad = None
    vehiculo_placa = None
    vehiculo_descripcion = None

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller:
            taller_nombre = taller.nombre_comercial

    if solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico_nombre = tecnico.nombre
            tecnico_especialidad = tecnico.especialidad

    vehiculo = request_vehicle(session, solicitud)
    if vehiculo:
        vehiculo_placa = vehiculo.placa
        vehiculo_descripcion = f"{vehiculo.marca} {vehiculo.modelo}".strip()

    return data.model_copy(
        update={
            "taller_nombre": taller_nombre,
            "tecnico_nombre": tecnico_nombre,
            "tecnico_especialidad": tecnico_especialidad,
            "vehiculo_placa": vehiculo_placa,
            "vehiculo_descripcion": vehiculo_descripcion,
        }
    )


def ensure_request_visible_to_user(session: Session, solicitud: Solicitud, current_user: User) -> None:
    if current_user.role == UserRole.ADMIN:
        return

    if current_user.role == UserRole.WORKSHOP:
        taller = obtener_taller_del_usuario(session, current_user)
        if not taller or solicitud.taller_id != taller.id:
            raise HTTPException(status_code=403, detail="No tienes permisos para ver esta solicitud")
        return

    vehiculo = request_vehicle(session, solicitud)
    if not vehiculo or vehiculo.propietario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver esta solicitud")


def _normalize_specialty(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _specialty_penalty(required_specialty: Optional[str], current_specialty: Optional[str]) -> float:
    required = _normalize_specialty(required_specialty)
    current = _normalize_specialty(current_specialty)
    if not required or required == "general":
        return 0.0
    return 0.0 if required in current else 18.0


def assign_best_technician(session: Session, solicitud: Solicitud) -> tuple[Optional[Tecnico], Optional[Taller]]:
    tecnicos = session.exec(select(Tecnico).where(Tecnico.disponible == True)).all()
    if not tecnicos:
        return None, None

    best_tecnico: Optional[Tecnico] = None
    best_score = float("inf")

    for tecnico in tecnicos:
        if tecnico.latitud is None or tecnico.longitud is None:
            distance = 35.0
        else:
            distance = haversine_km(solicitud.latitud, solicitud.longitud, tecnico.latitud, tecnico.longitud)

        score = distance + _specialty_penalty(solicitud.especialidad_requerida_ia, tecnico.especialidad)
        if score < best_score:
            best_score = score
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
    best_score = float("inf")

    for taller in talleres:
        if taller.latitud is None or taller.longitud is None:
            distance = 40.0
        else:
            distance = haversine_km(solicitud.latitud, solicitud.longitud, taller.latitud, taller.longitud)

        score = distance + _specialty_penalty(solicitud.especialidad_requerida_ia, taller.especialidades)
        if score < best_score:
            best_score = score
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


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, "", "null"):
        return None
    return int(value)


async def _read_creation_payload(
    request: Request,
) -> tuple[dict[str, Any], list[UploadFile], list[UploadFile], Optional[str], Optional[str]]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        images = [
            file
            for file in form.getlist("images")
            if isinstance(file, UploadFile) and file.filename
        ]
        audios = [
            file
            for file in form.getlist("audio")
            if isinstance(file, UploadFile) and file.filename
        ]
        payload = {
            "descripcion": str(form.get("descripcion", "")).strip(),
            "latitud": str(form.get("latitud", "")).strip(),
            "longitud": str(form.get("longitud", "")).strip(),
            "estado": str(form.get("estado", "pendiente")).strip() or "pendiente",
            "vehiculo_id": _optional_int(form.get("vehiculo_id")),
        }
        incident_type = str(form.get("incident_type", "")).strip() or None
        extra_notes = str(form.get("extra_notes", "")).strip() or None
        return payload, images, audios, incident_type, extra_notes

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="No se pudo leer el payload de la solicitud.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload invalido para solicitud.")
    incident_type = payload.get("incident_type")
    extra_notes = payload.get("extra_notes")
    return payload, [], [], incident_type, extra_notes


def _compose_ai_description(
    *,
    descripcion: str,
    incident_type: Optional[str],
    extra_notes: Optional[str],
    vehiculo: Optional[Vehiculo],
) -> str:
    parts = []
    if vehiculo:
        parts.append(f"Vehiculo: {vehiculo.placa} {vehiculo.marca} {vehiculo.modelo}")
        if vehiculo.color:
            parts.append(f"Color: {vehiculo.color}")
    if incident_type:
        parts.append(f"Tipo declarado: {incident_type}")
    parts.append(f"Descripcion: {descripcion}")
    if extra_notes:
        parts.append(f"Notas extra: {extra_notes}")
    return ". ".join(parts)


@router.post("/", response_model=SolicitudRead)
async def crear_solicitud(
    request: Request,
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    payload, image_uploads, audio_uploads, incident_type, extra_notes = await _read_creation_payload(request)
    solicitud_in = SolicitudCreate.model_validate(payload)
    solicitud = Solicitud.model_validate(solicitud_in)
    solicitud.estado_pago = "pendiente"

    vehiculo: Optional[Vehiculo] = None
    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
        if current_user.role == UserRole.DRIVER and vehiculo.propietario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No puedes reportar con un vehiculo de otro usuario")

    session.add(solicitud)
    session.flush()

    saved_image_paths: list[str] = []
    saved_audio_paths: list[str] = []

    for upload in image_uploads:
        relative_url = await save_upload_file(
            upload=upload,
            category="requests",
            prefix=f"solicitud-{solicitud.id}-imagen",
        )
        saved_image_paths.append(str(url_to_path(relative_url)))
        session.add(
            Evidencia(
                solicitud_id=solicitud.id,
                tipo_evidencia=TipoEvidencia.IMAGEN,
                ruta_archivo=relative_url,
            )
        )

    for upload in audio_uploads[:1]:
        relative_url = await save_upload_file(
            upload=upload,
            category="requests",
            prefix=f"solicitud-{solicitud.id}-audio",
        )
        saved_audio_paths.append(str(url_to_path(relative_url)))
        session.add(
            Evidencia(
                solicitud_id=solicitud.id,
                tipo_evidencia=TipoEvidencia.AUDIO,
                ruta_archivo=relative_url,
            )
        )

    vehicle_photo_path: Optional[str] = None
    if vehiculo and vehiculo.foto_url:
        local_photo = url_to_path(vehiculo.foto_url)
        if local_photo:
            vehicle_photo_path = str(local_photo)

    ai_input = _compose_ai_description(
        descripcion=solicitud.descripcion,
        incident_type=incident_type,
        extra_notes=extra_notes,
        vehiculo=vehiculo,
    )
    analysis = analyze_incident(
        descripcion=ai_input,
        incident_type=incident_type,
        image_paths=saved_image_paths,
        audio_paths=saved_audio_paths,
        vehicle_photo_path=vehicle_photo_path,
    )

    solicitud.clasificacion_ia = analysis.clasificacion
    solicitud.prioridad_ia = analysis.prioridad
    solicitud.resumen_ia = analysis.resumen
    solicitud.especialidad_requerida_ia = analysis.especialidad_requerida
    solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(
        analysis.clasificacion,
        analysis.prioridad,
    )

    tecnico, taller = assign_best_technician(session, solicitud)
    if tecnico:
        solicitud.estado = EstadoSolicitud.ASIGNADA
        solicitud.tecnico_id = tecnico.id
        solicitud.taller_id = tecnico.taller_id
        solicitud.tiempo_estimado_minutos = estimate_eta_minutes(solicitud, tecnico, taller)
        tecnico.disponible = False
        session.add(tecnico)
    else:
        solicitud.estado = EstadoSolicitud.PENDIENTE
        taller = assign_best_workshop(session, solicitud)
        if taller:
            solicitud.taller_id = taller.id
            solicitud.tiempo_estimado_minutos = estimate_eta_minutes(solicitud, None, taller)

    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
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


@router.get("/mis-solicitudes", response_model=List[SolicitudRead])
def listar_solicitudes_taller(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    solicitudes = session.exec(
        select(Solicitud)
        .join(Vehiculo)
        .where(Vehiculo.propietario_id == current_user.id)
        .offset(skip)
        .limit(limit)
    ).all()
    return [build_solicitud_read(session, solicitud) for solicitud in solicitudes]


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

    ensure_request_visible_to_user(session, solicitud, current_user)
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Solo el cliente puede cancelar su solicitud desde este flujo")

    if solicitud.estado in (EstadoSolicitud.RESUELTA, EstadoSolicitud.CANCELADA):
        raise HTTPException(status_code=400, detail="La solicitud ya esta cerrada")

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
