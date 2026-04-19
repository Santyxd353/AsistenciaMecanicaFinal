from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import Taller, Tecnico
from app.models.user import User, UserRole

router = APIRouter()


class TecnicoIn(BaseModel):
    nombre: str
    especialidad: str
    disponible: bool = True
    latitud: float | None = None
    longitud: float | None = None
    taller_id: int | None = None


def obtener_taller_del_usuario(session: Session, current_user: User) -> Taller | None:
    return session.exec(
        select(Taller).where(Taller.propietario_id == current_user.id)
    ).first()


@router.post("/")
def crear_tecnico(
    *,
    session: Session = Depends(get_session),
    tecnico_in: TecnicoIn,
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ADMIN and tecnico_in.taller_id:
        taller = session.get(Taller, tecnico_in.taller_id)
    else:
        taller = obtener_taller_del_usuario(session, current_user)

    if not taller:
        raise HTTPException(status_code=400, detail="Debes tener un taller registrado para crear tecnicos")

    tecnico = Tecnico(
        nombre=tecnico_in.nombre,
        especialidad=tecnico_in.especialidad,
        disponible=tecnico_in.disponible,
        latitud=tecnico_in.latitud,
        longitud=tecnico_in.longitud,
        taller_id=taller.id,
    )

    session.add(tecnico)
    session.commit()
    session.refresh(tecnico)
    return tecnico


@router.get("/", response_model=List[Tecnico])
def listar_tecnicos(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ADMIN:
        return session.exec(select(Tecnico).offset(skip).limit(limit)).all()

    taller = obtener_taller_del_usuario(session, current_user)
    if not taller:
        return []

    return session.exec(
        select(Tecnico).where(Tecnico.taller_id == taller.id).offset(skip).limit(limit)
    ).all()


@router.patch("/{tecnico_id}/disponibilidad")
def actualizar_disponibilidad(
    *,
    session: Session = Depends(get_session),
    tecnico_id: int,
    disponible: bool,
    current_user: User = Depends(get_current_user),
):
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="Tecnico no encontrado")

    if current_user.role != UserRole.ADMIN:
        taller = obtener_taller_del_usuario(session, current_user)
        if not taller or tecnico.taller_id != taller.id:
            raise HTTPException(status_code=403, detail="No tienes permisos para modificar este tecnico")

    tecnico.disponible = disponible
    session.add(tecnico)
    session.commit()
    session.refresh(tecnico)
    return tecnico
