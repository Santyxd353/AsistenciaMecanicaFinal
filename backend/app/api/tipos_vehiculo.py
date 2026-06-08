"""Catálogo de tipos de vehículo que un taller puede atender.

Decisiones:
* Lista abierta administrable: cualquier rol autenticado puede consultarla; sólo
  ADMIN puede crear / renombrar items (mismo patrón que `especialidades_taller`).
* Se siembra automáticamente desde `seed_default_tipos_vehiculo` para que el
  formulario de onboarding tenga opciones desde el primer arranque.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    TipoVehiculo,
    TipoVehiculoBase,
    TipoVehiculoRead,
)
from app.models.user import User, UserRole


router = APIRouter()


@router.get("/", response_model=list[TipoVehiculoRead])
def listar_tipos_vehiculo(
    session: Session = Depends(get_session),
):
    """Catálogo público: lo consume el onboarding del taller ANTES de
    autenticarse (durante el flujo "compré plan → registro taller").
    Por eso no exige token."""
    items = session.exec(select(TipoVehiculo).order_by(TipoVehiculo.nombre)).all()
    return [TipoVehiculoRead.model_validate(item) for item in items]


@router.post("/", response_model=TipoVehiculoRead, status_code=status.HTTP_201_CREATED)
def crear_tipo_vehiculo(
    data: TipoVehiculoBase,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede crear tipos de vehículo.",
        )
    nombre = (data.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre obligatorio.")
    existente = session.exec(select(TipoVehiculo).where(TipoVehiculo.nombre == nombre)).first()
    if existente:
        return TipoVehiculoRead.model_validate(existente)
    item = TipoVehiculo(nombre=nombre)
    session.add(item)
    session.commit()
    session.refresh(item)
    return TipoVehiculoRead.model_validate(item)
