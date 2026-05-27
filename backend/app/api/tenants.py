"""CRUD de Tenants.

Acceso restringido al ADMIN global (`tenant_id IS NULL` y rol ADMIN). Un
admin que pertenece a un tenant operativo NO puede crear otros tenants;
solo el admin de plataforma.

Sirve además el endpoint público (autenticado) `/mi-tenant` para que cada
cliente sepa a qué red pertenece.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import Tenant, TenantCreate, TenantRead, TenantUpdate
from app.models.user import User, UserRole


router = APIRouter()


def _solo_admin_global(current_user: User) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede gestionar tenants.",
        )


@router.get("/mi-tenant", response_model=TenantRead | None)
def mi_tenant(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.tenant_id is None:
        return None
    tenant = session.get(Tenant, current_user.tenant_id)
    return TenantRead.model_validate(tenant) if tenant else None


@router.get("/", response_model=List[TenantRead])
def listar_tenants(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _solo_admin_global(current_user)
    tenants = session.exec(select(Tenant).order_by(Tenant.id)).all()
    return [TenantRead.model_validate(item) for item in tenants]


@router.post("/", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
def crear_tenant(
    payload: TenantCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _solo_admin_global(current_user)
    slug = payload.slug.strip().lower()
    if not slug:
        raise HTTPException(status_code=400, detail="El slug es obligatorio.")
    existente = session.exec(select(Tenant).where(Tenant.slug == slug)).first()
    if existente:
        raise HTTPException(status_code=409, detail="Ya existe un tenant con ese slug.")
    tenant = Tenant(
        nombre=payload.nombre.strip(),
        slug=slug,
        descripcion=(payload.descripcion or "").strip() or None,
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return TenantRead.model_validate(tenant)


@router.put("/{tenant_id}", response_model=TenantRead)
def actualizar_tenant(
    tenant_id: int,
    payload: TenantUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _solo_admin_global(current_user)
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    if payload.nombre is not None:
        tenant.nombre = payload.nombre.strip()
    if payload.descripcion is not None:
        tenant.descripcion = payload.descripcion.strip() or None
    if payload.activo is not None:
        tenant.activo = payload.activo
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return TenantRead.model_validate(tenant)
