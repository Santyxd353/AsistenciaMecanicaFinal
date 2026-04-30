from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    DispositivoToken,
    DispositivoTokenCreate,
    DispositivoTokenRead,
)
from app.models.user import User

router = APIRouter()


@router.post("/token", response_model=DispositivoTokenRead)
def registrar_token_dispositivo(
    *,
    payload: DispositivoTokenCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    token = payload.token.strip()
    plataforma = payload.plataforma.strip() or "android"

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token FCM es obligatorio.",
        )

    dispositivo = session.exec(
        select(DispositivoToken).where(DispositivoToken.token == token)
    ).first()

    now = datetime.utcnow()
    if dispositivo:
        dispositivo.usuario_id = current_user.id
        dispositivo.plataforma = plataforma
        dispositivo.activo = True
        dispositivo.fecha_actualizacion = now
    else:
        dispositivo = DispositivoToken(
            usuario_id=current_user.id,
            token=token,
            plataforma=plataforma,
            activo=True,
            fecha_actualizacion=now,
        )

    session.add(dispositivo)
    session.commit()
    session.refresh(dispositivo)
    return dispositivo


@router.delete("/token", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_token_dispositivo(
    *,
    payload: DispositivoTokenCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    dispositivo = session.exec(
        select(DispositivoToken).where(
            DispositivoToken.token == payload.token.strip(),
            DispositivoToken.usuario_id == current_user.id,
        )
    ).first()

    if dispositivo:
        dispositivo.activo = False
        dispositivo.fecha_actualizacion = datetime.utcnow()
        session.add(dispositivo)
        session.commit()

