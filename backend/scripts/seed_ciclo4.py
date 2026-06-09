from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from app.core.security import get_password_hash
from app.db.session import engine, init_db
from app.models.domain import (
    Cotizacion,
    Especialidad,
    EspecialidadTaller,
    EstadoCotizacion,
    EstadoSolicitud,
    Notificacion,
    Pago,
    Solicitud,
    SubscriptionPaymentMock,
    TipoNotificacion,
    TrackingPing,
    Vehiculo,
    Taller,
    Tecnico,
    Tenant,
    TenantSubscription,
    SaaSPlan,
    VehiculoHistorialReparacion,
)
from app.models.user import User, UserRole


PASSWORD = "Prueba*2026"
BASE_TIME = datetime.utcnow().replace(microsecond=0) - timedelta(days=12)
PLANS_BY_INDEX = ["gratis", "intermedio", "premium", "pro"]
ACTIVE_TALLER_COUNT = 5
TECHNICIANS_PER_TALLER = 2
CASES_PER_TALLER = 10
LOGIN_EMAIL_DOMAIN = "taller.test"


@dataclass(frozen=True)
class TenantSeed:
    slug: str
    nombre: str
    descripcion: str
    plan_codigo: str
    taller_nombre: str
    direccion: str
    telefono: str
    lat: float
    lng: float
    especialidades: tuple[str, ...]


TENANTS: tuple[TenantSeed, ...] = (
    TenantSeed("taller01", "taller01", "Tenant seed Santa Cruz - taller01.", "gratis", "taller01", "Av. Monseñor Rivero y 1er Anillo, Santa Cruz de la Sierra", "77010001", -17.7749, -63.1823, ("Bateria", "Electricidad", "Auxilio general")),
    TenantSeed("taller02", "taller02", "Tenant seed Santa Cruz - taller02.", "intermedio", "taller02", "Av. Cristo Redentor 2do Anillo, Santa Cruz de la Sierra", "77010002", -17.7584, -63.1817, ("Motor", "Frenos", "Auxilio general")),
    TenantSeed("taller03", "taller03", "Tenant seed Santa Cruz - taller03.", "premium", "taller03", "Av. Banzer 4to Anillo, Santa Cruz de la Sierra", "77010003", -17.7385, -63.1852, ("Llantas", "Motor", "Auxilio general")),
    TenantSeed("taller04", "taller04", "Tenant seed Santa Cruz - taller04.", "pro", "taller04", "Av. Beni 3er Anillo, Santa Cruz de la Sierra", "77010004", -17.7577, -63.1657, ("Bateria", "Llantas", "Auxilio general")),
    TenantSeed("taller05", "taller05", "Tenant seed Santa Cruz - taller05.", "gratis", "taller05", "Av. Alemana 4to Anillo, Santa Cruz de la Sierra", "77010005", -17.7555, -63.1518, ("Motor", "Electricidad", "Auxilio general")),
)
ACTIVE_TENANT_SLUGS = {item.slug for item in TENANTS}
RETIRED_SEED_TENANT_SLUGS = tuple(
    f"taller{index:02d}" for index in range(ACTIVE_TALLER_COUNT + 1, 11)
)


DRIVER_ASSIGNMENTS = [
    (
        f"conductor{index:02d}",
        f"conductor{index:02d}@{LOGIN_EMAIL_DOMAIN}",
        f"Conductor {index:02d}",
        f"taller{((index - 1) % len(TENANTS)) + 1:02d}",
    )
    for index in range(1, 11)
]


INCIDENT_PROFILES = (
    ("Problema de bateria o sistema electrico", "Alta", "El vehiculo no enciende y requiere revision de bateria/alternador."),
    ("Problema de llanta o neumatico", "Media", "El conductor reporta llanta baja o pinchada en ruta."),
    ("Problema de motor o recalentamiento", "Alta", "El vehiculo presenta recalentamiento y perdida de potencia."),
    ("Problema de frenos", "Alta", "El conductor reporta vibracion o perdida de respuesta al frenar."),
    ("Incidente general", "Media", "Falla general diagnosticada y resuelta por asistencia mecanica."),
)


REQUEST_TEMPLATES = [
    (
        f"seed-c4-req-{workshop_index:02d}-{case_index:02d}",
        f"conductor{((workshop_index + case_index - 2) % 10) + 1:02d}",
        f"taller{workshop_index:02d}",
        EstadoSolicitud.FINALIZADO,
        INCIDENT_PROFILES[(workshop_index + case_index - 2) % len(INCIDENT_PROFILES)][0],
        INCIDENT_PROFILES[(workshop_index + case_index - 2) % len(INCIDENT_PROFILES)][1],
        INCIDENT_PROFILES[(workshop_index + case_index - 2) % len(INCIDENT_PROFILES)][2],
        ((case_index % 5) - 2) * 0.006,
        (((case_index + 2) % 5) - 2) * 0.006,
    )
    for workshop_index in range(1, ACTIVE_TALLER_COUNT + 1)
    for case_index in range(1, CASES_PER_TALLER + 1)
]


def log(message: str) -> None:
    print(f"[seed-c4] {message}")


