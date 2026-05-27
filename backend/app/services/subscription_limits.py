from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.domain import SaaSPlan, SaaSPlanRead, TenantSubscription, Tecnico
from app.models.user import User, UserRole


LIMIT_ERROR_STATUS = status.HTTP_402_PAYMENT_REQUIRED


def plan_to_read(plan: SaaSPlan) -> SaaSPlanRead:
    return SaaSPlanRead(
        id=plan.id or 0,
        codigo=plan.codigo,
        nombre=plan.nombre,
        descripcion=plan.descripcion,
        precio_mensual=plan.precio_mensual,
        max_administradores=plan.max_administradores,
        max_mecanicos=plan.max_mecanicos,
        max_solicitudes_mes=plan.max_solicitudes_mes,
        beneficios=[item.strip() for item in (plan.beneficios or "").split("|") if item.strip()],
        activo=plan.activo,
    )


def get_plan_by_code(session: Session, codigo: str) -> SaaSPlan:
    plan = session.exec(
        select(SaaSPlan)
        .where(SaaSPlan.codigo == codigo.strip().lower())
        .where(SaaSPlan.activo == True)
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado.")
    return plan


def get_active_subscription(session: Session, tenant_id: int) -> tuple[TenantSubscription, SaaSPlan]:
    subscription = session.exec(
        select(TenantSubscription)
        .where(TenantSubscription.tenant_id == tenant_id)
        .where(TenantSubscription.estado == "activa")
        .order_by(TenantSubscription.fecha_creacion.desc())
    ).first()

    if subscription:
        plan = session.get(SaaSPlan, subscription.plan_id)
        if plan:
            return subscription, plan

    free_plan = get_plan_by_code(session, "gratis")
    subscription = TenantSubscription(
        tenant_id=tenant_id,
        plan_id=free_plan.id or 0,
        estado="activa",
    )
    session.add(subscription)
    session.flush()
    return subscription, free_plan


def count_tenant_admins(session: Session, tenant_id: int) -> int:
    return len(session.exec(
        select(User)
        .where(User.tenant_id == tenant_id)
        .where(User.role == UserRole.WORKSHOP)
        .where(User.is_active == True)
    ).all())


def count_tenant_mechanics(session: Session, tenant_id: int) -> int:
    return len(session.exec(
        select(Tecnico)
        .where(Tecnico.tenant_id == tenant_id)
        .where(Tecnico.activo == True)
    ).all())


def _raise_limit(code: str, message: str, plan: SaaSPlan, used: int, limit: int | None):
    raise HTTPException(
        status_code=LIMIT_ERROR_STATUS,
        detail={
            "code": code,
            "message": message,
            "plan": plan.codigo,
            "used": used,
            "limit": limit,
            "upgrade_url": "/upgrade-plan",
        },
    )


def ensure_can_create_admin(session: Session, tenant_id: int) -> None:
    _, plan = get_active_subscription(session, tenant_id)
    if plan.max_administradores is None:
        return
    used = count_tenant_admins(session, tenant_id)
    if used >= plan.max_administradores:
        _raise_limit(
            "PLAN_LIMIT_ADMIN",
            f"Tu plan {plan.nombre} permite {plan.max_administradores} administrador(es).",
            plan,
            used,
            plan.max_administradores,
        )


def ensure_can_create_mechanic(session: Session, tenant_id: int) -> None:
    _, plan = get_active_subscription(session, tenant_id)
    if plan.max_mecanicos is None:
        return
    used = count_tenant_mechanics(session, tenant_id)
    if used >= plan.max_mecanicos:
        _raise_limit(
            "PLAN_LIMIT_TECHNICIAN",
            f"Tu plan {plan.nombre} permite {plan.max_mecanicos} mecanico(s).",
            plan,
            used,
            plan.max_mecanicos,
        )


def current_subscription_payload(session: Session, tenant_id: int) -> dict:
    subscription, plan = get_active_subscription(session, tenant_id)
    admins = count_tenant_admins(session, tenant_id)
    mechanics = count_tenant_mechanics(session, tenant_id)
    subscription.fecha_actualizacion = datetime.utcnow()
    session.add(subscription)
    return {
        "plan": plan_to_read(plan).model_dump(),
        "estado": subscription.estado,
        "uso": {
            "administradores": admins,
            "mecanicos": mechanics,
        },
        "limites": {
            "administradores": plan.max_administradores,
            "mecanicos": plan.max_mecanicos,
            "solicitudes_mes": plan.max_solicitudes_mes,
        },
    }
