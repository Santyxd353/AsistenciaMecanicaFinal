from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.domain import Solicitud, SolicitudCreate, SolicitudRead, Tecnico, Taller
from app.models.user import User
from app.api.deps import get_current_user

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


@router.get("/mis-solicitudes", response_model=List[SolicitudRead])
def listar_solicitudes_taller(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Listar solicitudes asignadas al taller del usuario actual.
    Solo usuarios WORKSHOP con taller pueden ver sus solicitudes.
    """
    # Obtener el taller del usuario
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller:
        return []  # Si no tiene taller, devolver lista vacía

    solicitudes = session.exec(
        select(Solicitud).where(Solicitud.taller_id == taller.id)
        .offset(skip).limit(limit)
    ).all()
    return solicitudes


@router.patch("/{solicitud_id}/estado")
def actualizar_estado_solicitud(
    *,
    session: Session = Depends(get_session),
    solicitud_id: int,
    estado: str,
    tecnico_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar el estado de una solicitud asignada al taller del usuario.
    Solo el propietario del taller puede modificar sus solicitudes.
    """
    # Obtener la solicitud
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Verificar que la solicitud pertenece al taller del usuario
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller or solicitud.taller_id != taller.id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para modificar esta solicitud"
        )

    # Validar el estado
    from app.models.domain import EstadoSolicitud
    try:
        nuevo_estado = EstadoSolicitud(estado)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Estados válidos: {[e.value for e in EstadoSolicitud]}"
        )

    # Si se proporciona tecnico_id, verificar que pertenezca al taller
    if tecnico_id:
        tecnico = session.get(Tecnico, tecnico_id)
        if not tecnico or tecnico.taller_id != taller.id:
            raise HTTPException(
                status_code=400,
                detail="El técnico no pertenece a tu taller"
            )
        solicitud.tecnico_id = tecnico_id

    solicitud.estado = nuevo_estado
    session.add(solicitud)
    session.commit()
    session.refresh(solicitud)
    return solicitud


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
