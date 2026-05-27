from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from app.models.domain import (
    EstadoCandidato,
    EstadoSolicitud,
    Solicitud,
    SolicitudCandidato,
    Taller,
    Tecnico,
)

RADIO_MAXIMO_KM = 35.0
MAX_CANDIDATOS = 12


@dataclass(frozen=True)
class TallerScore:
    taller: Taller
    score: float
    distancia_km: float
    eta_minutos: int
    razon: str


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def normalizar_texto(texto: Optional[str]) -> str:
    if not texto:
        return ""
    limpio = unicodedata.normalize("NFKD", texto)
    limpio = "".join(caracter for caracter in limpio if not unicodedata.combining(caracter))
    return " ".join(limpio.casefold().split())


def palabras_clave_solicitud(solicitud: Solicitud) -> list[str]:
    texto = normalizar_texto(
        f"{solicitud.especialidad_requerida_ia or ''} "
        f"{solicitud.clasificacion_ia or ''} {solicitud.descripcion or ''}"
    )
    if any(item in texto for item in ["bateria", "electrico", "arranque", "alternador"]):
        return ["bateria", "electrico", "electricidad", "arranque"]
    if any(item in texto for item in ["llanta", "neumatico", "pinchazo", "pinchada", "rueda"]):
        return ["llanta", "neumatico", "vulcanizacion", "rueda"]
    if any(item in texto for item in ["choque", "colision", "accidente", "golpe", "grua"]):
        return ["choque", "colision", "carroceria", "grua"]
    if any(item in texto for item in ["motor", "recalentamiento", "humo", "radiador"]):
        return ["motor", "mecanica", "recalentamiento", "radiador"]
    if any(item in texto for item in ["llave", "cerrajeria", "cerradura"]):
        return ["cerrajeria", "llave", "cerradura"]
    return ["general", "mecanica", "auxilio"]


def prioridad_peso(prioridad: Optional[str]) -> float:
    prioridad_normalizada = normalizar_texto(prioridad)
    if prioridad_normalizada == "alta":
        return 18.0
    if prioridad_normalizada == "media":
        return 9.0
    return 3.0


def eta_desde_distancia(distancia_km: float) -> int:
    return max(6, min(120, int(round(distancia_km * 2.8 + 8))))


def talleres_activos(session: Session, tenant_id: int | None) -> list[Taller]:
    statement = select(Taller).where(Taller.activo == True)
    if tenant_id is not None:
        statement = statement.where(Taller.tenant_id == tenant_id)
    return session.exec(statement).all()


def tecnicos_disponibles_taller(
    session: Session,
    taller_id: int,
    tenant_id: int | None,
) -> list[Tecnico]:
    statement = (
        select(Tecnico)
        .where(Tecnico.taller_id == taller_id)
        .where(Tecnico.activo == True)
        .where(Tecnico.disponible == True)
    )
    if tenant_id is not None:
        statement = statement.where(Tecnico.tenant_id == tenant_id)
    return session.exec(statement).all()


def especialidad_match(taller: Taller, solicitud: Solicitud) -> bool:
    especialidades = [normalizar_texto(item.nombre) for item in taller.especialidades]
    if not especialidades:
        return True
    palabras = palabras_clave_solicitud(solicitud)
    return any(
        palabra in especialidad or especialidad in {"general", "mecanica", "mecanica general"}
        for especialidad in especialidades
        for palabra in palabras
    )


