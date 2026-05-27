from __future__ import annotations

from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    PlanCheckoutCreate,
    PlanCheckoutRead,
    PlanPaymentRead,
    SaaSPlan,
    SubscriptionPaymentMock,
    TenantSubscription,
)
from app.models.user import User, UserRole
from app.services.subscription_limits import (
    current_subscription_payload,
    get_plan_by_code,
    plan_to_read,
)

router = APIRouter()


class ChangePlanPayload(BaseModel):
    plan_codigo: str


def _new_reference() -> str:
    return f"SUB-{secrets.token_hex(8).upper()}"


def _new_onboarding_token() -> str:
    return secrets.token_urlsafe(32)


@router.post("/checkout", response_model=PlanCheckoutRead)
def crear_checkout(payload: PlanCheckoutCreate, session: Session = Depends(get_session)):
    plan = get_plan_by_code(session, payload.plan_codigo)
    payment = SubscriptionPaymentMock(
        plan_id=plan.id or 0,
        monto=plan.precio_mensual,
        moneda="BOB",
        estado="pendiente_pago",
        referencia=_new_reference(),
        metodo="mock",
        contacto_email=payload.email.strip().lower(),
        contacto_nombre=(payload.nombre_contacto or "").strip() or None,
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return PlanCheckoutRead(
        checkout_id=payment.id or 0,
        referencia=payment.referencia,
        estado=payment.estado,
        monto=payment.monto,
        moneda=payment.moneda,
        plan=plan_to_read(plan),
    )


@router.post("/checkout/{checkout_id}/pay", response_model=PlanPaymentRead)
def pagar_checkout(checkout_id: int, session: Session = Depends(get_session)):
    payment = session.get(SubscriptionPaymentMock, checkout_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Checkout no encontrado.")
    plan = session.get(SaaSPlan, payment.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado.")
    if payment.estado == "pagado" and payment.onboarding_token:
        return PlanPaymentRead(
            checkout_id=payment.id or 0,
            estado=payment.estado,
            onboarding_token=payment.onboarding_token,
            plan_codigo=plan.codigo,
        )

    payment.estado = "pagado"
    payment.fecha_pago = datetime.utcnow()
    payment.onboarding_token = _new_onboarding_token()
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return PlanPaymentRead(
        checkout_id=payment.id or 0,
        estado=payment.estado,
        onboarding_token=payment.onboarding_token or "",
        plan_codigo=plan.codigo,
    )


@router.get("/current")
def suscripcion_actual(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.tenant_id is None:
        raise HTTPException(status_code=400, detail="El superadmin global no tiene plan operativo.")
    return current_subscription_payload(session, current_user.tenant_id)


@router.post("/change-plan")
def cambiar_plan(
    payload: ChangePlanPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.WORKSHOP, UserRole.ADMIN} or current_user.tenant_id is None:
        raise HTTPException(status_code=403, detail="Solo administradores de taller pueden cambiar plan.")

    plan = get_plan_by_code(session, payload.plan_codigo)
    current = session.exec(
        select(TenantSubscription)
        .where(TenantSubscription.tenant_id == current_user.tenant_id)
        .where(TenantSubscription.estado == "activa")
    ).all()
    for item in current:
        item.estado = "cancelada"
        item.fecha_actualizacion = datetime.utcnow()
        session.add(item)

    payment = SubscriptionPaymentMock(
        tenant_id=current_user.tenant_id,
        plan_id=plan.id or 0,
        monto=plan.precio_mensual,
        moneda="BOB",
        estado="pagado",
        referencia=_new_reference(),
        metodo="upgrade_mock",
        contacto_email=current_user.email,
        contacto_nombre=current_user.full_name,
        fecha_pago=datetime.utcnow(),
        usado=True,
    )
    session.add(payment)
    session.flush()

    subscription = TenantSubscription(
        tenant_id=current_user.tenant_id,
        plan_id=plan.id or 0,
        estado="activa",
        pago_mock_id=payment.id,
    )
    session.add(subscription)
    session.commit()
    return {
        "message": f"Plan actualizado a {plan.nombre}.",
        "subscription": current_subscription_payload(session, current_user.tenant_id),
    }
