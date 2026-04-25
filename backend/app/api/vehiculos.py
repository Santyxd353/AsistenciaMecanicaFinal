from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import Vehiculo, VehiculoCreate, VehiculoRead, VehiculoUpdate
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=VehiculoRead)
def crear_vehiculo(
    *,
    session: Session = Depends(get_session),
    vehiculo_in: VehiculoCreate,
    current_user: User = Depends(get_current_user),
):
    vehiculo = Vehiculo.model_validate(vehiculo_in)
    vehiculo.propietario_id = current_user.id
    session.add(vehiculo)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo registrar el vehiculo. Verifica que la placa no este duplicada.",
        ) from exc

    session.refresh(vehiculo)
    return vehiculo


@router.get("/", response_model=List[VehiculoRead])
def listar_vehiculos(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Vehiculo)
        .where(Vehiculo.propietario_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    vehiculos = session.exec(statement).all()
    return vehiculos


@router.get("/{vehiculo_id}", response_model=VehiculoRead)
def obtener_vehiculo(
    *,
    session: Session = Depends(get_session),
    vehiculo_id: int,
    current_user: User = Depends(get_current_user),
):
    vehiculo = session.get(Vehiculo, vehiculo_id)
    if not vehiculo or vehiculo.propietario_id != current_user.id:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
    return vehiculo


@router.put("/{vehiculo_id}", response_model=VehiculoRead)
def actualizar_vehiculo(
    *,
    session: Session = Depends(get_session),
    vehiculo_id: int,
    vehiculo_in: VehiculoUpdate,
    current_user: User = Depends(get_current_user),
):
    vehiculo = session.get(Vehiculo, vehiculo_id)
    if not vehiculo or vehiculo.propietario_id != current_user.id:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")

    update_data = vehiculo_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehiculo, field, value)

    session.add(vehiculo)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo actualizar el vehiculo. Verifica que la placa no este duplicada.",
        ) from exc

    session.refresh(vehiculo)
    return vehiculo