def score_taller(session: Session, taller: Taller, solicitud: Solicitud) -> TallerScore | None:
    if solicitud.tenant_id is not None and taller.tenant_id != solicitud.tenant_id:
        return None

    tecnicos_libres = tecnicos_disponibles_taller(
        session,
        taller.id or 0,
        solicitud.tenant_id,
    )
    carga_statement = (
        select(Solicitud)
        .where(Solicitud.taller_id == taller.id)
        .where(Solicitud.estado.notin_([
            EstadoSolicitud.RESUELTA,
            EstadoSolicitud.CANCELADA,
            EstadoSolicitud.FINALIZADO,
            EstadoSolicitud.CANCELADO,
        ]))
    )
    if solicitud.tenant_id is not None:
        carga_statement = carga_statement.where(Solicitud.tenant_id == solicitud.tenant_id)
    carga_abierta = session.exec(carga_statement).all()

    capacidad = max(1, taller.capacidad_operativa or 1)
    if len(carga_abierta) >= capacidad and not tecnicos_libres:
        return None

    if taller.latitud is None or taller.longitud is None:
        distancia = 30.0
    else:
        distancia = haversine_km(solicitud.latitud, solicitud.longitud, taller.latitud, taller.longitud)

    if distancia > RADIO_MAXIMO_KM:
        return None

    compatible = especialidad_match(taller, solicitud)
    if not compatible:
        return None

    eta = eta_desde_distancia(distancia)
    distancia_score = max(0.0, 35.0 - distancia)
    disponibilidad_score = min(len(tecnicos_libres), capacidad) * 12.0
    capacidad_score = max(0.0, capacidad - len(carga_abierta)) * 6.0
    especialidad_score = 20.0 if compatible else 0.0
    reputacion_score = min(5.0, taller.calificacion_promedio or 0.0) * 3.0
    score = (
        distancia_score
        + disponibilidad_score
        + capacidad_score
        + especialidad_score
        + reputacion_score
        + prioridad_peso(solicitud.prioridad_ia)
    )

    razon = (
        f"distancia={distancia:.1f}km, eta={eta}min, "
        f"tecnicos_libres={len(tecnicos_libres)}, capacidad={capacidad}"
    )
    return TallerScore(taller=taller, score=round(score, 2), distancia_km=round(distancia, 2), eta_minutos=eta, razon=razon)


def generar_candidatos(session: Session, solicitud: Solicitud) -> list[SolicitudCandidato]:
    existentes = session.exec(
        select(SolicitudCandidato)
        .where(SolicitudCandidato.solicitud_id == solicitud.id)
        .where(SolicitudCandidato.tenant_id == solicitud.tenant_id)
    ).all()
    for candidato in existentes:
        session.delete(candidato)
    session.flush()

    scores = [
        score
        for taller in talleres_activos(session, solicitud.tenant_id)
        if (score := score_taller(session, taller, solicitud)) is not None
    ]
    scores.sort(key=lambda item: item.score, reverse=True)

    candidatos: list[SolicitudCandidato] = []
    for index, item in enumerate(scores[:MAX_CANDIDATOS], start=1):
        candidato = SolicitudCandidato(
            solicitud_id=solicitud.id or 0,
            taller_id=item.taller.id or 0,
            tenant_id=solicitud.tenant_id,
            posicion=index,
            score=item.score,
            distancia_km=item.distancia_km,
            eta_minutos=item.eta_minutos,
            estado=EstadoCandidato.NOTIFICADO if index == 1 else EstadoCandidato.PENDIENTE,
            razon=item.razon,
        )
        session.add(candidato)
        candidatos.append(candidato)

    if candidatos:
        mejor = candidatos[0]
        solicitud.distancia_estimada_km = mejor.distancia_km
        solicitud.tiempo_estimado_minutos = mejor.eta_minutos
        solicitud.asignacion_score = mejor.score
        if solicitud.estado == EstadoSolicitud.PENDIENTE:
            solicitud.estado = EstadoSolicitud.BUSCANDO_TALLER
        session.add(solicitud)

    session.flush()
    return candidatos


def siguiente_candidato(session: Session, solicitud: Solicitud) -> SolicitudCandidato | None:
    return session.exec(
        select(SolicitudCandidato)
        .where(SolicitudCandidato.solicitud_id == solicitud.id)
        .where(SolicitudCandidato.tenant_id == solicitud.tenant_id)
        .where(SolicitudCandidato.estado.in_([EstadoCandidato.PENDIENTE, EstadoCandidato.NOTIFICADO]))
        .order_by(SolicitudCandidato.posicion)
    ).first()


def marcar_candidato(
    session: Session,
    solicitud: Solicitud,
    taller_id: int,
    estado: EstadoCandidato,
    razon: str | None = None,
) -> SolicitudCandidato | None:
    candidato = session.exec(
        select(SolicitudCandidato)
        .where(SolicitudCandidato.solicitud_id == solicitud.id)
        .where(SolicitudCandidato.taller_id == taller_id)
        .where(SolicitudCandidato.tenant_id == solicitud.tenant_id)
    ).first()
    if not candidato:
        return None
    candidato.estado = estado
    candidato.razon = razon or candidato.razon
    session.add(candidato)
    session.flush()
    return candidato
