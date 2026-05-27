"""Dependencias compartidas de FastAPI.

`get_current_user` valida el JWT y devuelve el `User` correspondiente.

`get_tenant_id` extrae el `tenant_id` del usuario autenticado. ADMIN sin
tenant devuelve `None` (acceso global). El resto de roles que llegue con
`tenant_id == None` se considera un estado inválido y se rechaza con 403.

`tenant_scope` es una utilidad para aplicar `WHERE tenant_id = ?` a una
sentencia SQLModel cuando el usuario tiene tenant asignado, o no filtrar
cuando es admin global.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session

from app.core.security import ALGORITHM, SECRET_KEY
from app.db.session import get_session
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("user_id")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = session.get(User, user_id)

    if not user:
        raise credentials_exception

    return user


def get_tenant_id(current_user: User = Depends(get_current_user)) -> Optional[int]:
    """Devuelve el tenant_id del usuario.

    * ADMIN sin tenant: devuelve None (admin global). El handler debe decidir
      si listar global o requerir ?tenant_id=.
    * Cualquier otro rol sin tenant: 403 (estado inválido — no debería ocurrir).
    """
    if current_user.tenant_id is None and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no tiene tenant asignado. Contacta al administrador.",
        )
    return current_user.tenant_id


def scope_by_tenant(stmt, model: Any, tenant_id: Optional[int]):
    """Aplica WHERE tenant_id = X si tenant_id no es None.

    Ejemplo:
        stmt = select(Solicitud)
        stmt = scope_by_tenant(stmt, Solicitud, tenant_id)
    """
    if tenant_id is None:
        return stmt
    return stmt.where(model.tenant_id == tenant_id)
