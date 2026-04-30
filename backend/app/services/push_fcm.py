import json
import os
from typing import Optional

from sqlmodel import Session, select

from app.models.domain import DispositivoToken


_firebase_ready: Optional[bool] = None


def _init_firebase() -> bool:
    global _firebase_ready
    if _firebase_ready is not None:
        return _firebase_ready

    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception as exc:
        print(f"FCM deshabilitado: firebase-admin no esta instalado ({exc}).")
        _firebase_ready = False
        return False

    try:
        if firebase_admin._apps:
            _firebase_ready = True
            return True

        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        service_account_path = (
            os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        options = {"projectId": project_id} if project_id else None

        if service_account_json:
            payload = json.loads(service_account_json)
            cred = credentials.Certificate(payload)
            firebase_admin.initialize_app(cred, options=options)
        elif service_account_path:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, options=options)
        else:
            # En Cloud Run puede funcionar con Application Default Credentials
            # si la cuenta de servicio tiene permisos sobre Firebase Cloud Messaging.
            firebase_admin.initialize_app(options=options)

        _firebase_ready = True
        return True
    except Exception as exc:
        print(f"FCM deshabilitado: no se pudo inicializar Firebase ({exc}).")
        _firebase_ready = False
        return False


def enviar_push_al_usuario(
    session: Session,
    *,
    usuario_id: int,
    titulo: str,
    mensaje: str,
    solicitud_id: Optional[int] = None,
    tipo: Optional[str] = None,
    accion_url: Optional[str] = None,
) -> None:
    if not _init_firebase():
        return

    try:
        from firebase_admin import exceptions, messaging
    except Exception as exc:
        print(f"FCM deshabilitado: no se pudo cargar messaging ({exc}).")
        return

    tokens = session.exec(
        select(DispositivoToken).where(
            DispositivoToken.usuario_id == usuario_id,
            DispositivoToken.activo == True,
        )
    ).all()

    if not tokens:
        return

    data = {
        "tipo": tipo or "general",
        "solicitud_id": str(solicitud_id or ""),
        "accion_url": accion_url or "",
    }

    for device in tokens:
        message = messaging.Message(
            token=device.token,
            notification=messaging.Notification(title=titulo, body=mensaje),
            data=data,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="asistencia_mecanica_alertas",
                    sound="default",
                ),
            ),
        )

        try:
            messaging.send(message)
        except exceptions.FirebaseError as exc:
            error_text = str(exc).lower()
            if "registration-token-not-registered" in error_text or "invalid" in error_text:
                device.activo = False
                session.add(device)
            print(f"No se pudo enviar push FCM al usuario {usuario_id}: {exc}")
        except Exception as exc:
            print(f"No se pudo enviar push FCM al usuario {usuario_id}: {exc}")

