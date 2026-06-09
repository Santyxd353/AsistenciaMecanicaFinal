import os
from datetime import timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, or_, select

import re

from app.api.deps import get_current_user
from app.models.domain import Taller, Tecnico, Tenant
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    get_password_hash,
    verify_refresh_token,
    verify_password_reset_token,
    verify_password,
)
from app.db.session import get_session
from app.models.user import (
    AuthResponse,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    User,
    UserRead,
    UserRegister,
    UserRole,
    UserUpdate,
)
from app.services.password_reset_delivery import send_password_reset_email
from app.services.storage import save_upload_file

router = APIRouter()
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:4200").rstrip("/")
FORGOT_PASSWORD_RESPONSE = (
    "Si el correo existe, te enviamos instrucciones para restablecer la contraseña."
)
TECNICO_FORGOT_PASSWORD_RESPONSE = (
    "Usted no tiene autorización para poder solicitar recuperación de contraseña"
)


class LoginAdminPayload(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str


class LoginWorkerPayload(BaseModel):
    taller_id: int
    username: str
    password: str


class LoginClientPayload(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str


def build_auth_response(user: User) -> AuthResponse:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Multi-tenant: incluimos tenant_id en el JWT para que cada request entrante
    # pueda derivar el ámbito sin necesidad de hacer un JOIN extra. ADMIN sin
    # tenant se identifica por `tenant_id == null` en el payload.
    token_data = {
        "sub": user.username,
        "role": user.role,
        "user_id": user.id,
        "tenant_id": user.tenant_id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(data=token_data)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        user=UserRead.model_validate(user),
    )


def _slugify_tenant(name: str) -> str:
    """Convierte un texto libre en un slug seguro para URL/identificador.

    Reemplaza no-alfanuméricos por `-`, colapsa duplicados y lo pasa a
    minúsculas. Si queda vacío, devuelve un placeholder que el caller
    deberá completar (p. ej. con un sufijo aleatorio).
    """
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "tenant"


def _resolver_tenant_para_registro(
    *,
    db: Session,
    payload: UserRegister,
    role: UserRole,
) -> Tenant:
    """Resuelve qué Tenant asignar al nuevo usuario.

    Reglas:
    * Si el cliente envió `tenant_slug` → debe existir y estar activo.
    * Sin slug:
      - DRIVER → tenant `default` (se crea si no existe; pensado para clientes
        que se autoregistran sin pertenecer a una red específica).
      - WORKSHOP → se crea un Tenant nuevo a nombre del taller. Esto cumple
        el caso "una red de talleres = un tenant" sin obligar a un admin a
        provisionar el tenant antes.
      - TECNICO/ADMIN → no se permite auto-registro con esta función.
    """
    if payload.tenant_slug:
        slug = payload.tenant_slug.strip().lower()
        tenant = db.exec(select(Tenant).where(Tenant.slug == slug)).first()
        if not tenant or not tenant.activo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El tenant '{slug}' no existe o está inactivo.",
            )
        return tenant

    if role == UserRole.WORKSHOP:
        base_nombre = (payload.tenant_nombre or payload.full_name or payload.username).strip()
        base_slug = _slugify_tenant(base_nombre)
        # Resolver colisiones añadiendo sufijo numérico.
        slug_candidate = base_slug
        suffix = 1
        while db.exec(select(Tenant).where(Tenant.slug == slug_candidate)).first() is not None:
            suffix += 1
            slug_candidate = f"{base_slug}-{suffix}"
        tenant = Tenant(nombre=base_nombre or "Taller", slug=slug_candidate)
        db.add(tenant)
        db.flush()
        return tenant

    default = db.exec(select(Tenant).where(Tenant.slug == "default")).first()
    if not default:
        default = Tenant(nombre="Default", slug="default", descripcion="Tenant por defecto.")
        db.add(default)
        db.flush()
    return default


def create_user_for_role(
    *,
    db: Session,
    payload: UserRegister,
    role: UserRole,
) -> AuthResponse:
    tenant = _resolver_tenant_para_registro(db=db, payload=payload, role=role)
    user = User(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        full_name=(payload.full_name or "").strip() or None,
        role=role,
        is_active=True,
        hashed_password=get_password_hash(payload.password),
        tenant_id=tenant.id,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario o correo ya existe.",
        ) from exc

    db.refresh(user)
    return build_auth_response(user)


@router.post("/register/client", response_model=AuthResponse)
def register_client(payload: UserRegister, db: Session = Depends(get_session)):
    return create_user_for_role(db=db, payload=payload, role=UserRole.DRIVER)


@router.post("/register/workshop", response_model=AuthResponse)
def register_workshop(payload: UserRegister, db: Session = Depends(get_session)):
    return create_user_for_role(db=db, payload=payload, role=UserRole.WORKSHOP)


@router.post("/login", response_model=AuthResponse)
def login(db: Session = Depends(get_session), form_data: OAuth2PasswordRequestForm = Depends()):
    statement = select(User).where(User.username == form_data.username)
    user = db.exec(statement).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return build_auth_response(user)


@router.post("/login/admin", response_model=AuthResponse)
def login_admin(payload: LoginAdminPayload, db: Session = Depends(get_session)):
    identifier = (payload.email or payload.username or "").strip().lower()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingresa tu correo.",
        )

    user = db.exec(select(User).where(User.email == identifier)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )
    if user.role not in {UserRole.ADMIN, UserRole.WORKSHOP}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta no es administrativa. Usa Login Trabajadores.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta inactiva.")
    return build_auth_response(user)


