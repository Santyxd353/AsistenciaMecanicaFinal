from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.security import get_password_hash
from app.db.session import get_session
from app.models.domain import WorkshopAdminCreate, WorkshopAdminRead
from app.models.user import User, UserRole
from app.services.subscription_limits import count_tenant_admins, ensure_can_create_admin

router = APIRouter()


def _tenant_operativo(current_user: User, tenant_id: int | None = None) -> int:
    if current_user.role == UserRole.ADMIN and current_user.tenant_id is None:
        if tenant_id is None:
            raise HTTPException(status_code=400, detail="El superadmin debe indicar tenant_id.")
        return tenant_id
    if current_user.role not in {UserRole.WORKSHOP, UserRole.ADMIN} or current_user.tenant_id is None:
        raise HTTPException(status_code=403, detail="Solo administradores pueden gestionar administradores.")
    return current_user.tenant_id


def _read(user: User) -> WorkshopAdminRead:
    return WorkshopAdminRead(
        id=user.id or 0,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        tenant_id=user.tenant_id,
    )


@router.get("/", response_model=list[WorkshopAdminRead])
def listar_administradores(
    tenant_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tenant = _tenant_operativo(current_user, tenant_id)
    users = session.exec(
        select(User)
        .where(User.tenant_id == tenant)
        .where(User.role == UserRole.WORKSHOP)
        .order_by(User.id)
    ).all()
    return [_read(user) for user in users]


@router.post("/", response_model=WorkshopAdminRead, status_code=status.HTTP_201_CREATED)
def crear_administrador(
    payload: WorkshopAdminCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tenant = _tenant_operativo(current_user)
    ensure_can_create_admin(session, tenant)
    user = User(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        full_name=(payload.full_name or "").strip() or None,
        role=UserRole.WORKSHOP,
        is_active=True,
        tenant_id=tenant,
        hashed_password=get_password_hash(payload.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo crear el administrador. Usuario o correo ya existe.",
        ) from exc
    session.refresh(user)
    return _read(user)


@router.delete("/{user_id}")
def desactivar_administrador(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tenant = _tenant_operativo(current_user)
    user = session.get(User, user_id)
    if not user or user.tenant_id != tenant or user.role != UserRole.WORKSHOP:
        raise HTTPException(status_code=404, detail="Administrador no encontrado.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta.")
    if user.is_active and count_tenant_admins(session, tenant) <= 1:
        raise HTTPException(status_code=400, detail="Debe quedar al menos un administrador activo.")
    user.is_active = False
    session.add(user)
    session.commit()
    return {"ok": True}
