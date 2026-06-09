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
    Tecnico,
    Vehiculo,
)
from app.models.user import User, UserRole


router = APIRouter()


def _obtener_taller_actual(session: Session, current_user: User) -> Taller:
    """Devuelve el taller operativo del usuario actual.

    En SaaS hay admins de tenant que no siempre son `propietario_id` directo
    del taller. Por eso primero buscamos por propietario y luego por tenant.
    """
    if current_user.role not in {UserRole.WORKSHOP, UserRole.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores de taller pueden ver estos reportes.",
        )

    stmt = select(Taller)
    if current_user.tenant_id is not None:
        stmt = stmt.where(Taller.tenant_id == current_user.tenant_id)

    taller = session.exec(
        stmt.where(Taller.propietario_id == current_user.id)
    ).first()
    if taller:
        return taller

    if current_user.tenant_id is not None:
        taller = session.exec(
            select(Taller)
            .where(Taller.tenant_id == current_user.tenant_id)
            .where(Taller.activo == True)
            .order_by(Taller.id)
        ).first()
        if taller:
            return taller

    raise HTTPException(status_code=404, detail="No se encontro taller para este usuario.")


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


def _add_count(bucket: dict[str, int], key: str | None) -> None:
    clean = (key or "Sin dato").strip() or "Sin dato"
    bucket[clean] = bucket.get(clean, 0) + 1