def infer_specialty(clasificacion: str) -> str:
    texto = clasificacion.casefold()
    if "bateria" in texto or "electrico" in texto or "electric" in texto:
        return "electricidad"
    if "llanta" in texto or "neumatico" in texto:
        return "llantas"
    if "motor" in texto or "recalentamiento" in texto:
        return "motor"
    if "cerrajer" in texto or "llave" in texto:
        return "cerrajeria"
    return "general"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed manual para ciclo 4.")
    parser.add_argument(
        "--step",
        default="summary",
        choices=[
            "bootstrap",
            "tenants",
            "workshops",
            "drivers",
            "technicians",
            "vehicles",
            "requests",
            "quotes",
            "payments",
            "notifications",
            "tracking",
            "summary",
            "all",
        ],
    )
    return parser.parse_args()


def ensure_user(
    session: Session,
    *,
    username: str,
    email: str,
    full_name: str,
    role: UserRole,
    tenant_id: int | None,
    telefono: str | None = None,
) -> User:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            tenant_id=tenant_id,
            telefono=telefono,
            is_active=True,
            hashed_password=get_password_hash(PASSWORD),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        log(f"Usuario creado: {username}")
        return user

    user.email = email
    user.full_name = full_name
    user.role = role
    user.tenant_id = tenant_id
    user.telefono = telefono
    user.is_active = True
    session.add(user)
    session.commit()
    session.refresh(user)
    log(f"Usuario actualizado: {username}")
    return user


def get_tenant_map(session: Session) -> dict[str, Tenant]:
    result: dict[str, Tenant] = {}
    for item in TENANTS:
        tenant = session.exec(select(Tenant).where(Tenant.slug == item.slug)).first()
        if tenant:
            result[item.slug] = tenant
    return result


def cleanup_retired_seed_data(session: Session) -> None:
    retired_tenants = session.exec(
        select(Tenant).where(Tenant.slug.in_(RETIRED_SEED_TENANT_SLUGS))
    ).all()
    retired_tenant_ids = [tenant.id for tenant in retired_tenants if tenant.id is not None]

    obsolete_requests: list[Solicitud] = []
    for index in range(ACTIVE_TALLER_COUNT + 1, 11):
        obsolete_requests.extend(
            session.exec(
                select(Solicitud).where(
                    Solicitud.cliente_sync_id.like(f"seed-c4-req-{index:02d}-%")
                )
            ).all()
        )
    obsolete_request_ids = [item.id for item in obsolete_requests if item.id is not None]

    if obsolete_request_ids:
        for solicitud in obsolete_requests:
            solicitud.cotizacion_seleccionada_id = None
            session.add(solicitud)
        session.commit()

        for model in (TrackingPing, Notificacion, Pago, VehiculoHistorialReparacion, Cotizacion):
            for row in session.exec(
                select(model).where(model.solicitud_id.in_(obsolete_request_ids))
            ).all():
                session.delete(row)
        session.commit()

        for solicitud in obsolete_requests:
            session.delete(solicitud)
        session.commit()
        log(f"Solicitudes seed retiradas eliminadas: {len(obsolete_request_ids)}")

    for index in range(ACTIVE_TALLER_COUNT + 1, 11):
        referencia = f"seed-c4-subpay-{index:02d}"
        payment = session.exec(
            select(SubscriptionPaymentMock).where(
                SubscriptionPaymentMock.referencia == referencia
            )
        ).first()
        if payment:
            session.delete(payment)
    session.commit()

    if retired_tenant_ids:
        for taller in session.exec(
            select(Taller).where(Taller.tenant_id.in_(retired_tenant_ids))
        ).all():
            taller.activo = False
            session.add(taller)

        for sub in session.exec(
            select(TenantSubscription).where(
                TenantSubscription.tenant_id.in_(retired_tenant_ids)
            )
        ).all():
            sub.estado = "inactiva"
            session.add(sub)

        for user in session.exec(
            select(User).where(User.tenant_id.in_(retired_tenant_ids))
        ).all():
            if user.username.startswith("seed_owner_"):
                user.email = f"{user.username}@{LOGIN_EMAIL_DOMAIN}"
                user.is_active = False
                session.add(user)

        for tenant in retired_tenants:
            tenant.activo = False
            session.add(tenant)
        session.commit()
        log(f"Tenants seed retirados desactivados: {len(retired_tenant_ids)}")


def step_bootstrap() -> None:
    init_db()
    log("Base, tenant default, planes y especialidades iniciales listos.")


def step_tenants() -> None:
    with Session(engine) as session:
        plans = {
            plan.codigo: plan
            for plan in session.exec(select(SaaSPlan)).all()
        }
        for item in TENANTS:
            tenant = session.exec(select(Tenant).where(Tenant.slug == item.slug)).first()
            if not tenant:
                tenant = Tenant(
                    nombre=item.nombre,
                    slug=item.slug,
                    descripcion=item.descripcion,
                    activo=True,
                )
                session.add(tenant)
                session.commit()
                session.refresh(tenant)
                log(f"Tenant creado: {item.slug}")
            else:
                tenant.nombre = item.nombre
                tenant.descripcion = item.descripcion
                tenant.activo = True
                session.add(tenant)
                session.commit()
                session.refresh(tenant)
                log(f"Tenant actualizado: {item.slug}")

            plan = plans.get(item.plan_codigo)
            if not plan or tenant.id is None or plan.id is None:
                continue
            sub = session.exec(
                select(TenantSubscription).where(
                    TenantSubscription.tenant_id == tenant.id,
                    TenantSubscription.estado == "activa",
                )
            ).first()
            if not sub:
                sub = TenantSubscription(
                    tenant_id=tenant.id,
                    plan_id=plan.id,
                    estado="activa",
                )
            else:
                sub.plan_id = plan.id
                sub.estado = "activa"
            session.add(sub)
            session.commit()
        cleanup_retired_seed_data(session)


