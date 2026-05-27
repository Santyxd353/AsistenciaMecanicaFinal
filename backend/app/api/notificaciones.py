from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, func, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    Notificacion,
    NotificacionRead,
    NotificacionesNoLeidasRead,
)
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=List[NotificacionRead])
def listar_notificaciones(
    *,
    solo_no_leidas: bool = False,
    solicitud_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(Notificacion).where(
        Notificacion.destinatario_id == current_user.id
    )
    if current_user.tenant_id is not None:
        statement = statement.where(Notificacion.tenant_id == current_user.tenant_id)

    if solo_no_leidas:
        statement = statement.where(Notificacion.leida == False)

    if solicitud_id is not None:
        statement = statement.where(Notificacion.solicitud_id == solicitud_id)

    notificaciones = session.exec(
        statement
        .order_by(Notificacion.fecha_creacion.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return notificaciones


@router.get("/no-leidas/count", response_model=NotificacionesNoLeidasRead)
def contar_notificaciones_no_leidas(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    total = session.exec(
        select(func.count(Notificacion.id)).where(
            Notificacion.destinatario_id == current_user.id,
            Notificacion.tenant_id == current_user.tenant_id,
            Notificacion.leida == False,
        )
    ).one()

    return NotificacionesNoLeidasRead(total=int(total or 0))


@router.patch("/marcar-todas-leidas", response_model=NotificacionesNoLeidasRead)
def marcar_todas_como_leidas(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    notificaciones = session.exec(
        select(Notificacion).where(
            Notificacion.destinatario_id == current_user.id,
            Notificacion.tenant_id == current_user.tenant_id,
            Notificacion.leida == False,
        )
    ).all()

    for notificacion in notificaciones:
        notificacion.leida = True
        session.add(notificacion)

    session.commit()
    return NotificacionesNoLeidasRead(total=0)


@router.patch("/{notificacion_id}/leida", response_model=NotificacionRead)
def marcar_notificacion_como_leida(
    *,
    notificacion_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    notificacion = session.get(Notificacion, notificacion_id)

    if (
        not notificacion
        or notificacion.destinatario_id != current_user.id
        or notificacion.tenant_id != current_user.tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificacion no encontrada.",
        )

    notificacion.leida = True
    session.add(notificacion)
    session.commit()
    session.refresh(notificacion)

    return notificacion
