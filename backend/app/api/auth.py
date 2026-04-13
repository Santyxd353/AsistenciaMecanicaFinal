from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_session
from app.models.user import AuthResponse, User, UserRead, UserRegister, UserRole, UserUpdate

router = APIRouter()


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