def step_workshops() -> None:
    with Session(engine) as session:
        tenant_map = get_tenant_map(session)
        specialty_map = {
            item.nombre: item
            for item in session.exec(select(EspecialidadTaller)).all()
        }
        for index, item in enumerate(TENANTS, start=1):
            tenant = tenant_map[item.slug]
            owner = ensure_user(
                session,
                username=f"seed_owner_{index:02d}",
                email=f"owner{index:02d}@{LOGIN_EMAIL_DOMAIN}",
                full_name=f"Administrador Taller {index}",
                role=UserRole.WORKSHOP,
                tenant_id=tenant.id,
                telefono=f"730000{index:02d}",
            )
            taller = session.exec(
                select(Taller).where(Taller.propietario_id == owner.id)
            ).first()
            if not taller:
                taller = Taller(
                    nombre_comercial=item.taller_nombre,
                    direccion=item.direccion,
                    telefono=item.telefono,
                    email_contacto=f"contacto{index:02d}@{LOGIN_EMAIL_DOMAIN}",
                    horario_atencion="Lunes-Domingo 06:00-22:00",
                    descripcion=f"Taller seed para {item.nombre}.",
                    sitio_web=f"https://{item.slug}.{LOGIN_EMAIL_DOMAIN}",
                    latitud=item.lat,
                    longitud=item.lng,
                    capacidad_operativa=5,
                    activo=True,
                    propietario_id=owner.id or 0,
                    tenant_id=tenant.id,
                )
            else:
                taller.nombre_comercial = item.taller_nombre
                taller.direccion = item.direccion
                taller.telefono = item.telefono
                taller.email_contacto = f"contacto{index:02d}@{LOGIN_EMAIL_DOMAIN}"
                taller.horario_atencion = "Lunes-Domingo 06:00-22:00"
                taller.descripcion = f"Taller seed para {item.nombre}."
                taller.sitio_web = f"https://{item.slug}.{LOGIN_EMAIL_DOMAIN}"
                taller.latitud = item.lat
                taller.longitud = item.lng
                taller.capacidad_operativa = 5
                taller.activo = True
                taller.propietario_id = owner.id or 0
                taller.tenant_id = tenant.id
            session.add(taller)
            session.commit()
            session.refresh(taller)

            taller.especialidades = [
                specialty_map[name]
                for name in item.especialidades
                if name in specialty_map
            ]
            session.add(taller)
            session.commit()
            log(f"Taller listo: {item.taller_nombre}")


def step_drivers() -> None:
    with Session(engine) as session:
        tenant_map = get_tenant_map(session)
        for index, (username, email, full_name, tenant_slug) in enumerate(DRIVER_ASSIGNMENTS, start=1):
            tenant = tenant_map[tenant_slug]
            ensure_user(
                session,
                username=username,
                email=email,
                full_name=full_name,
                role=UserRole.DRIVER,
                tenant_id=tenant.id,
                telefono=f"740000{index:02d}",
            )


def step_technicians() -> None:
    with Session(engine) as session:
        tenant_map = get_tenant_map(session)
        specialty_map = {
            item.nombre: item
            for item in session.exec(select(Especialidad)).all()
        }
        for index, item in enumerate(TENANTS, start=1):
            tenant = tenant_map[item.slug]
            taller = session.exec(
                select(Taller).where(Taller.tenant_id == tenant.id)
            ).first()
            if not taller:
                raise RuntimeError(f"No existe taller para tenant {item.slug}")

            for slot in range(1, TECHNICIANS_PER_TALLER + 1):
                tech_index = (index - 1) * TECHNICIANS_PER_TALLER + slot
                username = f"tecnico{tech_index:02d}"
                user = ensure_user(
                    session,
                    username=username,
                    email=f"{username}@{LOGIN_EMAIL_DOMAIN}",
                    full_name=f"Tecnico {tech_index:02d}",
                    role=UserRole.TECNICO,
                    tenant_id=tenant.id,
                    telefono=f"780100{tech_index:02d}",
                )
                ci = f"90{tech_index:02d}2026"
                tecnico = session.exec(
                    select(Tecnico).where(Tecnico.id_usuario == user.id)
                ).first()
                lat_offset = 0.0015 * slot
                lng_offset = -0.0015 * slot
                if not tecnico:
                    tecnico = Tecnico(
                        nombre=f"tecnico{tech_index:02d}",
                        ci=ci,
                        direccion=f"Base tecnica {slot} - {item.direccion}",
                        latitud=item.lat + lat_offset,
                        longitud=item.lng + lng_offset,
                        latitud_actual=item.lat + lat_offset + 0.0005,
                        longitud_actual=item.lng + lng_offset - 0.0005,
                        ultima_actualizacion_ubicacion=BASE_TIME + timedelta(hours=tech_index),
                        disponible=True,
                        activo=True,
                        taller_id=taller.id,
                        id_usuario=user.id,
                        tenant_id=tenant.id,
                    )
                else:
                    tecnico.nombre = f"tecnico{tech_index:02d}"
                    tecnico.ci = ci
                    tecnico.direccion = f"Base tecnica {slot} - {item.direccion}"
                    tecnico.latitud = item.lat + lat_offset
                    tecnico.longitud = item.lng + lng_offset
                    tecnico.latitud_actual = item.lat + lat_offset + 0.0005
                    tecnico.longitud_actual = item.lng + lng_offset - 0.0005
                    tecnico.ultima_actualizacion_ubicacion = BASE_TIME + timedelta(hours=tech_index)
                    tecnico.disponible = True
                    tecnico.activo = True
                    tecnico.taller_id = taller.id
                    tecnico.id_usuario = user.id
                    tecnico.tenant_id = tenant.id
                tecnico.total_calificaciones = 5
                tecnico.calificacion_promedio = round(4.2 + (tech_index % 5) * 0.15, 2)
                session.add(tecnico)
                session.commit()
                session.refresh(tecnico)

                tecnico.especialidades = [
                    specialty_map[name]
                    for name in item.especialidades[:2]
                    if name in specialty_map
                ]
                session.add(tecnico)
                session.commit()
                log(f"Tecnico listo: {username}")


