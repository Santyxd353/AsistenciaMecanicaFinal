from __future__ import annotations

from datetime import datetime
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.auth import build_auth_response
from app.api.talleres import _obtener_especialidades_taller
from app.core.security import get_password_hash
from app.db.session import get_session
from app.models.domain import (
    OnboardingAdminCreate,
    SubscriptionPaymentMock,
    Taller,
    TallerCreate,
    Tenant,
    TenantSubscription,
)
from app.models.user import AuthResponse, User, UserRole

router = APIRouter()


class WorkshopOnboardingPayload(BaseModel):
    onboarding_token: str
    admin: OnboardingAdminCreate
    taller: TallerCreate


def _slugify(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "taller"


def _unique_slug(session: Session, name: str) -> str:
    base = _slugify(name)
    candidate = base
    suffix = 1
    while session.exec(select(Tenant).where(Tenant.slug == candidate)).first():
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


@router.post("/workshop", response_model=AuthResponse)
def crear_taller_desde_onboarding(
    payload: WorkshopOnboardingPayload,
    session: Session = Depends(get_session),
):
    payment = session.exec(
        select(SubscriptionPaymentMock)
        .where(SubscriptionPaymentMock.onboarding_token == payload.onboarding_token)
    ).first()
    if not payment or payment.estado != "pagado":
        raise HTTPException(status_code=400, detail="El pago del plan no existe o no fue confirmado.")
    if payment.usado:
        raise HTTPException(status_code=409, detail="Este enlace de creacion de taller ya fue usado.")

    if len(payload.admin.password) < 6:
        raise HTTPException(status_code=400, detail="La contrasena debe tener al menos 6 caracteres.")
    if not payload.taller.nombre_comercial.strip():
        raise HTTPException(status_code=400, detail="El nombre comercial del taller es obligatorio.")

    especialidades = _obtener_especialidades_taller(session, payload.taller.especialidad_ids)
    tenant = Tenant(
        nombre=payload.taller.nombre_comercial.strip(),
        slug=_unique_slug(session, payload.taller.nombre_comercial),
        descripcion=f"Tenant creado desde onboarding del plan #{payment.plan_id}.",
        activo=True,
    )
    session.add(tenant)
    session.flush()

    admin = User(
        username=payload.admin.username.strip(),
        email=payload.admin.email.strip().lower(),
        full_name=(payload.admin.full_name or "").strip() or None,
        role=UserRole.WORKSHOP,
        is_active=True,
        tenant_id=tenant.id,
        hashed_password=get_password_hash(payload.admin.password),
    )
    session.add(admin)
    session.flush()

    taller_data = payload.taller.model_dump(exclude={"especialidad_ids"})
    taller = Taller(
        **taller_data,
        propietario_id=admin.id or 0,
        tenant_id=tenant.id,
    )
    taller.especialidades = especialidades
    session.add(taller)
    session.flush()

    payment.tenant_id = tenant.id
    payment.usado = True
    session.add(payment)

    subscription = TenantSubscription(
        tenant_id=tenant.id or 0,
        plan_id=payment.plan_id,
        estado="activa",
        pago_mock_id=payment.id,
        fecha_inicio=datetime.utcnow(),
    )
    session.add(subscription)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo crear el taller. Verifica que usuario/correo no existan.",
        ) from exc

    session.refresh(admin)
    return build_auth_response(admin)
