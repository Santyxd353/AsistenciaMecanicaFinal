from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.domain import Solicitud, SolicitudCreate, SolicitudRead, Tecnico
from app.models.user import User

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
        taller = session.get(User, solicitud.taller_id)
        if taller:
            taller_nombre = taller.full_name or taller.username

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
):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    solicitud.estado = estado

    if estado == "asignada" and tecnico_id:
        tecnico = session.get(Tecnico, tecnico_id)
        if not tecnico:
            raise HTTPException(status_code=404, detail="Tecnico no encontrado")
        solicitud.tecnico_id = tecnico_id
        solicitud.taller_id = tecnico.taller_id
        tecnico.disponible = False
        session.add(tecnico)

    if estado in ("resuelta", "cancelada") and solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico.disponible = True
            session.add(tecnico)

    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return build_solicitud_read(session, solicitud)
