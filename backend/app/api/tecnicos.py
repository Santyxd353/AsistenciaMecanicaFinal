from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel

from app.db.session import get_session
from app.models.domain import Tecnico, Taller
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

class TecnicoIn(BaseModel):
    nombre: str
    especialidad: str
    disponible: bool = True
    latitud: float | None = None
    longitud: float | None = None

@router.post("/")
def crear_tecnico(
    *,
    session: Session = Depends(get_session),
    tecnico_in: TecnicoIn,
    current_user: User = Depends(get_current_user)
):
    """
    Crear un nuevo técnico para el taller del usuario actual.
    Solo usuarios WORKSHOP con taller registrado pueden crear técnicos.
    """
    # Verificar que el usuario tenga un taller
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller:
        raise HTTPException(
            status_code=400,
            detail="Debes tener un taller registrado para crear técnicos"
        )

    tecnico = Tecnico(
        nombre=tecnico_in.nombre,
        especialidad=tecnico_in.especialidad,
        disponible=tecnico_in.disponible,
        latitud=tecnico_in.latitud,
        longitud=tecnico_in.longitud,
        taller_id=taller.id,  # Usar el ID del taller del usuario
    )

    session.add(tecnico)
    session.commit()
    session.refresh(tecnico)
    return tecnico

@router.get("/")
def listar_tecnicos(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Listar técnicos del taller del usuario actual.
    """
    # Obtener el taller del usuario
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller:
        return []  # Si no tiene taller, devolver lista vacía

    tecnicos = session.exec(
        select(Tecnico).where(Tecnico.taller_id == taller.id)
        .offset(skip).limit(limit)
    ).all()
    return tecnicos

@router.patch("/{tecnico_id}/disponibilidad")
def actualizar_disponibilidad(
    *,
    session: Session = Depends(get_session),
    tecnico_id: int,
    disponible: bool,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar la disponibilidad de un técnico.
    Solo el propietario del taller puede modificar sus técnicos.
    """
    # Obtener el técnico
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    # Verificar que el técnico pertenece al taller del usuario
    taller = session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()

    if not taller or tecnico.taller_id != taller.id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para modificar este técnico"
        )

    tecnico.disponible = disponible
    session.add(tecnico)
    session.commit()
    session.refresh(tecnico)
    return tecnico
