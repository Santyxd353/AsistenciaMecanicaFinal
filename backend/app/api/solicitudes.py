from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import EstadoSolicitud, Solicitud, SolicitudCreate, SolicitudRead, Taller, Tecnico
from app.models.user import User, UserRole

router = APIRouter()


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


def build_solicitud_read(session: Session, solicitud: Solicitud) -> SolicitudRead:
    data = SolicitudRead.model_validate(solicitud)
    taller_nombre = None
    tecnico_nombre = None
    tecnico_especialidad = None

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller:
            taller_nombre = taller.nombre_comercial

    if solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico_nombre = tecnico.nombre
            tecnico_especialidad = tecnico.especialidad

    return data.model_copy(
        update={
            "taller_nombre": taller_nombre,
            "tecnico_nombre": tecnico_nombre,
            "tecnico_especialidad": tecnico_especialidad,
        }
    )


def obtener_taller_del_usuario(session: Session, current_user: User) -> Taller | None:
    return session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()


@router.post("/", response_model=SolicitudRead)
def crear_solicitud(*, session: Session = Depends(get_session), solicitud_in: SolicitudCreate):
    solicitud = Solicitud.model_validate(solicitud_in)
    clasif, prio, resm = simular_procesamiento_ia(solicitud.descripcion)
    solicitud.clasificacion_ia = clasif
    solicitud.prioridad_ia = prio
    solicitud.resumen_ia = resm
    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)


@router.get("/", response_model=List[SolicitudRead])
def listar_solicitudes(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    solicitudes = session.exec(select(Solicitud).offset(skip).limit(limit)).all()
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


@router.get("/{solicitud_id}", response_model=SolicitudRead)
def obtener_solicitud(*, session: Session = Depends(get_session), solicitud_id: int):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
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

    if tecnico_id:
        tecnico = session.get(Tecnico, tecnico_id)
        if not tecnico:
            raise HTTPException(status_code=404, detail="Tecnico no encontrado")

        if current_user.role != UserRole.ADMIN and (not taller or tecnico.taller_id != taller.id):
            raise HTTPException(status_code=400, detail="El tecnico no pertenece a tu taller")

        solicitud.tecnico_id = tecnico_id
        solicitud.taller_id = tecnico.taller_id
        if nuevo_estado not in (EstadoSolicitud.RESUELTA, EstadoSolicitud.CANCELADA):
            tecnico.disponible = False
            session.add(tecnico)
    elif nuevo_estado == EstadoSolicitud.ASIGNADA and current_user.role != UserRole.ADMIN and taller:
        solicitud.taller_id = taller.id

    if nuevo_estado in (EstadoSolicitud.RESUELTA, EstadoSolicitud.CANCELADA) and solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico.disponible = True
            session.add(tecnico)

    solicitud.estado = nuevo_estado
    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)