def step_vehicles() -> None:
    marcas = ["Toyota", "Nissan", "Suzuki", "Kia", "Hyundai", "Chevrolet", "Ford", "Volkswagen", "Honda", "Mazda"]
    modelos = ["Corolla", "Frontier", "Swift", "Rio", "Accent", "Onix", "Ranger", "Gol", "Civic", "BT-50"]
    colores = ["Blanco", "Gris", "Rojo", "Azul", "Negro", "Plata", "Verde", "Dorado", "Guindo", "Celeste"]
    with Session(engine) as session:
        for index, (username, _email, _full_name, _tenant_slug) in enumerate(DRIVER_ASSIGNMENTS, start=1):
            user = session.exec(select(User).where(User.username == username)).first()
            if not user:
                raise RuntimeError(f"No existe conductor {username}")
            placa = f"SCZ{index:04d}"
            vehicle = session.exec(select(Vehiculo).where(Vehiculo.placa == placa)).first()
            if not vehicle:
                vehicle = Vehiculo(
                    placa=placa,
                    marca=marcas[index - 1],
                    modelo=modelos[index - 1],
                    color=colores[index - 1],
                    propietario_id=user.id,
                    tenant_id=user.tenant_id,
                )
            else:
                vehicle.marca = marcas[index - 1]
                vehicle.modelo = modelos[index - 1]
                vehicle.color = colores[index - 1]
                vehicle.propietario_id = user.id
                vehicle.tenant_id = user.tenant_id
            session.add(vehicle)
            session.commit()
            log(f"Vehiculo listo: {placa}")


def _tecnicos_for_taller(session: Session, taller_id: int) -> list[Tecnico]:
    return list(session.exec(
        select(Tecnico)
        .where(Tecnico.taller_id == taller_id)
        .order_by(Tecnico.id.asc())
    ).all())


