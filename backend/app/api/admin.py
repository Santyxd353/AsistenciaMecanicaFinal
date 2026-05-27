"""Endpoints exclusivos del rol ADMIN: métricas globales y panel de gestión.

Decisiones:
* Las métricas se calculan on-demand contra Postgres (volumen pequeño en MVP).
  Para escalar habría que cachear o materializar en una vista.
* No se exponen datos sensibles (hashed_password) por defecto: el `UserRead`
  ya los excluye.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    AuditLog,
    EstadoSolicitud,
    Pago,
    Solicitud,
    Taller,
    TallerRead,
    Tecnico,
    Tenant,
)
from app.models.user import User, UserRead, UserRole


router = APIRouter()


def _solo_admin(current_user: User) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recurso reservado a administradores.",
        )


@router.get("/usuarios", response_model=List[UserRead])
def listar_usuarios(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    role: Optional[UserRole] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _solo_admin(current_user)
    stmt = select(User).offset(max(skip, 0)).limit(limit)
    if role is not None:
        stmt = stmt.where(User.role == role)
    return [UserRead.model_validate(item) for item in session.exec(stmt).all()]


@router.patch("/usuarios/{user_id}/activo", response_model=UserRead)
def toggle_usuario_activo(
    user_id: int,
    activo: bool,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _solo_admin(current_user)
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propio usuario.")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user.is_active = activo
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserRead.model_validate(user)


@router.get("/talleres", response_model=List[TallerRead])
def listar_talleres_global(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _solo_admin(current_user)
    talleres = session.exec(select(Taller).offset(max(skip, 0)).limit(limit)).all()
    out: list[TallerRead] = []
    for taller in talleres:
        data = TallerRead.model_validate(taller)
        out.append(data.model_copy(update={"especialidades": [
            {"id": esp.id, "nombre": esp.nombre} for esp in (taller.especialidades or [])
        ]}))
    return out


@router.get("/metricas")
def metricas_globales(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """KPIs para el panel admin: usuarios, solicitudes por estado, ingresos."""
    _solo_admin(current_user)

    total_usuarios = len(session.exec(select(User)).all())
    total_talleres = len(session.exec(select(Taller)).all())
    total_tecnicos = len(session.exec(select(Tecnico)).all())

    solicitudes = session.exec(select(Solicitud)).all()
    por_estado: dict[str, int] = {}
    for solicitud in solicitudes:
        clave = (solicitud.estado.value if hasattr(solicitud.estado, "value") else str(solicitud.estado))
        por_estado[clave] = por_estado.get(clave, 0) + 1

    pagos = session.exec(select(Pago).where(Pago.estado == "pagado")).all()
    ingresos_totales = round(sum(item.monto for item in pagos), 2)
    comision_total = round(sum(item.comision_plataforma for item in pagos), 2)

    hace_7d = datetime.utcnow() - timedelta(days=7)
    solicitudes_7d = [item for item in solicitudes if item.fecha_creacion and item.fecha_creacion >= hace_7d]

    return {
        "usuarios": {
            "total": total_usuarios,
            "talleres": total_talleres,
            "tecnicos": total_tecnicos,
        },
        "solicitudes": {
            "total": len(solicitudes),
            "ultimos_7_dias": len(solicitudes_7d),
            "por_estado": por_estado,
        },
        "ingresos": {
            "total_cobrado": ingresos_totales,
            "comision_plataforma": comision_total,
            "neto_talleres": round(ingresos_totales - comision_total, 2),
        },
    }


@router.get("/super-dashboard")
def super_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Resumen completo para superadmin: toda la plataforma, sin scope tenant."""
    _solo_admin(current_user)

    tenants = session.exec(select(Tenant).order_by(Tenant.id)).all()
    users = session.exec(select(User).order_by(User.id)).all()
    talleres = session.exec(select(Taller).order_by(Taller.id)).all()
    tecnicos = session.exec(select(Tecnico).order_by(Tecnico.id)).all()
    solicitudes = session.exec(select(Solicitud).order_by(Solicitud.fecha_creacion.desc())).all()
    pagos = session.exec(select(Pago).order_by(Pago.fecha_creacion.desc())).all()
    auditoria = session.exec(
        select(AuditLog).order_by(AuditLog.fecha_creacion.desc()).limit(20)
    ).all()

    por_estado: dict[str, int] = {}
    por_tipo: dict[str, int] = {}
    for solicitud in solicitudes:
        estado = solicitud.estado.value if hasattr(solicitud.estado, "value") else str(solicitud.estado)
        por_estado[estado] = por_estado.get(estado, 0) + 1
        tipo = (solicitud.clasificacion_ia or "Sin clasificar").strip()
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

    pagos_confirmados = [pago for pago in pagos if pago.estado == "pagado"]
    ingreso_bruto = round(sum(pago.monto for pago in pagos_confirmados), 2)
    comision = round(sum(pago.comision_plataforma for pago in pagos_confirmados), 2)

    def tenant_name(tenant_id: int | None) -> str:
        tenant = next((item for item in tenants if item.id == tenant_id), None)
        return tenant.nombre if tenant else "Global"

    def propietario_nombre(user_id: int | None) -> str:
        user = next((item for item in users if item.id == user_id), None)
        return user.full_name or user.username if user else "Sin propietario"

    def taller_nombre(taller_id: int | None) -> str:
        taller = next((item for item in talleres if item.id == taller_id), None)
        return taller.nombre_comercial if taller else "Sin taller"

    def tecnico_nombre(tecnico_id: int | None) -> str:
        tecnico = next((item for item in tecnicos if item.id == tecnico_id), None)
        return tecnico.nombre if tecnico else "Sin tecnico"

    return {
        "resumen": {
            "tenants": len(tenants),
            "usuarios": len(users),
            "talleres": len(talleres),
            "tecnicos": len(tecnicos),
            "solicitudes": len(solicitudes),
            "pagos": len(pagos_confirmados),
            "ingreso_bruto": ingreso_bruto,
            "comision_plataforma": comision,
            "neto_talleres": round(ingreso_bruto - comision, 2),
        },
        "solicitudes": {
            "por_estado": por_estado,
            "por_tipo": por_tipo,
            "recientes": [
                {
                    "id": item.id,
                    "tenant_id": item.tenant_id,
                    "tenant": tenant_name(item.tenant_id),
                    "descripcion": item.descripcion,
                    "estado": item.estado.value if hasattr(item.estado, "value") else str(item.estado),
                    "clasificacion_ia": item.clasificacion_ia,
                    "prioridad_ia": item.prioridad_ia,
                    "taller": taller_nombre(item.taller_id),
                    "tecnico": tecnico_nombre(item.tecnico_id),
                    "latitud": item.latitud,
                    "longitud": item.longitud,
                    "fecha_creacion": item.fecha_creacion.isoformat() if item.fecha_creacion else None,
                }
                for item in solicitudes[:30]
            ],
        },
        "tenants": [
            {
                "id": item.id,
                "nombre": item.nombre,
                "slug": item.slug,
                "activo": item.activo,
                "usuarios": len([u for u in users if u.tenant_id == item.id]),
                "talleres": len([t for t in talleres if t.tenant_id == item.id]),
                "solicitudes": len([s for s in solicitudes if s.tenant_id == item.id]),
            }
            for item in tenants
        ],
        "talleres": [
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "tenant": tenant_name(item.tenant_id),
                "nombre_comercial": item.nombre_comercial,
                "direccion": item.direccion,
                "telefono": item.telefono,
                "propietario": propietario_nombre(item.propietario_id),
                "activo": item.activo,
                "calificacion_promedio": item.calificacion_promedio,
                "capacidad_operativa": item.capacidad_operativa,
                "latitud": item.latitud,
                "longitud": item.longitud,
                "tecnicos": len([tec for tec in tecnicos if tec.taller_id == item.id]),
                "solicitudes": len([s for s in solicitudes if s.taller_id == item.id]),
            }
            for item in talleres
        ],
        "tecnicos": [
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "tenant": tenant_name(item.tenant_id),
                "nombre": item.nombre,
                "taller": taller_nombre(item.taller_id),
                "disponible": item.disponible,
                "activo": item.activo,
                "latitud": item.latitud_actual or item.latitud,
                "longitud": item.longitud_actual or item.longitud,
            }
            for item in tecnicos
        ],
        "pagos": [
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "tenant": tenant_name(item.tenant_id),
                "solicitud_id": item.solicitud_id,
                "usuario_id": item.usuario_id,
                "monto": item.monto,
                "comision_plataforma": item.comision_plataforma,
                "estado": item.estado,
                "metodo": item.metodo,
                "fecha_creacion": item.fecha_creacion.isoformat() if item.fecha_creacion else None,
            }
            for item in pagos[:30]
        ],
        "auditoria": [
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "tenant": tenant_name(item.tenant_id),
                "actor_id": item.actor_id,
                "actor_rol": item.actor_rol,
                "accion": item.accion,
                "entidad": item.entidad,
                "entidad_id": item.entidad_id,
                "detalle": item.detalle,
                "fecha_creacion": item.fecha_creacion.isoformat() if item.fecha_creacion else None,
            }
            for item in auditoria
        ],
        "mapa": {
            "talleres": [
                {"id": item.id, "nombre": item.nombre_comercial, "latitud": item.latitud, "longitud": item.longitud}
                for item in talleres
                if item.latitud is not None and item.longitud is not None
            ],
            "tecnicos": [
                {
                    "id": item.id,
                    "nombre": item.nombre,
                    "latitud": item.latitud_actual or item.latitud,
                    "longitud": item.longitud_actual or item.longitud,
                }
                for item in tecnicos
                if (item.latitud_actual or item.latitud) is not None
                and (item.longitud_actual or item.longitud) is not None
            ],
            "solicitudes": [
                {
                    "id": item.id,
                    "descripcion": item.descripcion,
                    "latitud": item.latitud,
                    "longitud": item.longitud,
                    "estado": item.estado.value if hasattr(item.estado, "value") else str(item.estado),
                }
                for item in solicitudes[:50]
                if item.latitud is not None and item.longitud is not None
            ],
        },
    }


