import bcrypt
from datetime import datetime, timedelta
import os
from typing import Optional
from jose import JWTError, jwt
from app.models.user import User

# SECURITY: nunca dejar un default productivo aquí. En dev permitimos un valor
# auto-generado (no determinista, vive el tiempo del proceso) si la variable no
# está configurada, de forma que los tokens de un proceso no sean válidos en
# otro. En producción se DEBE definir SECRET_KEY por entorno.
_SECRET_KEY_RAW = os.getenv("SECRET_KEY")
if not _SECRET_KEY_RAW:
    import secrets as _secrets

    _SECRET_KEY_RAW = _secrets.token_urlsafe(48)
    print(
        "ADVERTENCIA: SECRET_KEY no configurada. Se generó una efímera para "
        "este proceso; los tokens emitidos no serán válidos tras un reinicio."
    )
SECRET_KEY = _SECRET_KEY_RAW
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30")
)
PASSWORD_RESET_SCOPE = "password_reset"
REFRESH_TOKEN_SCOPE = "refresh_token"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    # bcrypt.hashpw returns bytes, we decode to string for the database
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "scope": REFRESH_TOKEN_SCOPE})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_refresh_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    if payload.get("scope") != REFRESH_TOKEN_SCOPE:
        return None

    return payload


def create_password_reset_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": email,
        "scope": PASSWORD_RESET_SCOPE,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    if payload.get("scope") != PASSWORD_RESET_SCOPE:
        return None

    email = payload.get("sub")
    if not isinstance(email, str) or not email.strip():
        return None

    return email