def step_requests() -> None:
    with Session(engine) as session:
        tenant_map = get_tenant_map(session)
        completed_by_taller: dict[int, list[int]] = {}
        for index, (sync_id, driver_username, tenant_slug, state, clasificacion, prioridad, detalle, dlat, dlng) in enumerate(REQUEST_TEMPLATES, start=1):
            user = session.exec(select(User).where(User.username == driver_username)).first()
            if not user:
                raise RuntimeError(f"No existe conductor {driver_username}")
            tenant = tenant_map[tenant_slug]
            vehicle = session.exec(
                select(Vehiculo).where(Vehiculo.propietario_id == user.id)
            ).first()
            taller = session.exec(
                select(Taller).where(Taller.tenant_id == tenant.id)
            ).first()
            tecnicos = _tecnicos_for_taller(session, taller.id) if taller and taller.id else []
            if not taller or not tecnicos:
                raise RuntimeError(f"Falta taller o tecnico para {tenant_slug}")

            workshop_number = int(tenant_slug.replace("taller", ""))
            case_number = ((index - 1) % 10) + 1
            tecnico = tecnicos[(case_number - 1) % len(tecnicos)]
            created_at = BASE_TIME + timedelta(hours=index * 2)
            assigned_at = created_at + timedelta(minutes=6 + workshop_number) if state in {
                EstadoSolicitud.ASIGNADA,
                EstadoSolicitud.TECNICO_EN_CAMINO,
                EstadoSolicitud.TECNICO_LLEGO,
                EstadoSolicitud.EN_PROCESO,
                EstadoSolicitud.FINALIZADO,
            } else None
            arrived_at = assigned_at + timedelta(minutes=12 + case_number) if state in {
                EstadoSolicitud.TECNICO_LLEGO,
                EstadoSolicitud.EN_PROCESO,
                EstadoSolicitud.FINALIZADO,
            } and assigned_at else None
            finished_at = arrived_at + timedelta(minutes=28 + (case_number * 3)) if state == EstadoSolicitud.FINALIZADO and arrived_at else None
            costo = round(180 + workshop_number * 18 + case_number * 22.5, 2)
            comision = round(costo * 0.10, 2)

            solicitud = session.exec(
                select(Solicitud).where(Solicitud.cliente_sync_id == sync_id)
            ).first()
            if not solicitud:
                solicitud = Solicitud(
                    descripcion=f"[{sync_id}] {detalle} Atendido en Santa Cruz por {taller.nombre_comercial}.",
                    latitud=(taller.latitud or -17.7833) + dlat,
                    longitud=(taller.longitud or -63.1821) + dlng,
                    estado=state,
                    clasificacion_ia=clasificacion,
                    prioridad_ia=prioridad,
                    resumen_ia=f"Resumen seed: {detalle}",
                    especialidad_requerida_ia=infer_specialty(clasificacion),
                    distancia_estimada_km=round(1.2 + case_number * 0.45 + workshop_number * 0.08, 2),
                    asignacion_score=round(0.70 + (case_number % 7) * 0.035, 2),
                    tiempo_estimado_minutos=18 + case_number,
                    precio_cobrado=costo,
                    comision_plataforma=comision,
                    estado_pago="pagado",
                    vehiculo_id=vehicle.id if vehicle else None,
                    taller_id=taller.id,
                    tecnico_id=tecnico.id,
                    tenant_id=tenant.id,
                    cliente_sync_id=sync_id,
                    sla_esperado_minutos=95 + (case_number % 3) * 15,
                    fecha_taller_asignado=assigned_at,
                    fecha_tecnico_llego=arrived_at,
                    fecha_finalizado=finished_at,
                )
                solicitud.fecha_creacion = created_at
            else:
                solicitud.descripcion = f"[{sync_id}] {detalle} Atendido en Santa Cruz por {taller.nombre_comercial}."
                solicitud.latitud = (taller.latitud or -17.7833) + dlat
                solicitud.longitud = (taller.longitud or -63.1821) + dlng
                solicitud.estado = state
                solicitud.clasificacion_ia = clasificacion
                solicitud.prioridad_ia = prioridad
                solicitud.resumen_ia = f"Resumen seed: {detalle}"
                solicitud.especialidad_requerida_ia = infer_specialty(clasificacion)
                solicitud.distancia_estimada_km = round(1.2 + case_number * 0.45 + workshop_number * 0.08, 2)
                solicitud.asignacion_score = round(0.70 + (case_number % 7) * 0.035, 2)
                solicitud.tiempo_estimado_minutos = 18 + case_number
                solicitud.precio_cobrado = costo
                solicitud.comision_plataforma = comision
                solicitud.estado_pago = "pagado"
                solicitud.vehiculo_id = vehicle.id if vehicle else None
                solicitud.taller_id = taller.id
                solicitud.tecnico_id = tecnico.id
                solicitud.tenant_id = tenant.id
                solicitud.sla_esperado_minutos = 95 + (case_number % 3) * 15
                solicitud.fecha_taller_asignado = assigned_at
                solicitud.fecha_tecnico_llego = arrived_at
                solicitud.fecha_finalizado = finished_at
                solicitud.fecha_creacion = created_at
            session.add(solicitud)
            session.commit()
            session.refresh(solicitud)

            history = session.exec(
                select(VehiculoHistorialReparacion).where(
                    VehiculoHistorialReparacion.solicitud_id == solicitud.id
                )
            ).first()
            if vehicle and solicitud.id:
                if not history:
                    history = VehiculoHistorialReparacion(
                        vehiculo_id=vehicle.id or 0,
                        solicitud_id=solicitud.id,
                        taller_id=taller.id,
                        tecnico_id=tecnico.id,
                        tenant_id=tenant.id,
                    )
                history.titulo = f"Atencion {case_number:02d} en {taller.nombre_comercial}"
                history.diagnostico = clasificacion
                history.acciones_realizadas = (
                    "Diagnostico en sitio, asistencia mecanica, prueba de funcionamiento "
                    "y cierre del caso con conformidad del conductor."
                )
                history.categoria = infer_specialty(clasificacion)
                history.prioridad = prioridad
                history.costo = costo
                history.estado_pago = "pagado"
                history.kilometraje = 45000 + index * 137
                history.observaciones = f"Caso seed KPI {sync_id}; tecnico asignado {tecnico.nombre}."
                history.fecha_servicio = finished_at or created_at
                history.fecha_creacion = created_at
                history.fecha_actualizacion = finished_at or created_at
                session.add(history)
                session.commit()

            if taller.id:
                completed_by_taller.setdefault(taller.id, []).append(assigned_at.minute if assigned_at else 0)
            log(f"Solicitud lista: {sync_id}")

        for taller_id, assignment_minutes in completed_by_taller.items():
            taller = session.get(Taller, taller_id)
            if not taller:
                continue
            taller.total_servicios_completados = len(assignment_minutes)
            taller.tiempo_respuesta_promedio = round(sum(assignment_minutes) / len(assignment_minutes)) if assignment_minutes else None
            taller.calificacion_promedio = 4.3
            session.add(taller)
        session.commit()


