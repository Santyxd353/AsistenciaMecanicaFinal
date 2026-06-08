"""Pagos: registro simulado del cobro al cliente con comisión 10% para la plataforma.

No se integra con pasarela real (decisión documentada): el endpoint deja la
arquitectura lista para conectar Stripe/MercadoPago más adelante reemplazando
solo el `metodo` y la `referencia`.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    EstadoSolicitud,
    Pago,
    PagoRead,
    Solicitud,
    Taller,
    TipoNotificacion,
    Vehiculo,
)
from app.models.user import User, UserRole
from app.services.audit import registrar_auditoria
from app.services.notificaciones import crear_notificacion


router = APIRouter()


COMISION_PLATAFORMA = 0.10


class PagoCreate(BaseModel):
    monto: float = Field(..., gt=0)
    metodo: str = Field(default="simulado", max_length=30)


def _solicitud_del_cliente(session: Session, solicitud_id: int, current_user: User) -> Solicitud:
    solicitud = session.get(Solicitud, solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
    if solicitud.vehiculo_id:
        vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
        if not vehiculo or vehiculo.propietario_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el dueño del vehículo puede pagar la solicitud.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La solicitud no tiene vehículo asociado.",
        )
    return solicitud


@router.post(
    "/solicitudes/{solicitud_id}",
    response_model=PagoRead,
    status_code=status.HTTP_201_CREATED,
)
def registrar_pago(
    solicitud_id: int,
    payload: PagoCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Registra un pago. Solo el cliente dueño del vehículo puede pagar.

    Reglas:
    * la solicitud debe estar FINALIZADA antes de cobrar
    * la comisión se calcula al 10% sobre el monto cobrado
    * se actualiza `solicitud.estado_pago = pagado` y `fecha_pago`
    """
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el cliente puede registrar pagos.",
        )

    solicitud = _solicitud_del_cliente(session, solicitud_id, current_user)

    if solicitud.estado != EstadoSolicitud.FINALIZADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede pagar una solicitud finalizada.",
        )
    if solicitud.estado_pago == "pagado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta solicitud ya fue pagada.",
        )

    monto_base = solicitud.precio_cobrado if solicitud.cotizacion_seleccionada_id else payload.monto
    if monto_base is None or monto_base <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La solicitud no tiene un monto valido para pagar.",
        )
    monto = round(monto_base, 2)
    comision = round(monto * COMISION_PLATAFORMA, 2)

    pago = Pago(
        solicitud_id=solicitud_id,
        usuario_id=current_user.id or 0,
        tenant_id=solicitud.tenant_id,
        monto=monto,
        comision_plataforma=comision,
        metodo=payload.metodo,
        estado="pagado",
        referencia=f"sim_{secrets.token_hex(8)}",
    )
    session.add(pago)

    solicitud.estado_pago = "pagado"
    solicitud.fecha_pago = datetime.utcnow()
    solicitud.precio_cobrado = monto
    solicitud.comision_plataforma = comision
    session.add(solicitud)

    if solicitud.taller_id:
        taller = session.get(Taller, solicitud.taller_id)
        if taller and taller.propietario_id:
            crear_notificacion(
                session,
                destinatario_id=taller.propietario_id,
                tipo=TipoNotificacion.SERVICIO_CONCLUIDO_PAGO,
                titulo="Pago recibido",
                mensaje=(
                    f"Solicitud #{solicitud_id}: el cliente pagó "
                    f"{monto:.2f} (comisión plataforma {comision:.2f})."
                ),
                solicitud_id=solicitud_id,
                accion_url="/taller/solicitudes",
            )

    registrar_auditoria(
        session,
        actor=current_user,
        accion="pago_registrado",
        entidad="solicitud",
        entidad_id=solicitud_id,
        detalle=f"monto={monto} comision={comision} metodo={payload.metodo}",
    )

    session.commit()
    session.refresh(pago)
    return PagoRead.model_validate(pago)


@router.get("/solicitudes/{solicitud_id}", response_model=Optional[PagoRead])
def consultar_pago(
    solicitud_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Pago).where(Pago.solicitud_id == solicitud_id)
    if current_user.tenant_id is not None:
        stmt = stmt.where(Pago.tenant_id == current_user.tenant_id)
    pago = session.exec(stmt).first()
    if not pago:
        return None

    # Permisos: cliente dueño, taller dueño o admin.
    if current_user.role == UserRole.ADMIN or pago.usuario_id == current_user.id:
        return PagoRead.model_validate(pago)

    if current_user.role == UserRole.WORKSHOP:
        solicitud = session.get(Solicitud, solicitud_id)
        taller = session.exec(
            select(Taller)
            .where(Taller.propietario_id == current_user.id)
            .where(Taller.tenant_id == current_user.tenant_id)
        ).first()
        if solicitud and taller and solicitud.taller_id == taller.id:
            return PagoRead.model_validate(pago)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos sobre este pago.",
    )


@router.get("/mis-pagos", response_model=List[PagoRead])
def listar_mis_pagos(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pagos = session.exec(
        select(Pago)
        .where(Pago.usuario_id == current_user.id)
        .where(Pago.tenant_id == current_user.tenant_id)
        .order_by(Pago.fecha_creacion.desc())
    ).all()
    return [PagoRead.model_validate(item) for item in pagos]


@router.get("/taller", response_model=List[PagoRead])
def pagos_recibidos_taller(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Pagos asociados a solicitudes del taller del usuario actual."""
    if current_user.role != UserRole.WORKSHOP:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el taller puede consultar sus pagos.",
        )
    taller = session.exec(
        select(Taller)
        .where(Taller.propietario_id == current_user.id)
        .where(Taller.tenant_id == current_user.tenant_id)
    ).first()
    if not taller:
        return []
    pagos = session.exec(
        select(Pago)
        .join(Solicitud, Solicitud.id == Pago.solicitud_id)
        .where(Solicitud.taller_id == taller.id)
        .where(Solicitud.tenant_id == taller.tenant_id)
        .where(Pago.tenant_id == taller.tenant_id)
        .order_by(Pago.fecha_creacion.desc())
    ).all()
    return [PagoRead.model_validate(item) for item in pagos]