@router.post("/reasignacion/expirar")
def expirar_candidatos_endpoint(
    timeout_segundos: int = Query(90, ge=15, le=3600),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Recorre solicitudes BUSCANDO_TALLER y expira candidatos sin respuesta.

    Pensado para llamarse desde un cron externo (k8s CronJob, scheduler).
    Devuelve el resumen de reasignaciones que se ejecutaron en esta corrida.
    """
    _solo_admin(current_user)
    from app.services.reasignacion import expirar_candidatos_sin_respuesta

    en_busqueda = session.exec(
        select(Solicitud).where(Solicitud.estado == EstadoSolicitud.BUSCANDO_TALLER)
    ).all()
    reasignadas: list[dict] = []
    for solicitud in en_busqueda:
        nuevo = expirar_candidatos_sin_respuesta(
            session,
            solicitud=solicitud,
            timeout_segundos=timeout_segundos,
        )
        if nuevo is not None:
            reasignadas.append({
                "solicitud_id": solicitud.id,
                "nuevo_taller_id": nuevo.id,
                "nuevo_taller_nombre": nuevo.nombre_comercial,
            })
    session.commit()
    return {"reasignadas": reasignadas, "total": len(reasignadas)}


@router.get("/talleres/{taller_id}/metricas")
def metricas_taller(
    taller_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Métricas detalladas de un taller: accesible al admin y al taller dueño."""
    taller = session.get(Taller, taller_id)
    if not taller:
        raise HTTPException(status_code=404, detail="Taller no encontrado.")

    if current_user.role != UserRole.ADMIN and not (
        current_user.role == UserRole.WORKSHOP and taller.propietario_id == current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a las métricas de este taller.",
        )

    solicitudes = session.exec(
        select(Solicitud).where(Solicitud.taller_id == taller_id)
    ).all()

    finalizadas = [item for item in solicitudes if item.estado == EstadoSolicitud.FINALIZADO]
    canceladas = [item for item in solicitudes if item.estado == EstadoSolicitud.CANCELADO]
    activas = [
        item
        for item in solicitudes
        if item.estado in {
            EstadoSolicitud.ASIGNADA,
            EstadoSolicitud.TECNICO_EN_CAMINO,
            EstadoSolicitud.TECNICO_LLEGO,
            EstadoSolicitud.EN_PROCESO,
        }
    ]

    pagos = session.exec(
        select(Pago)
        .join(Solicitud, Solicitud.id == Pago.solicitud_id)
        .where(Solicitud.taller_id == taller_id)
        .where(Pago.estado == "pagado")
    ).all()
    ingreso_bruto = round(sum(item.monto for item in pagos), 2)
    comision = round(sum(item.comision_plataforma for item in pagos), 2)

    return {
        "taller_id": taller_id,
        "nombre": taller.nombre_comercial,
        "tecnicos": len(session.exec(
            select(Tecnico).where(Tecnico.taller_id == taller_id)
        ).all()),
        "solicitudes": {
            "total": len(solicitudes),
            "finalizadas": len(finalizadas),
            "canceladas": len(canceladas),
            "activas": len(activas),
        },
        "ingresos": {
            "bruto": ingreso_bruto,
            "comision_plataforma": comision,
            "neto": round(ingreso_bruto - comision, 2),
        },
        "reputacion": taller.calificacion_promedio or 0.0,
    }
