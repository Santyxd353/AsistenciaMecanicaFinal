"""KPIs operacionales calculados desde la base de datos.

Indicadores incluidos (del PDF del 2do parcial):

1. Tiempo promedio de asignación (creación → taller_asignado).
2. Tiempo promedio de llegada (taller_asignado → tecnico_llego).
3. Incidentes por tipo (clasificación IA).
4. Talleres más eficientes (ranking por tiempo de respuesta + finalización).
5. Zonas con más incidentes (clustering simple por redondeo de lat/lng).
6. Casos cancelados.
7. SLA cumplimiento (% de servicios atendidos dentro de `sla_esperado_minutos`).

Todos los queries se aplican con scope multi-tenant: ADMIN global puede pedir
`?tenant_id=` para inspeccionar un tenant específico, o no pasarlo para
agregado global. WORKSHOP/ADMIN de tenant solo ven su tenant.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import (
    EstadoSolicitud,
    Pago,
    Solicitud,
    Taller,
)
from app.models.user import User, UserRole


router = APIRouter()


def _resolver_tenant(current_user: User, tenant_id_query: Optional[int]) -> Optional[int]:
    """Resuelve el tenant_id efectivo respetando aislamiento.

    * ADMIN global: puede pasar `?tenant_id=` o quedarse global (None).
    * Cualquier otro rol: forzado al tenant del usuario; ignora el query.
    """
    if current_user.role == UserRole.ADMIN and current_user.tenant_id is None:
        return tenant_id_query
    if tenant_id_query is not None and tenant_id_query != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes consultar KPIs de otro tenant.",
        )
    return current_user.tenant_id


def _solicitudes_scope(session: Session, tenant_id: Optional[int]) -> list[Solicitud]:
    stmt = select(Solicitud)
    if tenant_id is not None:
        stmt = stmt.where(Solicitud.tenant_id == tenant_id)
    return list(session.exec(stmt).all())


def _delta_min(a: Optional[datetime], b: Optional[datetime]) -> Optional[float]:
    if a is None or b is None:
        return None
    delta = (b - a).total_seconds() / 60.0
    return delta if delta >= 0 else None


@router.get("/")
def kpis_principales(
    tenant_id: Optional[int] = Query(default=None),
    dias: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Devuelve los 7 KPIs principales del dashboard del 2do parcial."""
    effective_tenant = _resolver_tenant(current_user, tenant_id)

    desde = datetime.utcnow() - timedelta(days=dias)

    solicitudes = [
        item
        for item in _solicitudes_scope(session, effective_tenant)
        if item.fecha_creacion and item.fecha_creacion >= desde
    ]

    # ---- 1. Tiempo promedio de asignación
    tiempos_asignacion: list[float] = []
    for solicitud in solicitudes:
        delta = _delta_min(solicitud.fecha_creacion, solicitud.fecha_taller_asignado)
        if delta is not None:
            tiempos_asignacion.append(delta)
    tiempo_asignacion_promedio = (
        round(sum(tiempos_asignacion) / len(tiempos_asignacion), 2)
        if tiempos_asignacion else None
    )

    # ---- 2. Tiempo promedio de llegada
    tiempos_llegada: list[float] = []
    for solicitud in solicitudes:
        delta = _delta_min(solicitud.fecha_taller_asignado, solicitud.fecha_tecnico_llego)
        if delta is not None:
            tiempos_llegada.append(delta)
    tiempo_llegada_promedio = (
        round(sum(tiempos_llegada) / len(tiempos_llegada), 2)
        if tiempos_llegada else None
    )

    # ---- 3. Incidentes por tipo (clasificación IA)
    por_tipo: dict[str, int] = {}
    for solicitud in solicitudes:
        clave = (solicitud.clasificacion_ia or "Sin clasificar").strip()
        por_tipo[clave] = por_tipo.get(clave, 0) + 1

    # ---- 4. Talleres más eficientes
    # Score combinado: prioriza talleres con servicios FINALIZADOS y
    # menores tiempos de asignación+llegada+reparación. Devolvemos top 5.
    metrics_por_taller: dict[int, dict] = {}
    for solicitud in solicitudes:
        if not solicitud.taller_id:
            continue
        entry = metrics_por_taller.setdefault(solicitud.taller_id, {
            "total": 0,
            "finalizadas": 0,
            "tiempos_total_min": [],
        })
        entry["total"] += 1
        if solicitud.estado == EstadoSolicitud.FINALIZADO:
            entry["finalizadas"] += 1
        ciclo = _delta_min(solicitud.fecha_creacion, solicitud.fecha_finalizado)
        if ciclo is not None:
            entry["tiempos_total_min"].append(ciclo)

    talleres_ranking: list[dict] = []
    for taller_id, datos in metrics_por_taller.items():
        if datos["finalizadas"] == 0:
            continue
        promedio = sum(datos["tiempos_total_min"]) / len(datos["tiempos_total_min"]) if datos["tiempos_total_min"] else 0
        # Score: 50% tasa de finalización, 50% inverso del tiempo total.
        # Se normaliza tiempo con un divisor empírico de 120 min (2h)
        # como referencia operativa razonable.
        tasa_final = datos["finalizadas"] / datos["total"] if datos["total"] else 0
        tiempo_factor = max(0.0, 1.0 - (promedio / 240.0))
        score = round(50.0 * tasa_final + 50.0 * tiempo_factor, 2)
        taller = session.get(Taller, taller_id)
        talleres_ranking.append({
            "taller_id": taller_id,
            "nombre": taller.nombre_comercial if taller else None,
            "total_servicios": datos["total"],
            "finalizados": datos["finalizadas"],
            "tiempo_promedio_total_min": round(promedio, 2),
            "score_eficiencia": score,
        })
    talleres_ranking.sort(key=lambda item: item["score_eficiencia"], reverse=True)

    # ---- 5. Zonas con más incidentes (cluster por redondeo a 2 decimales ≈ 1.1km)
    zonas: dict[str, dict] = {}
    for solicitud in solicitudes:
        if solicitud.latitud is None or solicitud.longitud is None:
            continue
        clave = f"{round(solicitud.latitud, 2)},{round(solicitud.longitud, 2)}"
        bucket = zonas.setdefault(clave, {
            "lat": round(solicitud.latitud, 2),
            "lng": round(solicitud.longitud, 2),
            "incidentes": 0,
        })
        bucket["incidentes"] += 1
    zonas_ordenadas = sorted(zonas.values(), key=lambda item: item["incidentes"], reverse=True)

    # ---- 6. Casos cancelados
    cancelados = [item for item in solicitudes if item.estado == EstadoSolicitud.CANCELADO]
    porcentaje_cancelacion = (
        round(len(cancelados) / len(solicitudes) * 100, 2)
        if solicitudes else 0.0
    )

    # ---- 7. SLA cumplimiento
    sla_total = 0
    sla_cumplidos = 0
    for solicitud in solicitudes:
        if solicitud.estado != EstadoSolicitud.FINALIZADO:
            continue
        ciclo = _delta_min(solicitud.fecha_creacion, solicitud.fecha_finalizado)
        if ciclo is None:
            continue
        sla_total += 1
        if ciclo <= (solicitud.sla_esperado_minutos or 60):
            sla_cumplidos += 1
    sla_cumplimiento_pct = (
        round(sla_cumplidos / sla_total * 100, 2) if sla_total else None
    )

    # Ingresos (extra, útil para el dashboard).
    pagos_stmt = select(Pago).where(Pago.estado == "pagado")
    if effective_tenant is not None:
        pagos_stmt = pagos_stmt.where(Pago.tenant_id == effective_tenant)
    pagos = list(session.exec(pagos_stmt).all())
    ingreso_bruto = round(sum(item.monto for item in pagos), 2)
    comision = round(sum(item.comision_plataforma for item in pagos), 2)

    return {
        "tenant_id": effective_tenant,
        "ventana_dias": dias,
        "total_solicitudes": len(solicitudes),
        "tiempo_promedio_asignacion_min": tiempo_asignacion_promedio,
        "tiempo_promedio_llegada_min": tiempo_llegada_promedio,
        "incidentes_por_tipo": por_tipo,
        "talleres_mas_eficientes": talleres_ranking[:5],
        "zonas_con_mas_incidentes": zonas_ordenadas[:10],
        "casos_cancelados": {
            "total": len(cancelados),
            "porcentaje": porcentaje_cancelacion,
        },
        "sla_cumplimiento_pct": sla_cumplimiento_pct,
        "ingresos": {
            "bruto": ingreso_bruto,
            "comision_plataforma": comision,
            "neto_talleres": round(ingreso_bruto - comision, 2),
        },
    }


