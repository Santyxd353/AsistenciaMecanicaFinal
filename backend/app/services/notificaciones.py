from typing import Iterable, Optional

from sqlmodel import Session

from app.models.domain import Notificacion, TipoNotificacion
from app.services.push_fcm import enviar_push_al_usuario


def crear_notificacion(
    session: Session,
    *,
    destinatario_id: int,
    tipo: TipoNotificacion,
    titulo: str,
    mensaje: str,
    solicitud_id: Optional[int] = None,
    accion_url: Optional[str] = None,
    commit: bool = False,
) -> Notificacion:
    notificacion = Notificacion(
        destinatario_id=destinatario_id,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        solicitud_id=solicitud_id,
        accion_url=accion_url,
    )
    session.add(notificacion)
    session.flush()

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
            )
        )

    return notificaciones
