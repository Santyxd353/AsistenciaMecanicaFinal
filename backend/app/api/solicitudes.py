import math
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    EstadoSolicitud,
    Solicitud,
    SolicitudCreate,
    SolicitudRead,
    Taller,
    Tecnico,
    Vehiculo,
)
from app.models.user import User, UserRole

router = APIRouter()


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
    clasif, prio, resm = simular_procesamiento_ia(solicitud.descripcion)
    solicitud.clasificacion_ia = clasif
    solicitud.prioridad_ia = prio
    solicitud.resumen_ia = resm
    solicitud.estado_pago = "pendiente"
    solicitud.precio_cobrado, solicitud.comision_plataforma = estimate_pricing(clasif, prio)

    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if not vehiculo:
            raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
        if current_user.role == UserRole.DRIVER and vehiculo.propietario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No puedes reportar con un vehiculo de otro usuario")

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