@router.get("/series-temporales")
def kpis_series(
    tenant_id: Optional[int] = Query(default=None),
    dias: int = Query(default=14, ge=1, le=90),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Serie diaria de solicitudes creadas y finalizadas — para charts."""
    effective_tenant = _resolver_tenant(current_user, tenant_id)
    desde = (datetime.utcnow() - timedelta(days=dias)).replace(hour=0, minute=0, second=0, microsecond=0)
    solicitudes = [
        item
        for item in _solicitudes_scope(session, effective_tenant)
        if item.fecha_creacion and item.fecha_creacion >= desde
    ]

    buckets: dict[str, dict] = {}
    for i in range(dias + 1):
        dia = (desde + timedelta(days=i)).date().isoformat()
        buckets[dia] = {"fecha": dia, "creadas": 0, "finalizadas": 0, "canceladas": 0}

    for solicitud in solicitudes:
        if solicitud.fecha_creacion:
            clave = solicitud.fecha_creacion.date().isoformat()
            if clave in buckets:
                buckets[clave]["creadas"] += 1
        if solicitud.fecha_finalizado:
            clave = solicitud.fecha_finalizado.date().isoformat()
            if clave in buckets:
                buckets[clave]["finalizadas"] += 1
        if solicitud.estado == EstadoSolicitud.CANCELADO and solicitud.fecha_creacion:
            clave = solicitud.fecha_creacion.date().isoformat()
            if clave in buckets:
                buckets[clave]["canceladas"] += 1

    return {"tenant_id": effective_tenant, "serie": list(buckets.values())}
