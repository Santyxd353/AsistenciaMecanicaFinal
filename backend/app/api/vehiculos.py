from __future__ import annotations

from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    Solicitud,
    Taller,
    Tecnico,
    Vehiculo,
    VehiculoCreate,
    VehiculoHistorialCreate,
    VehiculoHistorialRead,
    VehiculoHistorialReparacion,
    VehiculoRead,
    VehiculoUpdate,
)
from app.models.user import User, UserRole
from app.services.ai import analyze_vehicle_photos
from app.services.audit import registrar_auditoria
from app.services.storage import delete_relative_url, save_upload_file, url_to_path

router = APIRouter()


class VehiclePreviewRead(BaseModel):
    placa: str = ""
    marca: str = ""
    modelo: str = ""
    anio: int | None = None
    color: str = ""
    resumen: str
    source: str


def _taller_del_usuario(session: Session, user: User) -> Taller | None:
    return session.exec(select(Taller).where(Taller.propietario_id == user.id)).first()


def _tecnico_del_usuario(session: Session, user: User) -> Tecnico | None:
    return session.exec(select(Tecnico).where(Tecnico.id_usuario == user.id)).first()


def _vehiculo_visible_para_usuario(
    session: Session,
    vehiculo: Vehiculo,
    current_user: User,
) -> bool:
    if current_user.role == UserRole.ADMIN:
        return current_user.tenant_id is None or vehiculo.tenant_id == current_user.tenant_id

    if current_user.role == UserRole.DRIVER:
        return (
            vehiculo.propietario_id == current_user.id
            and vehiculo.tenant_id == current_user.tenant_id
        )

    if current_user.role == UserRole.WORKSHOP:
        taller = _taller_del_usuario(session, current_user)
        if not taller:
            return False
        return session.exec(
            select(Solicitud)
            .where(Solicitud.vehiculo_id == vehiculo.id)
            .where(Solicitud.taller_id == taller.id)
        ).first() is not None

    if current_user.role == UserRole.TECNICO:
        tecnico = _tecnico_del_usuario(session, current_user)
        if not tecnico:
            return False
        return session.exec(
            select(Solicitud)
            .where(Solicitud.vehiculo_id == vehiculo.id)
            .where(Solicitud.tecnico_id == tecnico.id)
        ).first() is not None

    return False


def _puede_escribir_historial(
    session: Session,
    vehiculo: Vehiculo,
    current_user: User,
    solicitud_id: int | None,
) -> tuple[bool, int | None, int | None]:
    if current_user.role == UserRole.ADMIN:
        return True, None, None

    taller = _taller_del_usuario(session, current_user) if current_user.role == UserRole.WORKSHOP else None
    tecnico = _tecnico_del_usuario(session, current_user) if current_user.role == UserRole.TECNICO else None

    stmt = select(Solicitud).where(Solicitud.vehiculo_id == vehiculo.id)
    if solicitud_id is not None:
        stmt = stmt.where(Solicitud.id == solicitud_id)
    if taller:
        stmt = stmt.where(Solicitud.taller_id == taller.id)
    elif tecnico:
        stmt = stmt.where(Solicitud.tecnico_id == tecnico.id)
    else:
        return False, None, None

    solicitud = session.exec(stmt).first()
    if not solicitud:
        return False, None, None
    return True, solicitud.taller_id, solicitud.tecnico_id


def _historial_read(session: Session, item: VehiculoHistorialReparacion) -> VehiculoHistorialRead:
    data = VehiculoHistorialRead.model_validate(item)
    taller_nombre = None
    tecnico_nombre = None
    solicitud_estado = None
    if item.taller_id:
        taller = session.get(Taller, item.taller_id)
        taller_nombre = taller.nombre_comercial if taller else None
    if item.tecnico_id:
        tecnico = session.get(Tecnico, item.tecnico_id)
        tecnico_nombre = tecnico.nombre if tecnico else None
    if item.solicitud_id:
        solicitud = session.get(Solicitud, item.solicitud_id)
        solicitud_estado = solicitud.estado.value if solicitud and hasattr(solicitud.estado, "value") else (
            str(solicitud.estado) if solicitud else None
        )
    return data.model_copy(update={
        "taller_nombre": taller_nombre,
        "tecnico_nombre": tecnico_nombre,
        "solicitud_estado": solicitud_estado,
    })


