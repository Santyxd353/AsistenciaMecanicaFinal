import os
from typing import Iterable, Optional

from sqlmodel import Session

from app.models.domain import Notificacion, TipoNotificacion
from app.models.user import User
from app.services.push_fcm import enviar_push_al_usuario
from app.services.push_onesignal import enviar_push_al_usuario as enviar_push_onesignal


def _legacy_fcm_fallback_enabled() -> bool:
    value = os.getenv("ENABLE_LEGACY_FCM_FALLBACK", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def crear_notificacion(
    session: Session,
    *,
    destinatario_id: int,
    tipo: TipoNotificacion,
    titulo: str,
    mensaje: str,
    solicitud_id: Optional[int] = None,
    accion_url: Optional[str] = None,
    tenant_id: Optional[int] = None,
    commit: bool = False,
) -> Notificacion:
    destinatario = session.get(User, destinatario_id)
    effective_tenant_id = tenant_id if tenant_id is not None else (
        destinatario.tenant_id if destinatario else None
    )
    notificacion = Notificacion(
        destinatario_id=destinatario_id,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        solicitud_id=solicitud_id,
        accion_url=accion_url,
        tenant_id=effective_tenant_id,
    )
    session.add(notificacion)
    session.flush()

    enviado_por_onesignal = enviar_push_onesignal(
        usuario=destinatario,
        titulo=titulo,
        mensaje=mensaje,
        solicitud_id=solicitud_id,
        tipo=tipo.value,
        accion_url=accion_url,
    )

    if not enviado_por_onesignal and _legacy_fcm_fallback_enabled():
        enviar_push_al_usuario(
            session,
            usuario_id=destinatario_id,
            titulo=titulo,
            mensaje=mensaje,
            solicitud_id=solicitud_id,
            tipo=tipo.value,
            accion_url=accion_url,
        )

    if commit:
        session.commit()
        session.refresh(notificacion)

    return notificacion


def crear_notificaciones_para_usuarios(
    session: Session,
    *,
    destinatario_ids: Iterable[int],
    tipo: TipoNotificacion,
    titulo: str,
    mensaje: str,
    solicitud_id: Optional[int] = None,
    accion_url: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> list[Notificacion]:
    notificaciones: list[Notificacion] = []
    ids_unicos = list(dict.fromkeys(destinatario_ids))

    for destinatario_id in ids_unicos:
        notificaciones.append(
            crear_notificacion(
                session,
                destinatario_id=destinatario_id,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                solicitud_id=solicitud_id,
                accion_url=accion_url,
                tenant_id=tenant_id,
            )
        )

    return notificaciones