@router.post("/login/client", response_model=AuthResponse)
def login_client(payload: LoginClientPayload, db: Session = Depends(get_session)):
    identifier = (payload.email or payload.username or "").strip().lower()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingresa tu correo.",
        )

    user = db.exec(select(User).where(User.email == identifier)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )
    if user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta no es de usuario cliente. Usa el login correspondiente.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta inactiva.")
    return build_auth_response(user)


@router.post("/login/worker", response_model=AuthResponse)
def login_worker(payload: LoginWorkerPayload, db: Session = Depends(get_session)):
    taller = db.get(Taller, payload.taller_id)
    if not taller or not taller.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Taller no encontrado o inactivo.")

    identifier = payload.username.strip().lower()
    user = db.exec(
        select(User).where(
            or_(
                User.username == payload.username.strip(),
                User.email == identifier,
            )
        )
    ).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos.",
        )
    if user.role != UserRole.TECNICO:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta cuenta no es de trabajador.")
    if user.tenant_id != taller.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no pertenece al taller seleccionado.",
        )

    tecnico = db.exec(
        select(Tecnico)
        .where(Tecnico.id_usuario == user.id)
        .where(Tecnico.taller_id == taller.id)
        .where(Tecnico.tenant_id == taller.tenant_id)
    ).first()
    if not tecnico or not tecnico.activo or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El trabajador no esta activo en este taller.",
        )
    return build_auth_response(user)


@router.post("/refresh", response_model=AuthResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_session)):
    token_payload = verify_refresh_token(payload.refresh_token)
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido o expirado.",
        )

    user_id = token_payload.get("user_id")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido o expirado.",
        ) from exc

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no disponible.",
        )

    return build_auth_response(user)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_session)):
    email = payload.email.strip().lower()
    if not email:
        return MessageResponse(message=FORGOT_PASSWORD_RESPONSE)

    statement = select(User).where(User.email == email)
    user = db.exec(statement).first()

    if user:
        if user.role == UserRole.TECNICO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=TECNICO_FORGOT_PASSWORD_RESPONSE,
            )
        token = create_password_reset_token(user.email)
        reset_url = f"{FRONTEND_BASE_URL}/reset-password?token={token}"
        send_password_reset_email(user.email, reset_url)

    return MessageResponse(message=FORGOT_PASSWORD_RESPONSE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_session)):
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe tener al menos 6 caracteres.",
        )

    email = verify_password_reset_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de recuperación es inválido o expiró.",
        )

    statement = select(User).where(User.email == email)
    user = db.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de recuperación es inválido o expiró.",
        )

    if user.role == UserRole.TECNICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=TECNICO_FORGOT_PASSWORD_RESPONSE,
        )

    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()

    return MessageResponse(message="La contraseña fue actualizada correctamente.")


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if payload.username is not None:
        current_user.username = payload.username.strip()
    if payload.email is not None:
        current_user.email = payload.email.strip().lower()
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip() or None
    if payload.telefono is not None:
        current_user.telefono = payload.telefono.strip() or None
    if payload.foto_url is not None:
        current_user.foto_url = payload.foto_url.strip() or None
    if payload.contacto_emergencia is not None:
        current_user.contacto_emergencia = payload.contacto_emergencia.strip() or None

    db.add(current_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar el perfil. Verifica usuario y correo.",
        ) from exc

    db.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.post("/me/foto", response_model=UserRead)
async def upload_me_foto(
    foto: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not foto.content_type or not foto.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes subir una imagen valida.",
        )
    current_user.foto_url = await save_upload_file(
        upload=foto,
        category="profile",
        prefix=f"user-{current_user.id}",
    )
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return UserRead.model_validate(current_user)