async def _read_vehicle_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        return {
            "placa": str(form.get("placa", "")).strip(),
            "marca": str(form.get("marca", "")).strip(),
            "modelo": str(form.get("modelo", "")).strip(),
            "color": str(form.get("color", "")).strip() or None,
        }

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="No se pudo leer el payload del vehiculo.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload invalido para vehiculo.")
    return payload


@router.post("/preview-from-photo", response_model=VehiclePreviewRead)
async def previsualizar_vehiculo_desde_fotos(
    *,
    fotos: list[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
):
    if not fotos:
        raise HTTPException(status_code=400, detail="Debes enviar al menos una foto del vehiculo.")

    saved_paths: list[str] = []
    relative_urls: list[str] = []
    original_names = [foto.filename or "" for foto in fotos[:4]]
    try:
        for index, foto in enumerate(fotos[:4], start=1):
            relative_url = await save_upload_file(
                upload=foto,
                category="vehicle-preview",
                prefix=f"{current_user.id}-preview-{index}",
            )
            relative_urls.append(relative_url)
            local_path = url_to_path(relative_url)
            if local_path:
                saved_paths.append(str(local_path))

        analysis = analyze_vehicle_photos(image_paths=saved_paths, file_names=original_names)
        return VehiclePreviewRead(
            placa=analysis.placa,
            marca=analysis.marca,
            modelo=analysis.modelo,
            anio=analysis.anio,
            color=analysis.color,
            resumen=analysis.resumen,
            source=analysis.source,
        )
    except Exception as exc:
        return VehiclePreviewRead(
            placa="",
            marca="",
            modelo="",
            anio=None,
            color="",
            resumen=f"No se pudo analizar automaticamente: {exc}. Completa los datos manualmente.",
            source="safe-error",
        )
    finally:
        for relative_url in relative_urls:
            delete_relative_url(relative_url)


@router.post("/", response_model=VehiculoRead)
async def crear_vehiculo(
    request: Request,
    *,
    session: Session = Depends(get_session),
    foto: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
):
    payload = await _read_vehicle_payload(request)
    vehiculo_in = VehiculoCreate.model_validate(payload)
    vehiculo = Vehiculo.model_validate(vehiculo_in)
    vehiculo.placa = vehiculo.placa.strip().upper()
    if not vehiculo.placa:
        raise HTTPException(status_code=400, detail="La placa es obligatoria.")
    duplicado = session.exec(
        select(Vehiculo)
        .where(Vehiculo.tenant_id == current_user.tenant_id)
        .where(Vehiculo.placa == vehiculo.placa)
    ).first()
    if duplicado:
        raise HTTPException(status_code=400, detail="Ya existe un vehiculo con esa placa en tu tenant.")
    vehiculo.propietario_id = current_user.id
    vehiculo.tenant_id = current_user.tenant_id
    session.add(vehiculo)

    if foto:
        # El backend actual no persiste foto_url en el modelo, pero aceptamos el archivo
        # para mantener compatibilidad con clientes que envian multipart.
        await foto.read()

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo registrar el vehiculo. Verifica que la placa no este duplicada.",
        ) from exc

    session.refresh(vehiculo)
    return vehiculo


@router.get("/", response_model=List[VehiculoRead])
def listar_vehiculos(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Vehiculo)
        .where(Vehiculo.propietario_id == current_user.id)
        .where(Vehiculo.tenant_id == current_user.tenant_id)
        .offset(skip)
        .limit(limit)
    )
    vehiculos = session.exec(statement).all()
    return vehiculos


@router.get("/{vehiculo_id}/historial", response_model=List[VehiculoHistorialRead])
def listar_historial_vehiculo(
    *,
    session: Session = Depends(get_session),
    vehiculo_id: int,
    current_user: User = Depends(get_current_user),
):
    vehiculo = session.get(Vehiculo, vehiculo_id)
    if not vehiculo or not _vehiculo_visible_para_usuario(session, vehiculo, current_user):
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")

    historial = session.exec(
        select(VehiculoHistorialReparacion)
        .where(VehiculoHistorialReparacion.vehiculo_id == vehiculo.id)
        .order_by(VehiculoHistorialReparacion.fecha_servicio.desc())
    ).all()
    return [_historial_read(session, item) for item in historial]