def _top_dict(bucket: dict[str, int], limit: int = 8) -> list[dict]:
    return [
        {"nombre": key, "total": value}
        for key, value in sorted(bucket.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]


@router.get("/taller")
def reportes_taller(
    dias: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Reportes operativos para administrador de taller.

    Incluye rendimiento de trabajadores, incidentes frecuentes, modelos de auto
    auxiliados, zonas con mas auxilio, tiempos, ingresos y estado de casos.
    """
    taller = _obtener_taller_actual(session, current_user)
    desde = datetime.utcnow() - timedelta(days=dias)

    solicitudes = list(session.exec(
        select(Solicitud)
        .where(Solicitud.taller_id == taller.id)
        .where(Solicitud.tenant_id == taller.tenant_id)
        .where(Solicitud.fecha_creacion >= desde)
        .order_by(Solicitud.fecha_creacion.desc())
    ).all())

    tecnicos = {
        tecnico.id: tecnico
        for tecnico in session.exec(
            select(Tecnico)
            .where(Tecnico.taller_id == taller.id)
            .where(Tecnico.tenant_id == taller.tenant_id)
        ).all()
        if tecnico.id is not None
    }

    total = len(solicitudes)
    finalizadas = [s for s in solicitudes if s.estado == EstadoSolicitud.FINALIZADO]
    canceladas = [s for s in solicitudes if s.estado == EstadoSolicitud.CANCELADO]
    activas = [
        s for s in solicitudes
        if s.estado in {
            EstadoSolicitud.ASIGNADA,
            EstadoSolicitud.TECNICO_EN_CAMINO,
            EstadoSolicitud.TECNICO_LLEGO,
            EstadoSolicitud.EN_PROCESO,
        }
    ]
    pendientes = [
        s for s in solicitudes
        if s.estado in {EstadoSolicitud.PENDIENTE, EstadoSolicitud.BUSCANDO_TALLER}
    ]

    incidentes: dict[str, int] = {}
    modelos: dict[str, int] = {}
    marcas: dict[str, int] = {}
    zonas: dict[str, dict] = {}
    estados: dict[str, int] = {}
    tecnico_stats: dict[int, dict] = {}
    tiempos_llegada: list[float] = []
    tiempos_cierre: list[float] = []

    for solicitud in solicitudes:
        _add_count(estados, solicitud.estado.value if isinstance(solicitud.estado, EstadoSolicitud) else str(solicitud.estado))
        _add_count(incidentes, solicitud.clasificacion_ia)

        if solicitud.vehiculo_id:
            vehiculo = session.get(Vehiculo, solicitud.vehiculo_id)
            if vehiculo:
                _add_count(marcas, vehiculo.marca)
                modelo_label = f"{vehiculo.marca} {vehiculo.modelo}".strip()
                _add_count(modelos, modelo_label)

        if solicitud.latitud is not None and solicitud.longitud is not None:
            key = f"{round(solicitud.latitud, 2)},{round(solicitud.longitud, 2)}"
            zone = zonas.setdefault(key, {
                "lat": round(solicitud.latitud, 2),
                "lng": round(solicitud.longitud, 2),
                "total": 0,
            })
            zone["total"] += 1

        llegada = _delta_min(solicitud.fecha_taller_asignado, solicitud.fecha_tecnico_llego)
        if llegada is not None:
            tiempos_llegada.append(llegada)
        cierre = _delta_min(solicitud.fecha_creacion, solicitud.fecha_finalizado)
        if cierre is not None:
            tiempos_cierre.append(cierre)

        if solicitud.tecnico_id:
            entry = tecnico_stats.setdefault(solicitud.tecnico_id, {
                "tecnico_id": solicitud.tecnico_id,
                "nombre": tecnicos.get(solicitud.tecnico_id).nombre if solicitud.tecnico_id in tecnicos else "Mecanico",
                "total": 0,
                "finalizados": 0,
                "activos": 0,
                "cancelados": 0,
                "ingresos": 0.0,
                "tiempos_cierre": [],
                "calificacion": tecnicos.get(solicitud.tecnico_id).calificacion_promedio if solicitud.tecnico_id in tecnicos else 0.0,
            })
            entry["total"] += 1
            if solicitud.estado == EstadoSolicitud.FINALIZADO:
                entry["finalizados"] += 1
                entry["ingresos"] += float(solicitud.precio_cobrado or 0)
            elif solicitud.estado == EstadoSolicitud.CANCELADO:
                entry["cancelados"] += 1
            elif solicitud in activas:
                entry["activos"] += 1
            cierre_tecnico = _delta_min(solicitud.fecha_creacion, solicitud.fecha_finalizado)
            if cierre_tecnico is not None:
                entry["tiempos_cierre"].append(cierre_tecnico)

    trabajadores = []
    for entry in tecnico_stats.values():
        avg = (
            sum(entry["tiempos_cierre"]) / len(entry["tiempos_cierre"])
            if entry["tiempos_cierre"] else None
        )
        tasa_finalizacion = (
            round(entry["finalizados"] / entry["total"] * 100, 1)
            if entry["total"] else 0.0
        )
        score = round(
            (tasa_finalizacion * 0.55)
            + min(entry["finalizados"] * 7, 30)
            + min(float(entry["calificacion"] or 0) * 3, 15),
            1,
        )
        trabajadores.append({
            "tecnico_id": entry["tecnico_id"],
            "nombre": entry["nombre"],
            "total": entry["total"],
            "finalizados": entry["finalizados"],
            "activos": entry["activos"],
            "cancelados": entry["cancelados"],
            "ingresos": round(entry["ingresos"], 2),
            "tiempo_promedio_cierre_min": round(avg, 1) if avg is not None else None,
            "tasa_finalizacion_pct": tasa_finalizacion,
            "calificacion": round(float(entry["calificacion"] or 0), 1),
            "score": score,
        })
    trabajadores.sort(key=lambda item: item["score"], reverse=True)

    ingresos = round(sum(float(s.precio_cobrado or 0) for s in finalizadas), 2)
    comision = round(sum(float(s.comision_plataforma or 0) for s in finalizadas), 2)
    promedio_llegada = round(sum(tiempos_llegada) / len(tiempos_llegada), 1) if tiempos_llegada else None
    promedio_cierre = round(sum(tiempos_cierre) / len(tiempos_cierre), 1) if tiempos_cierre else None

    return {
        "taller": {
            "id": taller.id,
            "nombre": taller.nombre_comercial,
            "calificacion": taller.calificacion_promedio,
        },
        "ventana_dias": dias,
        "resumen": {
            "solicitudes": total,
            "pendientes": len(pendientes),
            "activas": len(activas),
            "finalizadas": len(finalizadas),
            "canceladas": len(canceladas),
            "ingresos": ingresos,
            "comision": comision,
            "neto": round(ingresos - comision, 2),
            "tiempo_promedio_llegada_min": promedio_llegada,
            "tiempo_promedio_cierre_min": promedio_cierre,
        },
        "trabajadores_mas_rendimiento": trabajadores[:8],
        "tipos_incidente": _top_dict(incidentes),
        "modelos_auxiliados": _top_dict(modelos),
        "marcas_auxiliadas": _top_dict(marcas),
        "zonas_mas_auxilio": sorted(zonas.values(), key=lambda item: item["total"], reverse=True)[:8],
        "estados": _top_dict(estados),
    }


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
