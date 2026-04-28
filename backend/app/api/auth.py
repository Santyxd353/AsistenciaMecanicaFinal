import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_password_reset_token,
    get_password_hash,
    verify_password_reset_token,
    verify_password,
)
from app.db.session import get_session
from app.models.user import (
    AuthResponse,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    User,
    UserRead,
    UserRegister,
    UserRole,
    UserUpdate,
)
from app.services.password_reset_delivery import send_password_reset_email

router = APIRouter()
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:4200").rstrip("/")
FORGOT_PASSWORD_RESPONSE = (
    "Si el correo existe, te enviamos instrucciones para restablecer la contraseña."
)
TECNICO_FORGOT_PASSWORD_RESPONSE = (
    "Usted no tiene autorización para poder solicitar recuperación de contraseña"
)


def build_auth_response(user: User) -> AuthResponse:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id},
        expires_delta=access_token_expires,
    )
    return AuthResponse(
        access_token=access_token,
        role=user.role,
        user=UserRead.model_validate(user),
    )


def create_user_for_role(
    *,
    db: Session,
    payload: UserRegister,
    role: UserRole,
) -> AuthResponse:
    user = User(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        full_name=(payload.full_name or "").strip() or None,
        role=role,
        is_active=True,
        hashed_password=get_password_hash(payload.password),
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