@router.post(
    "/{vehiculo_id}/historial",
    response_model=VehiculoHistorialRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_historial_vehiculo(
    *,
    session: Session = Depends(get_session),
    vehiculo_id: int,
    payload: VehiculoHistorialCreate,
    current_user: User = Depends(get_current_user),
):
    vehiculo = session.get(Vehiculo, vehiculo_id)
    if not vehiculo or not _vehiculo_visible_para_usuario(session, vehiculo, current_user):
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")

    puede_escribir, taller_id, tecnico_id = _puede_escribir_historial(
        session,
        vehiculo,
        current_user,
        payload.solicitud_id,
    )
    if not puede_escribir:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el taller o mecanico asignado pueden registrar historial tecnico.",
        )

    if payload.costo is not None and payload.costo < 0:
        raise HTTPException(status_code=400, detail="El costo no puede ser negativo.")
    if payload.kilometraje is not None and payload.kilometraje < 0:
        raise HTTPException(status_code=400, detail="El kilometraje no puede ser negativo.")

    item = VehiculoHistorialReparacion(
        vehiculo_id=vehiculo.id or 0,
        solicitud_id=payload.solicitud_id,
        taller_id=taller_id,
        tecnico_id=tecnico_id,
        tenant_id=current_user.tenant_id or vehiculo.tenant_id,
        titulo=(payload.titulo or "Atencion mecanica").strip(),
        diagnostico=(payload.diagnostico or "").strip() or None,
        acciones_realizadas=(payload.acciones_realizadas or "").strip() or None,
        categoria=(payload.categoria or "").strip() or None,
        prioridad=(payload.prioridad or "").strip() or None,
        costo=payload.costo,
        estado_pago=payload.estado_pago or "pendiente",
        kilometraje=payload.kilometraje,
        observaciones=(payload.observaciones or "").strip() or None,
        fecha_servicio=datetime.utcnow(),
    )
    session.add(item)
    registrar_auditoria(
        session,
        actor=current_user,
        accion="vehiculo_historial_creado",
        entidad="vehiculo",
        entidad_id=vehiculo.id,
        detalle=f"Historial tecnico creado para placa {vehiculo.placa}.",
    )
    session.commit()
    session.refresh(item)
    return _historial_read(session, item)


@router.get("/{vehiculo_id}", response_model=VehiculoRead)
def obtener_vehiculo(
    *,
    session: Session = Depends(get_session),
    vehiculo_id: int,
    current_user: User = Depends(get_current_user),
):
    vehiculo = session.get(Vehiculo, vehiculo_id)
    if (
        not vehiculo
        or vehiculo.propietario_id != current_user.id
        or vehiculo.tenant_id != current_user.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")
    return vehiculo


@router.put("/{vehiculo_id}", response_model=VehiculoRead)
async def actualizar_vehiculo(
    request: Request,
    *,
    session: Session = Depends(get_session),
    vehiculo_id: int,
    foto: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
):
    vehiculo = session.get(Vehiculo, vehiculo_id)
    if (
        not vehiculo
        or vehiculo.propietario_id != current_user.id
        or vehiculo.tenant_id != current_user.tenant_id
    ):
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")

    payload = await _read_vehicle_payload(request)
    vehiculo_in = VehiculoUpdate.model_validate(payload)
    update_data = vehiculo_in.model_dump(exclude_unset=True)
    if "placa" in update_data and update_data["placa"] is not None:
        placa = str(update_data["placa"]).strip().upper()
        if not placa:
            raise HTTPException(status_code=400, detail="La placa es obligatoria.")
        duplicado = session.exec(
            select(Vehiculo)
            .where(Vehiculo.tenant_id == current_user.tenant_id)
            .where(Vehiculo.placa == placa)
            .where(Vehiculo.id != vehiculo.id)
        ).first()
        if duplicado:
            raise HTTPException(status_code=400, detail="Ya existe un vehiculo con esa placa en tu tenant.")
        update_data["placa"] = placa
    for field, value in update_data.items():
        setattr(vehiculo, field, value)

    if foto:
        await foto.read()

    session.add(vehiculo)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se pudo actualizar el vehiculo. Verifica que la placa no este duplicada.",
        ) from exc

    session.refresh(vehiculo)
    return vehiculo
