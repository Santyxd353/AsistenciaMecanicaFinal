import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.security import get_password_hash
from app.db.session import get_session
from app.models.domain import Especialidad, EspecialidadRead, Taller, Tecnico, TecnicoRead
from app.models.user import User, UserRole
from app.services.subscription_limits import ensure_can_create_mechanic

router = APIRouter()


class TecnicoIn(BaseModel):
    nombre: str
    email: str
    ci: str | None = None
    direccion: str | None = None
    especialidad_ids: list[int] = []
    especialidad: str | None = None
    disponible: bool = True
    activo: bool = True
    latitud: float | None = None
    longitud: float | None = None
    taller_id: int | None = None

    @field_validator("nombre")
    @classmethod
    def validar_texto_no_vacio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo es obligatorio")
        return value

    @field_validator("email")
    @classmethod
    def validar_email(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if not value:
            raise ValueError("El correo del mecánico es obligatorio.")
        # Regex pragmático suficiente para distinguir errores de tipeo. La
        # unicidad se verifica al insertar contra la BD.
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Ingresa un correo electrónico válido.")
        return value

    @field_validator("ci")
    @classmethod
    def validar_ci(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > 10:
            raise ValueError("El CI no puede exceder los 10 caracteres")
        return value

    @field_validator("direccion")
    @classmethod
    def validar_direccion(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("La dirección es obligatoria")
        return value


def obtener_taller_del_usuario(session: Session, current_user: User) -> Taller | None:
    return session.exec(
        select(Taller)
        .where(Taller.propietario_id == current_user.id)
        .where(Taller.tenant_id == current_user.tenant_id)
    ).first()


class TecnicoConvertirUsuarioIn(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def validar_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre de usuario es obligatorio")
        return value

    @field_validator("email")
    @classmethod
    def validar_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("El correo es obligatorio")
        return value

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return value


def _obtener_especialidades(
    session: Session,
    especialidad_ids: list[int]
) -> list[Especialidad]:
    ids_unicos = list(dict.fromkeys(especialidad_ids))
    if not ids_unicos:
        raise HTTPException(
            status_code=400,
            detail="Debes seleccionar al menos una especialidad"
        )

    especialidades = session.exec(
        select(Especialidad).where(Especialidad.id.in_(ids_unicos))
    ).all()

    if len(especialidades) != len(ids_unicos):
        raise HTTPException(
            status_code=400,
            detail="Una o más especialidades seleccionadas no existen"
        )

    especialidades_por_id = {especialidad.id: especialidad for especialidad in especialidades}
    return [especialidades_por_id[especialidad_id] for especialidad_id in ids_unicos]


def _obtener_o_crear_especialidad(session: Session, nombre: str) -> Especialidad:
    nombre_normalizado = nombre.strip() or "General"
    especialidad = session.exec(
        select(Especialidad).where(Especialidad.nombre == nombre_normalizado)
    ).first()
    if especialidad:
        return especialidad

    especialidad = Especialidad(nombre=nombre_normalizado)
    session.add(especialidad)
    session.flush()
    return especialidad


def _resolver_especialidades(session: Session, tecnico_in: TecnicoIn) -> list[Especialidad]:
    if tecnico_in.especialidad_ids:
        return _obtener_especialidades(session, tecnico_in.especialidad_ids)
    return [_obtener_o_crear_especialidad(session, tecnico_in.especialidad or "General")]


def _obtener_tecnico_con_especialidades(session: Session, tecnico_id: int) -> Tecnico | None:
    return session.exec(
        select(Tecnico)
        .options(selectinload(Tecnico.especialidades))
        .where(Tecnico.id == tecnico_id)
    ).first()


def _username_base(nombre: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", ".", nombre.lower()).strip(".")
    return cleaned or "mecanico"


def _username_unico(session: Session, nombre: str) -> str:
    base = _username_base(nombre)
    username = base
    counter = 1
    while session.exec(select(User).where(User.username == username)).first():
        counter += 1
        username = f"{base}{counter}"
    return username


def _password_temporal(ci: str) -> str:
    suffix = re.sub(r"[^0-9A-Za-z]", "", ci)[-4:] or secrets.token_hex(2)
    return f"Mec-{suffix}-{secrets.token_hex(2)}"


def _tecnico_read(
    session: Session,
    tecnico: Tecnico,
    password_temporal: str | None = None,
) -> TecnicoRead:
    """Arma la respuesta del mecanico incluyendo su usuario vinculado.

    `password_temporal` solo se entrega cuando acaba de crearse la cuenta. En
    listados posteriores no se puede recuperar porque el backend guarda hash,
    no contrasenas en claro.
    """
    usuario = session.get(User, tecnico.id_usuario) if tecnico.id_usuario else None
    return TecnicoRead(
        id=tecnico.id or 0,
        nombre=tecnico.nombre,
        ci=tecnico.ci or "",
        direccion=tecnico.direccion or "",
        latitud=tecnico.latitud,
        longitud=tecnico.longitud,
        latitud_actual=tecnico.latitud_actual,
        longitud_actual=tecnico.longitud_actual,
        ultima_actualizacion_ubicacion=tecnico.ultima_actualizacion_ubicacion,
        disponible=tecnico.disponible,
        activo=tecnico.activo,
        taller_id=tecnico.taller_id,
        id_usuario=tecnico.id_usuario,
        tenant_id=tecnico.tenant_id,
        calificacion_promedio=tecnico.calificacion_promedio or 0.0,
        total_calificaciones=tecnico.total_calificaciones or 0,
        especialidades=[
            EspecialidadRead(id=esp.id or 0, nombre=esp.nombre)
            for esp in (tecnico.especialidades or [])
        ],
        usuario_username=usuario.username if usuario else None,
        usuario_email=usuario.email if usuario else None,
        password_temporal=password_temporal,
    )


@router.get("/mi-perfil", response_model=TecnicoRead)
def obtener_mi_perfil_tecnico(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.TECNICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios tecnicos pueden consultar este perfil.",
        )

    tecnico = session.exec(
        select(Tecnico)
        .options(selectinload(Tecnico.especialidades))
        .where(Tecnico.id_usuario == current_user.id)
    ).first()

    if not tecnico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un perfil tecnico vinculado a este usuario.",
        )

    return _tecnico_read(session, tecnico)


@router.patch("/mi-disponibilidad", response_model=TecnicoRead)
def actualizar_mi_disponibilidad(
    *,
    disponible: bool,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.TECNICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los usuarios tecnicos pueden actualizar su disponibilidad.",
        )

    tecnico = session.exec(
        select(Tecnico).where(Tecnico.id_usuario == current_user.id)
    ).first()

    if not tecnico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un perfil tecnico vinculado a este usuario.",
        )

    tecnico.disponible = disponible
    session.add(tecnico)
    session.commit()

    tecnico_actualizado = _obtener_tecnico_con_especialidades(session, tecnico.id)
    if not tecnico_actualizado:
        raise HTTPException(status_code=500, detail="No se pudo cargar el tecnico actualizado")

    return _tecnico_read(session, tecnico_actualizado)

@router.post("/", response_model=TecnicoRead)
def crear_tecnico(
    *,
    session: Session = Depends(get_session),
    tecnico_in: TecnicoIn,
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ADMIN and tecnico_in.taller_id:
        taller = session.get(Taller, tecnico_in.taller_id)
    else:
        taller = obtener_taller_del_usuario(session, current_user)

    if not taller:
        raise HTTPException(status_code=400, detail="Debes tener un taller registrado para crear tecnicos")
    if current_user.tenant_id is not None and taller.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="No puedes crear tecnicos en otro tenant")
    if taller.tenant_id is not None:
        ensure_can_create_mechanic(session, taller.tenant_id)

    ci_value = tecnico_in.ci or f"AUTO{secrets.token_hex(3).upper()}"[:10]
    direccion_value = tecnico_in.direccion or "Pendiente"

    # El email lo provee el operador del taller — es el que el mecánico va a
    # usar para hacer login. Validamos unicidad acá para devolver un error
    # claro antes del INSERT (el constraint UNIQUE del schema sigue siendo
    # la red de seguridad).
    email_normalizado = tecnico_in.email
    existente_email = session.exec(
        select(User).where(User.email == email_normalizado)
    ).first()
    if existente_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cuenta con ese correo. Usa otro correo para este mecánico.",
        )

    username = _username_unico(session, tecnico_in.nombre)
    password_temporal = _password_temporal(ci_value)
    usuario = User(
        username=username,
        email=email_normalizado,
        full_name=tecnico_in.nombre,
        role=UserRole.TECNICO,
        is_active=tecnico_in.activo,
        tenant_id=taller.tenant_id,
        hashed_password=get_password_hash(password_temporal),
    )
    session.add(usuario)
    session.flush()

    tecnico = Tecnico(
        nombre=tecnico_in.nombre,
        ci=ci_value,
        direccion=direccion_value,
        disponible=tecnico_in.disponible,
        activo=tecnico_in.activo,
        latitud=tecnico_in.latitud,
        longitud=tecnico_in.longitud,
        id_usuario=usuario.id,
        taller_id=taller.id,
        tenant_id=taller.tenant_id,
    )
    tecnico.especialidades = _resolver_especialidades(session, tecnico_in)

    session.add(tecnico)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        # Diagnóstico fino del constraint violado. Antes devolvíamos siempre
        # "CI duplicado" aunque el problema fuera de username, email o FK,
        # lo cual escondía el error real al cliente y dejaba al usuario sin
        # forma de corregirlo.
        msg = str(getattr(exc, "orig", exc) or exc).lower()
        print(f"[crear_tecnico] IntegrityError: {msg}")
        if "tecnico_ci_key" in msg:
            detail = "El CI ya está registrado para otro técnico."
        elif "user_username_key" in msg:
            detail = "Conflicto con el usuario interno autogenerado. Reintenta."
        elif "user_email_key" in msg:
            detail = "Conflicto con el email interno autogenerado. Reintenta."
        elif "tecnico_id_usuario_key" in msg:
            detail = "Conflicto con la relación de usuario interno. Reintenta."
        else:
            detail = "No se pudo guardar el mecánico (violación de restricción)."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc
    tecnico_creado = _obtener_tecnico_con_especialidades(session, tecnico.id)
    if not tecnico_creado:
        raise HTTPException(status_code=500, detail="No se pudo cargar el técnico creado")
    return _tecnico_read(session, tecnico_creado, password_temporal=password_temporal)

@router.get("/", response_model=list[TecnicoRead])
def listar_tecnicos(
    *,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ADMIN:
        statement = (
            select(Tecnico)
            .options(selectinload(Tecnico.especialidades))
            .offset(skip)
            .limit(limit)
        )
        if current_user.tenant_id is not None:
            statement = statement.where(Tecnico.tenant_id == current_user.tenant_id)
        return [_tecnico_read(session, tecnico) for tecnico in session.exec(statement).all()]

    taller = obtener_taller_del_usuario(session, current_user)
    if not taller:
        return []

    tecnicos = session.exec(
        select(Tecnico)
        .options(selectinload(Tecnico.especialidades))
        .where(Tecnico.taller_id == taller.id)
        .where(Tecnico.tenant_id == taller.tenant_id)
        .offset(skip).limit(limit)
    ).all()
    return [_tecnico_read(session, tecnico) for tecnico in tecnicos]


@router.patch("/{tecnico_id}/disponibilidad", response_model=TecnicoRead)
def actualizar_disponibilidad(
    *,
    session: Session = Depends(get_session),
    tecnico_id: int,
    disponible: bool,
    current_user: User = Depends(get_current_user),
):
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="Tecnico no encontrado")

    if current_user.role == UserRole.ADMIN and current_user.tenant_id is not None and tecnico.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="No tienes permisos para modificar este tecnico")

    if current_user.role != UserRole.ADMIN:
        taller = obtener_taller_del_usuario(session, current_user)
        if not taller or tecnico.taller_id != taller.id or tecnico.tenant_id != taller.tenant_id:
            raise HTTPException(status_code=403, detail="No tienes permisos para modificar este tecnico")

    tecnico.disponible = disponible
    session.add(tecnico)
    session.commit()
    tecnico_actualizado = _obtener_tecnico_con_especialidades(session, tecnico.id)
    if not tecnico_actualizado:
        raise HTTPException(status_code=500, detail="No se pudo cargar el técnico actualizado")
    return _tecnico_read(session, tecnico_actualizado)

class TecnicoUpdate(BaseModel):
    nombre: str | None = None
    ci: str | None = None
    direccion: str | None = None
    especialidad_ids: list[int] | None = None
    disponible: bool | None = None
    activo: bool | None = None
    latitud: float | None = None
    longitud: float | None = None

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Este campo es obligatorio")
        return value

    @field_validator("ci")
    @classmethod
    def validar_ci(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("El CI es obligatorio")
        if len(value) > 10:
            raise ValueError("El CI no puede exceder los 10 caracteres")
        return value

    @field_validator("direccion")
    @classmethod
    def validar_direccion(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("La dirección es obligatoria")
        return value

@router.put("/{tecnico_id}", response_model=TecnicoRead)
def actualizar_tecnico(
    *,
    session: Session = Depends(get_session),
    tecnico_id: int,
    data: TecnicoUpdate,
    current_user: User = Depends(get_current_user)
):
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    taller = session.exec(
        select(Taller)
        .where(Taller.propietario_id == current_user.id)
        .where(Taller.tenant_id == current_user.tenant_id)
    ).first()

    if not taller or tecnico.taller_id != taller.id or tecnico.tenant_id != taller.tenant_id:
        raise HTTPException(status_code=403, detail="Sin permisos")

    update_data = data.model_dump(exclude_unset=True)
    especialidad_ids = update_data.pop("especialidad_ids", None)

    for key, value in update_data.items():
        setattr(tecnico, key, value)

    if especialidad_ids is not None:
        tecnico.especialidades = _obtener_especialidades(session, especialidad_ids)

    if tecnico.id_usuario is not None:
        usuario = session.get(User, tecnico.id_usuario)
        if usuario:
            usuario.is_active = tecnico.activo
            session.add(usuario)

    session.add(tecnico)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El CI ya está registrado para otro técnico.",
        ) from exc
    tecnico_actualizado = _obtener_tecnico_con_especialidades(session, tecnico.id)
    if not tecnico_actualizado:
        raise HTTPException(status_code=500, detail="No se pudo cargar el técnico actualizado")
    return _tecnico_read(session, tecnico_actualizado)


@router.post("/{tecnico_id}/convertir-a-usuario", response_model=TecnicoRead)
def convertir_tecnico_a_usuario(
    *,
    session: Session = Depends(get_session),
    tecnico_id: int,
    data: TecnicoConvertirUsuarioIn,
    current_user: User = Depends(get_current_user)
):
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    taller = session.exec(
        select(Taller)
        .where(Taller.propietario_id == current_user.id)
        .where(Taller.tenant_id == current_user.tenant_id)
    ).first()

    if not taller or tecnico.taller_id != taller.id or tecnico.tenant_id != taller.tenant_id:
        raise HTTPException(status_code=403, detail="Sin permisos")

    if tecnico.id_usuario is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El técnico ya está vinculado a un usuario del sistema.",
        )

    usuario = User(
        username=data.username.strip(),
        email=data.email.strip().lower(),
        full_name=tecnico.nombre,
        role=UserRole.TECNICO,
        is_active=tecnico.activo,
        tenant_id=taller.tenant_id,
        hashed_password=get_password_hash(data.password),
    )

    session.add(usuario)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo crear el usuario. Verifica que el usuario y correo sean únicos.",
        ) from exc

    session.refresh(usuario)
    tecnico.id_usuario = usuario.id
    session.add(tecnico)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo vincular el técnico con el usuario creado.",
        ) from exc

    tecnico_actualizado = _obtener_tecnico_con_especialidades(session, tecnico.id)
    if not tecnico_actualizado:
        raise HTTPException(status_code=500, detail="No se pudo cargar el técnico actualizado")
    return _tecnico_read(session, tecnico_actualizado, password_temporal=data.password)

@router.delete("/{tecnico_id}")
def eliminar_tecnico(
    *,
    session: Session = Depends(get_session),
    tecnico_id: int,
    current_user: User = Depends(get_current_user)
):
    tecnico = session.get(Tecnico, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=404, detail="No encontrado")

    taller = session.exec(
        select(Taller)
        .where(Taller.propietario_id == current_user.id)
        .where(Taller.tenant_id == current_user.tenant_id)
    ).first()

    if not taller or tecnico.taller_id != taller.id or tecnico.tenant_id != taller.tenant_id:
        raise HTTPException(status_code=403, detail="Sin permisos")

    session.delete(tecnico)
    session.commit()

    return {"ok": True}