def step_quotes() -> None:
    with Session(engine) as session:
        requests = session.exec(
            select(Solicitud).where(Solicitud.cliente_sync_id.like("seed-c4-req-%"))
        ).all()
        for index, solicitud in enumerate(sorted(requests, key=lambda item: item.cliente_sync_id or ""), start=1):
            if not solicitud.taller_id:
                taller = session.exec(
                    select(Taller).where(Taller.tenant_id == solicitud.tenant_id)
                ).first()
                solicitud.taller_id = taller.id if taller else None
                session.add(solicitud)
                session.commit()
            if not solicitud.taller_id:
                continue

            descripcion = f"[SEED-C4-COT-{index:02d}] Cotizacion seed ciclo 4"
            cotizacion = session.exec(
                select(Cotizacion).where(
                    Cotizacion.solicitud_id == solicitud.id,
                    Cotizacion.taller_id == solicitud.taller_id,
                )
            ).first()
            if not cotizacion:
                cotizacion = Cotizacion(
                    solicitud_id=solicitud.id or 0,
                    taller_id=solicitud.taller_id,
                    tenant_id=solicitud.tenant_id,
                    costo_estimado=round(180 + index * 35.5, 2),
                    tiempo_reparacion_horas=round(1.5 + index * 0.2, 1),
                    eta_llegada_minutos=15 + index * 2,
                    descripcion=descripcion,
                    incluye_repuestos=index % 2 == 0,
                    garantia_dias=15 + index,
                )
                cotizacion.fecha_creacion = BASE_TIME + timedelta(hours=2 + index)
            else:
                cotizacion.costo_estimado = round(180 + index * 35.5, 2)
                cotizacion.tiempo_reparacion_horas = round(1.5 + index * 0.2, 1)
                cotizacion.eta_llegada_minutos = 15 + index * 2
                cotizacion.descripcion = descripcion
                cotizacion.incluye_repuestos = index % 2 == 0
                cotizacion.garantia_dias = 15 + index

            if solicitud.estado in {EstadoSolicitud.FINALIZADO, EstadoSolicitud.EN_PROCESO, EstadoSolicitud.ASIGNADA}:
                cotizacion.estado = EstadoCotizacion.ACEPTADA
                cotizacion.fecha_seleccion = solicitud.fecha_taller_asignado
                solicitud.cotizacion_seleccionada_id = cotizacion.id
                solicitud.precio_cobrado = cotizacion.costo_estimado
                solicitud.comision_plataforma = round(cotizacion.costo_estimado * 0.10, 2)
            elif solicitud.estado == EstadoSolicitud.CANCELADO:
                cotizacion.estado = EstadoCotizacion.RECHAZADA
                cotizacion.fecha_seleccion = None
            else:
                cotizacion.estado = EstadoCotizacion.ENVIADA
                cotizacion.fecha_seleccion = None

            session.add(cotizacion)
            session.commit()
            session.refresh(cotizacion)
            if solicitud.cotizacion_seleccionada_id != cotizacion.id and cotizacion.estado == EstadoCotizacion.ACEPTADA:
                solicitud.cotizacion_seleccionada_id = cotizacion.id
                session.add(solicitud)
                session.commit()
            log(f"Cotizacion lista para solicitud {solicitud.cliente_sync_id}")


