from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import Vehiculo, VehiculoCreate, VehiculoRead, VehiculoUpdate
from app.models.user import User
from app.services.ai import analyze_vehicle_photos
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
    vehiculo.propietario_id = current_user.id
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
        .offset(skip)
        .limit(limit)
    )
    vehiculos = session.exec(statement).all()
    return vehiculos


@router.get("/{vehiculo_id}", response_model=VehiculoRead)
def obtener_vehiculo(
    *,
    session: Session = Depends(get_session),
    vehiculo_id: int,
    current_user: User = Depends(get_current_user),
):
    vehiculo = session.get(Vehiculo, vehiculo_id)
    if not vehiculo or vehiculo.propietario_id != current_user.id:
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
    if not vehiculo or vehiculo.propietario_id != current_user.id:
        raise HTTPException(status_code=404, detail="Vehiculo no encontrado")

    payload = await _read_vehicle_payload(request)
    vehiculo_in = VehiculoUpdate.model_validate(payload)
    update_data = vehiculo_in.model_dump(exclude_unset=True)
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
