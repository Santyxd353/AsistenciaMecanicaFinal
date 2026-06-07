import os
from typing import Optional

import requests

from app.models.user import User


ONESIGNAL_API_URL = "https://api.onesignal.com/notifications"
REQUEST_TIMEOUT_SECONDS = 10


def _onesignal_ready() -> bool:
    app_id = os.getenv("ONESIGNAL_APP_ID", "").strip()
    api_key = os.getenv("ONESIGNAL_REST_API_KEY", "").strip()
    ready = bool(app_id and api_key)
    if not ready:
        print(
            "OneSignal deshabilitado: faltan ONESIGNAL_APP_ID o "
            "ONESIGNAL_REST_API_KEY."
        )
    return ready


def build_external_id(user: User) -> str:
    tenant_key = str(user.tenant_id) if user.tenant_id is not None else "global"
    return f"{tenant_key}:{user.id}"


def enviar_push_al_usuario(
    *,
    usuario: Optional[User],
    titulo: str,
    mensaje: str,
    solicitud_id: Optional[int] = None,
    tipo: Optional[str] = None,
    accion_url: Optional[str] = None,
) -> bool:
    if usuario is None or usuario.id is None:
        return False

    if not _onesignal_ready():
        return False

    app_id = os.getenv("ONESIGNAL_APP_ID", "").strip()
    api_key = os.getenv("ONESIGNAL_REST_API_KEY", "").strip()
    external_id = build_external_id(usuario)

    payload = {
        "app_id": app_id,
        "include_aliases": {"external_id": [external_id]},
        "target_channel": "push",
        "headings": {"en": titulo, "es": titulo},
        "contents": {"en": mensaje, "es": mensaje},
        "data": {
            "tipo": tipo or "general",
            "solicitud_id": str(solicitud_id or ""),
            "accion_url": accion_url or "",
            "external_id": external_id,
        },
    }

    if accion_url:
        payload["url"] = accion_url

    try:
        response = requests.post(
            ONESIGNAL_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Key {api_key}",
            },
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        print(
            f"No se pudo enviar push OneSignal al usuario {usuario.id} "
            f"({external_id}): {exc}"
        )
        return False

    if response.status_code >= 400:
        print(
            f"OneSignal rechazo el push para el usuario {usuario.id} "
            f"({external_id}): {response.status_code} {response.text}"
        )
        return False

    try:
        body = response.json()
    except ValueError:
        print(
            f"OneSignal devolvio una respuesta no JSON para el usuario {usuario.id} "
            f"({external_id})."
        )
        return False

    message_id = body.get("id")
    if not message_id:
        print(
            f"OneSignal acepto la solicitud pero no creo mensaje para el usuario "
            f"{usuario.id} ({external_id}): {body}"
        )
        return False

    recipients = body.get("recipients")
    errors = body.get("errors")
    print(
        f"OneSignal push enviado: message_id={message_id} "
        f"external_id={external_id} recipients={recipients} "
        f"tipo={tipo or 'general'} solicitud_id={solicitud_id or ''}"
    )
    if errors:
        print(
            f"OneSignal respondio con advertencias para external_id={external_id}: "
            f"{errors}"
        )

    return True
