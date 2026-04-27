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
from app.services.storage import delete_relative_url, save_upload_file, url_to_path
from app.services.ai import analyze_vehicle_photos

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
            "anio": int(str(form.get("anio", "")).strip()) if str(form.get("anio", "")).strip() else None,
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

        analysis = analyze_vehicle_photos(image_paths=saved_paths)
        return VehiclePreviewRead(
            placa=analysis.placa,
            marca=analysis.marca,
            modelo=analysis.modelo,
            anio=analysis.anio,
            color=analysis.color,
            resumen=analysis.resumen,
            source=analysis.source,
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

    saved_photo_url: str | None = None
    if foto and foto.filename:
        saved_photo_url = await save_upload_file(
            upload=foto,
            category="vehicles",
            prefix=f"{current_user.id}-{vehiculo.placa}",
        )
        vehiculo.foto_url = saved_photo_url

    session.add(vehiculo)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        delete_relative_url(saved_photo_url)
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

    old_photo_url = vehiculo.foto_url
    new_photo_url: str | None = None
    if foto and foto.filename:
        new_photo_url = await save_upload_file(
            upload=foto,
            category="vehicles",
            prefix=f"{current_user.id}-{vehiculo.placa}",
        )
        vehiculo.foto_url = new_photo_url

    session.add(vehiculo)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if new_photo_url:
            delete_relative_url(new_photo_url)
        raise HTTPException(
            status_code=400,
            detail="No se pudo actualizar el vehiculo. Verifica que la placa no este duplicada.",
        ) from exc

    if new_photo_url and old_photo_url and old_photo_url != new_photo_url:
        delete_relative_url(old_photo_url)

    session.refresh(vehiculo)
    return vehiculo
