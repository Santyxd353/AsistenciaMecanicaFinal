from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
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

    if "no enciende" in desc_eval or "batería" in desc_eval or "click click" in desc_eval or "arranca" in desc_eval:
        clasificacion = "Problema de Batería / Eléctrico"
        prioridad = "Media"
        resumen = "El vehículo no responde al arranque, posible descarga de batería o falla en el alternador. Requiere auxilio eléctrico."
    elif "pinchada" in desc_eval or "llanta" in desc_eval:
        clasificacion = "Neumáticos"
        prioridad = "Baja"
        resumen = "Vehículo inmovilizado por llanta pinchada. Requiere taller móvil o grúa para cambio."
    elif "humo" in desc_eval or "recalentado" in desc_eval:
        clasificacion = "Problema de Motor / Recalentamiento"
        prioridad = "Alta"
        resumen = "Alerta crítica: posible fuga de refrigerante o problema grave de motor. ¡Riesgo de daño permanente!"

    return clasificacion, prioridad, resumen


@router.post("/", response_model=SolicitudRead)
def crear_solicitud(*, session: Session = Depends(get_session), solicitud_in: SolicitudCreate):
    solicitud = Solicitud.from_orm(solicitud_in)
    clasif, prio, resm = simular_procesamiento_ia(solicitud.descripcion)
    solicitud.clasificacion_ia = clasif
    solicitud.prioridad_ia = prio
    solicitud.resumen_ia = resm
    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return solicitud


@router.get("/", response_model=List[SolicitudRead])
def listar_solicitudes(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    solicitudes = session.exec(select(Solicitud).offset(skip).limit(limit)).all()
    return solicitudes


@router.get("/{solicitud_id}", response_model=SolicitudRead)
def obtener_solicitud(*, session: Session = Depends(get_session), solicitud_id: int):
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud


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

    # Si se está asignando, vincular el técnico y marcarlo como ocupado
    if estado == "asignada" and tecnico_id:
        tecnico = session.get(Tecnico, tecnico_id)
        if not tecnico:
            raise HTTPException(status_code=404, detail="Técnico no encontrado")
        solicitud.tecnico_id = tecnico_id
        tecnico.disponible = False
        session.add(tecnico)

    # Si se resuelve o cancela, liberar al técnico asignado
    if estado in ("resuelta", "cancelada") and solicitud.tecnico_id:
        tecnico = session.get(Tecnico, solicitud.tecnico_id)
        if tecnico:
            tecnico.disponible = True
            session.add(tecnico)

    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return solicitud