def step_payments() -> None:
    with Session(engine) as session:
        plans = {
            plan.codigo: plan
            for plan in session.exec(select(SaaSPlan)).all()
        }
        tenants = list(get_tenant_map(session).values())

        for index in range(1, ACTIVE_TALLER_COUNT + 1):
            tenant = tenants[(index - 1) % len(tenants)]
            plan_codigo = PLANS_BY_INDEX[(index - 1) % len(PLANS_BY_INDEX)]
            plan = plans[plan_codigo]
            referencia = f"seed-c4-subpay-{index:02d}"
            payment = session.exec(
                select(SubscriptionPaymentMock).where(
                    SubscriptionPaymentMock.referencia == referencia
                )
            ).first()
            if not payment:
                payment = SubscriptionPaymentMock(
                    plan_id=plan.id or 0,
                    tenant_id=tenant.id,
                    monto=round(plan.precio_mensual or 0, 2),
                    moneda="BOB",
                    estado="pagado" if index <= 6 else "pendiente_pago",
                    referencia=referencia,
                    metodo="mock",
                    contacto_email=f"billing{index:02d}@{LOGIN_EMAIL_DOMAIN}",
                    contacto_nombre=f"Contacto Billing {index:02d}",
                    onboarding_token=f"seed-c4-onboard-{index:02d}",
                    usado=index <= 4,
                    fecha_pago=BASE_TIME + timedelta(days=index) if index <= 6 else None,
                )
                payment.fecha_creacion = BASE_TIME + timedelta(days=index - 1)
            else:
                payment.plan_id = plan.id or 0
                payment.tenant_id = tenant.id
                payment.monto = round(plan.precio_mensual or 0, 2)
                payment.estado = "pagado" if index <= 6 else "pendiente_pago"
                payment.metodo = "mock"
                payment.contacto_email = f"billing{index:02d}@{LOGIN_EMAIL_DOMAIN}"
                payment.contacto_nombre = f"Contacto Billing {index:02d}"
                payment.onboarding_token = f"seed-c4-onboard-{index:02d}"
                payment.usado = index <= 4
                payment.fecha_pago = BASE_TIME + timedelta(days=index) if index <= 6 else None
                payment.fecha_creacion = BASE_TIME + timedelta(days=index - 1)
            session.add(payment)
            session.commit()

        paid_requests = session.exec(
            select(Solicitud)
            .where(Solicitud.cliente_sync_id.like("seed-c4-req-%"))
            .where(Solicitud.estado == EstadoSolicitud.FINALIZADO)
            .order_by(Solicitud.id.asc())
        ).all()
        for index, solicitud in enumerate(paid_requests, start=1):
            vehiculo = session.get(Vehiculo, solicitud.vehiculo_id) if solicitud.vehiculo_id else None
            if not vehiculo or not vehiculo.propietario_id:
                continue
            referencia = f"seed-c4-servicepay-{index:02d}"
            pago = session.exec(select(Pago).where(Pago.referencia == referencia)).first()
            monto = round((solicitud.precio_cobrado or (220 + index * 40)), 2)
            comision = round(monto * 0.10, 2)
            if not pago:
                pago = Pago(
                    solicitud_id=solicitud.id or 0,
                    usuario_id=vehiculo.propietario_id,
                    tenant_id=solicitud.tenant_id,
                    monto=monto,
                    comision_plataforma=comision,
                    metodo="mock",
                    estado="pagado",
                    referencia=referencia,
                )
                pago.fecha_creacion = (solicitud.fecha_finalizado or BASE_TIME) + timedelta(minutes=20)
            else:
                pago.solicitud_id = solicitud.id or 0
                pago.usuario_id = vehiculo.propietario_id
                pago.tenant_id = solicitud.tenant_id
                pago.monto = monto
                pago.comision_plataforma = comision
                pago.metodo = "mock"
                pago.estado = "pagado"
                pago.fecha_creacion = (solicitud.fecha_finalizado or BASE_TIME) + timedelta(minutes=20)
            solicitud.estado_pago = "pagado"
            solicitud.fecha_pago = pago.fecha_creacion
            solicitud.precio_cobrado = monto
            solicitud.comision_plataforma = comision
            session.add(solicitud)
            session.add(pago)
            session.commit()
        log("Pagos mock SaaS y pagos de servicio para KPI listos.")


def step_notifications() -> None:
    with Session(engine) as session:
        requests = session.exec(
            select(Solicitud)
            .where(Solicitud.cliente_sync_id.like("seed-c4-req-%"))
            .order_by(Solicitud.id.asc())
        ).all()
        for index in range(1, 11):
            solicitud = requests[(index - 1) % len(requests)]
            destinatario_id = None
            if index % 2 == 0:
                taller = session.get(Taller, solicitud.taller_id) if solicitud.taller_id else None
                destinatario_id = taller.propietario_id if taller else None
            else:
                vehiculo = session.get(Vehiculo, solicitud.vehiculo_id) if solicitud.vehiculo_id else None
                destinatario_id = vehiculo.propietario_id if vehiculo else None
            if not destinatario_id:
                continue

            accion_url = f"/seed/c4/notificacion/{index:02d}"
            notification = session.exec(
                select(Notificacion).where(Notificacion.accion_url == accion_url)
            ).first()
            if not notification:
                notification = Notificacion(
                    destinatario_id=destinatario_id,
                    tipo=TipoNotificacion.GENERAL if index % 3 else TipoNotificacion.TECNICO_EN_CAMINO,
                    titulo=f"Seed C4 Notificacion {index:02d}",
                    mensaje=f"Notificacion seed ciclo 4 #{index:02d}.",
                    solicitud_id=solicitud.id,
                    leida=index % 4 == 0,
                    accion_url=accion_url,
                    tenant_id=solicitud.tenant_id,
                )
                notification.fecha_creacion = BASE_TIME + timedelta(hours=80 + index)
            else:
                notification.destinatario_id = destinatario_id
                notification.tipo = TipoNotificacion.GENERAL if index % 3 else TipoNotificacion.TECNICO_EN_CAMINO
                notification.titulo = f"Seed C4 Notificacion {index:02d}"
                notification.mensaje = f"Notificacion seed ciclo 4 #{index:02d}."
                notification.solicitud_id = solicitud.id
                notification.leida = index % 4 == 0
                notification.tenant_id = solicitud.tenant_id
                notification.fecha_creacion = BASE_TIME + timedelta(hours=80 + index)
            session.add(notification)
            session.commit()
        log("Notificaciones seed listas.")


