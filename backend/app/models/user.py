from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

class UserRole(str, Enum):
    DRIVER = "driver"
    TECNICO = "tecnico"
    WORKSHOP = "workshop"
    ADMIN = "admin"

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    role: UserRole = UserRole.DRIVER
    is_active: bool = True

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    
    vehiculos: List["Vehiculo"] = Relationship(back_populates="propietario")
    taller: Optional["Taller"] = Relationship(back_populates="propietario")
    tecnico_perfil: Optional["Tecnico"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"uselist": False}
    )

class UserCreate(UserBase):
    password: str


class UserRegister(SQLModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserRead(UserBase):
    id: int


class AuthResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user: UserRead


class PasswordResetRequest(SQLModel):
    email: str


class PasswordResetConfirm(SQLModel):
    token: str
    new_password: str


class MessageResponse(SQLModel):
    message: str
