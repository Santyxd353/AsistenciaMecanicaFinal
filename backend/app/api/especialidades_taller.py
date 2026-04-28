from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.domain import (
    EspecialidadTaller,
    EspecialidadTallerBase,
    EspecialidadTallerRead,
)

router = APIRouter()


def _normalizar_nombre(nombre: str) -> str:
    return " ".join(nombre.strip().split())


@router.get("/", response_model=list[EspecialidadTallerRead])
def listar_especialidades_taller(session: Session = Depends(get_session)):
    return session.exec(
        select(EspecialidadTaller).order_by(EspecialidadTaller.nombre)
    ).all()


@router.post("/", response_model=EspecialidadTallerRead)
def crear_especialidad_taller(
    data: EspecialidadTallerBase,
    session: Session = Depends(get_session)
):
    nombre_limpio = _normalizar_nombre(data.nombre)
    if not nombre_limpio:
        raise HTTPException(status_code=400, detail="El nombre de la especialidad es obligatorio")

    especialidades = session.exec(select(EspecialidadTaller)).all()
    existente = next(
        (item for item in especialidades if item.nombre.strip().casefold() == nombre_limpio.casefold()),
        None
    )

    if existente:
        raise HTTPException(status_code=400, detail="La especialidad ya existe")

    especialidad = EspecialidadTaller(nombre=nombre_limpio)
    session.add(especialidad)
    session.commit()
    session.refresh(especialidad)
    return especialidad
