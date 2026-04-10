from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.domain import Tecnico

router = APIRouter()

# Schema limpio para crear un Tecnico (sin la FK que puede confundir)
class TecnicoCreate:
    pass

from pydantic import BaseModel

class TecnicoIn(BaseModel):
    nombre: str
    especialidad: str
    disponible: bool = True
    latitud: float | None = None
    longitud: float | None = None
    taller_id: int | None = None

@router.post("/")
def crear_tecnico(*, session: Session = Depends(get_session), tecnico_in: TecnicoIn):
    tecnico = Tecnico(
        nombre=tecnico_in.nombre,
        especialidad=tecnico_in.especialidad,
        disponible=tecnico_in.disponible,
        latitud=tecnico_in.latitud,
        longitud=tecnico_in.longitud,
        taller_id=tecnico_in.taller_id,
    )
    session.add(tecnico)
    session.commit()
    session.refresh(tecnico)
    return tecnico

@router.get("/")
def listar_tecnicos(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    tecnicos = session.exec(select(Tecnico).offset(skip).limit(limit)).all()
    return tecnicos

@router.patch("/{tecnico_id}/disponibilidad")
def actualizar_disponibilidad(
    *, session: Session = Depends(get_session), tecnico_id: int, disponible: bool
):
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    tecnico.disponible = disponible
    session.add(tecnico)
    session.commit()
    session.refresh(tecnico)
    return tecnico