def step_tracking() -> None:
    with Session(engine) as session:
        seed_requests = session.exec(
            select(Solicitud).where(Solicitud.cliente_sync_id.like("seed-c4-req-%"))
        ).all()
        seed_request_ids = [item.id for item in seed_requests if item.id is not None]
        if seed_request_ids:
            for ping in session.exec(
                select(TrackingPing).where(TrackingPing.solicitud_id.in_(seed_request_ids))
            ).all():
                session.delete(ping)
            session.commit()

        solicitudes = session.exec(
            select(Solicitud)
            .where(Solicitud.cliente_sync_id.in_(["seed-c4-req-01", "seed-c4-req-10"]))
        ).all()
        if not solicitudes:
            solicitudes = session.exec(
                select(Solicitud)
                .where(Solicitud.cliente_sync_id.like("seed-c4-req-%"))
                .where(Solicitud.tecnico_id.is_not(None))
                .order_by(Solicitud.id.asc())
            ).all()[:2]
        if not solicitudes:
            raise RuntimeError("No hay solicitudes con tecnico para tracking.")

        selected: list[Solicitud] = []
        for sync_id in ("seed-c4-req-01", "seed-c4-req-10"):
            req = session.exec(select(Solicitud).where(Solicitud.cliente_sync_id == sync_id)).first()
            if req:
                selected.append(req)
        if not selected:
            selected = solicitudes[:2]

        for index in range(1, 11):
            solicitud = selected[(index - 1) % len(selected)]
            if not solicitud.tecnico_id:
                continue
            dt = BASE_TIME + timedelta(hours=120, minutes=index * 4)
            ping = session.exec(
                select(TrackingPing).where(
                    TrackingPing.solicitud_id == solicitud.id,
                    TrackingPing.fecha_creacion == dt,
                )
            ).first()
            lat = solicitud.latitud + 0.0015 * index
            lng = solicitud.longitud - 0.0012 * index
            if not ping:
                ping = TrackingPing(
                    solicitud_id=solicitud.id or 0,
                    tecnico_id=solicitud.tecnico_id,
                    tenant_id=solicitud.tenant_id,
                    latitud=lat,
                    longitud=lng,
                    velocidad_kmh=25 + index,
                    rumbo_grados=95 + index,
                    distancia_restante_km=max(0.2, 8.5 - index * 0.6),
                    eta_minutos=max(2, 25 - index * 2),
                )
                ping.fecha_creacion = dt
            else:
                ping.latitud = lat
                ping.longitud = lng
                ping.velocidad_kmh = 25 + index
                ping.rumbo_grados = 95 + index
                ping.distancia_restante_km = max(0.2, 8.5 - index * 0.6)
                ping.eta_minutos = max(2, 25 - index * 2)
                ping.fecha_creacion = dt
            session.add(ping)
            session.commit()
        log("Tracking pings seed listos.")


def step_summary() -> None:
    with Session(engine) as session:
        tenant_ids = [item.id for item in get_tenant_map(session).values() if item.id is not None]
        seed_request_ids = [
            item.id
            for item in session.exec(
                select(Solicitud).where(Solicitud.cliente_sync_id.like("seed-c4-req-%"))
            ).all()
            if item.id is not None
        ]
        counts = {
            "tenants_seed": len(tenant_ids),
            "conductores_seed": len(session.exec(select(User).where(User.username.like("conductor%"))).all()),
            "tecnicos_seed_usuarios": len(session.exec(select(User).where(User.username.like("tecnico%"))).all()),
            "talleres_seed": len(session.exec(select(Taller).where(Taller.tenant_id.in_(tenant_ids))).all()),
            "tecnicos_seed": len(session.exec(select(Tecnico).where(Tecnico.nombre.like("tecnico%"))).all()),
            "vehiculos_seed": len(session.exec(select(Vehiculo).where(Vehiculo.placa.like("SCZ%"))).all()),
            "solicitudes_seed": len(seed_request_ids),
            "cotizaciones_seed": len(session.exec(select(Cotizacion).where(Cotizacion.descripcion.like("[SEED-C4-COT-%"))).all()),
            "historial_vehicular_seed": len(session.exec(select(VehiculoHistorialReparacion).where(VehiculoHistorialReparacion.solicitud_id.in_(seed_request_ids))).all()) if seed_request_ids else 0,
            "subscription_payments_seed": len(session.exec(select(SubscriptionPaymentMock).where(SubscriptionPaymentMock.referencia.like("seed-c4-subpay-%"))).all()),
            "service_payments_seed": len(session.exec(select(Pago).where(Pago.referencia.like("seed-c4-servicepay-%"))).all()),
            "notificaciones_seed": len(session.exec(select(Notificacion).where(Notificacion.accion_url.like("/seed/c4/notificacion/%"))).all()),
            "tracking_seed": len(session.exec(select(TrackingPing).where(TrackingPing.solicitud_id.in_(seed_request_ids))).all()) if seed_request_ids else 0,
        }
        for key, value in counts.items():
            log(f"{key}: {value}")
        log(f"Password comun de usuarios seed: {PASSWORD}")


def run_all() -> None:
    for step in (
        step_bootstrap,
        step_tenants,
        step_workshops,
        step_drivers,
        step_technicians,
        step_vehicles,
        step_requests,
        step_quotes,
        step_payments,
        step_notifications,
        step_tracking,
        step_summary,
    ):
        step()


def main() -> None:
    args = parse_args()
    actions = {
        "bootstrap": step_bootstrap,
        "tenants": step_tenants,
        "workshops": step_workshops,
        "drivers": step_drivers,
        "technicians": step_technicians,
        "vehicles": step_vehicles,
        "requests": step_requests,
        "quotes": step_quotes,
        "payments": step_payments,
        "notifications": step_notifications,
        "tracking": step_tracking,
        "summary": step_summary,
        "all": run_all,
    }
    actions[args.step]()


if __name__ == "__main__":
    main()
