from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import Session, select
from fastapi import Depends

from app.db.session import get_session
from app.models.domain import SaaSPlan, SaaSPlanRead
from app.services.subscription_limits import plan_to_read

router = APIRouter()


@router.get("/", response_model=list[SaaSPlanRead])
def listar_planes(session: Session = Depends(get_session)):
    planes = session.exec(
        select(SaaSPlan)
        .where(SaaSPlan.activo == True)
        .order_by(SaaSPlan.precio_mensual)
    ).all()
    return [plan_to_read(plan) for plan in planes]


@router.get("/{codigo}", response_model=SaaSPlanRead)
def detalle_plan(codigo: str, session: Session = Depends(get_session)):
    plan = session.exec(
        select(SaaSPlan)
        .where(SaaSPlan.codigo == codigo.strip().lower())
        .where(SaaSPlan.activo == True)
    ).first()
    if not plan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Plan no encontrado.")
    return plan_to_read(plan)
