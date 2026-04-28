from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.domain import Especialidad, EspecialidadCreate

router = APIRouter()

@router.get("/")
def listar_especialidades(session: Session = Depends(get_session)):
    return session.exec(
        select(Especialidad).order_by(Especialidad.nombre)
    ).all()

@router.post("/")
def crear_especialidad(
    data: EspecialidadCreate,
    session: Session = Depends(get_session)
):
    nombre_limpio = data.nombre.strip()

    existente = session.exec(
        select(Especialidad).where(Especialidad.nombre == nombre_limpio)
    ).first()

    if existente:
        raise HTTPException(status_code=400, detail="La especialidad ya existe")

    especialidad = Especialidad(nombre=nombre_limpio)
    session.add(especialidad)
    session.commit()
    session.refresh(especialidad)
    return especialidad