from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from sqlalchemy import Integer, case

from app.db.session import get_session
from app.models.domain import Taller, TallerCreate, TallerRead, TallerUpdate
from app.models.user import User, UserRole
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=TallerRead)
def crear_taller(
    *,
    session: Session = Depends(get_session),
    taller_in: TallerCreate,
    current_user: User = Depends(get_current_user)
):
    # Verificar que el usuario tenga rol WORKSHOP
    if current_user.role != UserRole.WORKSHOP:
        raise HTTPException(
            status_code=403,
            detail="Solo usuarios con rol WORKSHOP pueden crear talleres"
        )
    
    if not taller_in.nombre_comercial.strip():
        raise HTTPException(
            status_code=400,
            detail="El nombre comercial es obligatorio"
        )

    # Verificar que el usuario no tenga ya un taller
    existing_taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if existing_taller:
        raise HTTPException(
            status_code=400,
            detail="Ya tienes un taller registrado"
        )

    # Crear el taller
    taller = Taller(
        **taller_in.model_dump(),
        propietario_id=current_user.id
    )

    session.add(taller)
    session.commit()
    session.refresh(taller)

    return taller


@router.get("/mi-taller", response_model=TallerRead)
def obtener_mi_taller(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener la información del taller del usuario actual.
    """
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller:
        raise HTTPException(
            status_code=404,
            detail="No se encontró un taller registrado para este usuario"
        )

    return taller


@router.put("/mi-taller", response_model=TallerRead)
def actualizar_mi_taller(
    *,
    session: Session = Depends(get_session),
    taller_update: TallerUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar la información del taller del usuario actual.
    """
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller:
        raise HTTPException(
            status_code=404,
            detail="No se encontró un taller registrado para este usuario"
        )

    # Actualizar solo los campos proporcionados
    update_data = taller_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(taller, field, value)

    session.add(taller)
    session.commit()
    session.refresh(taller)

    return taller


@router.get("/estadisticas")
def obtener_estadisticas_taller(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener estadísticas del taller del usuario actual.
    """
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller:
        raise HTTPException(
            status_code=404,
            detail="No se encontró un taller registrado para este usuario"
        )

    # Calcular estadísticas de servicios
    from app.models.domain import Solicitud, EstadoSolicitud

    servicios_stats = session.exec(
        select(
            func.count(Solicitud.id).label("total_servicios"),
            func.avg(Solicitud.precio_cobrado).label("ingreso_promedio"),
            func.sum(Solicitud.comision_plataforma).label("comisiones_totales")
        ).where(
            Solicitud.taller_id == taller.id,
            Solicitud.estado == EstadoSolicitud.RESUELTA
        )
    ).first()

    # Calcular estadísticas de técnicos
    from app.models.domain import Tecnico
    """
    tecnicos_stats = session.exec(
        select(
            func.count(Tecnico.id).label("total_tecnicos"),
            func.sum(Tecnico.disponible.cast(func.Integer)).label("tecnicos_disponibles")
        ).where(Tecnico.taller_id == taller.id)
    ).first()
    
    tecnicos_stats = session.exec(
        select(
            func.count(Tecnico.id).label("total_tecnicos"),
            func.sum(Tecnico.disponible.cast(Integer)).label("tecnicos_disponibles")
        ).where(Tecnico.taller_id == taller.id)
    ).first()
    """

    tecnicos_stats = session.exec(
        select(
            func.count(Tecnico.id).label("total_tecnicos"),
            func.sum(
                case((Tecnico.disponible == True, 1), else_=0)
            ).label("tecnicos_disponibles")
        ).where(Tecnico.taller_id == taller.id)
    ).first()

    return {
        "taller_info": {
            "id": taller.id,
            "nombre_comercial": taller.nombre_comercial,
            "calificacion_promedio": taller.calificacion_promedio,
            "total_servicios_completados": taller.total_servicios_completados
        },
        "servicios": {
            "total_completados": servicios_stats.total_servicios or 0,
            "ingreso_promedio_por_servicio": float(servicios_stats.ingreso_promedio or 0),
            "comisiones_totales_pagadas": float(servicios_stats.comisiones_totales or 0)
        },
        """
        "tecnicos": {
            "total_tecnicos": tecnicos_stats.total_tecnicos or 0,
            "tecnicos_disponibles": tecnicos_stats.tecnicos_disponibles or 0
        },
        """
        "tecnicos": {
            "total_tecnicos": int(tecnicos_stats.total_tecnicos or 0),
            "tecnicos_disponibles": int(tecnicos_stats.tecnicos_disponibles or 0)
        },
        "tiempo_respuesta_promedio": taller.tiempo_respuesta_promedio
    }