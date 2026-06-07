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
)
from app.models.user import User, UserRole


PASSWORD = "Prueba*2026"
BASE_TIME = datetime.utcnow().replace(microsecond=0) - timedelta(days=5)
PLANS_BY_INDEX = ["gratis", "intermedio", "premium", "pro"]


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
    TenantSeed(
        slug="seed-c4-norte",
        nombre="Red Norte",
        descripcion="Tenant seed ciclo 4 - red norte.",
        plan_codigo="gratis",
        taller_nombre="Taller Norte Motors",
        direccion="Av. Busch #100, La Paz",
        telefono="72000001",
        lat=-16.4995,
        lng=-68.1240,
        especialidades=("Bateria", "Electricidad", "Auxilio general"),
    ),
    TenantSeed(
        slug="seed-c4-centro",
        nombre="Red Centro",
        descripcion="Tenant seed ciclo 4 - red centro.",
        plan_codigo="intermedio",
        taller_nombre="Centro Diesel Service",
        direccion="Calle Comercio #220, La Paz",
        telefono="72000002",
        lat=-16.4950,
        lng=-68.1335,
        especialidades=("Motor", "Frenos", "Auxilio general"),
    ),
    TenantSeed(
        slug="seed-c4-sur",
        nombre="Red Sur",
        descripcion="Tenant seed ciclo 4 - red sur.",
        plan_codigo="premium",
        taller_nombre="Sur Auto Rescue",
        direccion="Calacoto, Calle 17 #55, La Paz",
        telefono="72000003",
        lat=-16.5391,
        lng=-68.0728,
        especialidades=("Llantas", "Motor", "Auxilio general"),
    ),
    TenantSeed(
        slug="seed-c4-elalto",
        nombre="Red El Alto",
        descripcion="Tenant seed ciclo 4 - red el alto.",
        plan_codigo="pro",
        taller_nombre="Altiplano Taller Express",
        direccion="Ceja de El Alto #80, El Alto",
        telefono="72000004",
        lat=-16.5047,
        lng=-68.1644,
        especialidades=("Bateria", "Llantas", "Auxilio general"),
    ),
)


DRIVER_ASSIGNMENTS = [
    ("seed_driver_01", "driver01@seedc4.test", "Conductor Uno", "seed-c4-norte"),
    ("seed_driver_02", "driver02@seedc4.test", "Conductor Dos", "seed-c4-centro"),
    ("seed_driver_03", "driver03@seedc4.test", "Conductor Tres", "seed-c4-sur"),
    ("seed_driver_04", "driver04@seedc4.test", "Conductor Cuatro", "seed-c4-elalto"),
    ("seed_driver_05", "driver05@seedc4.test", "Conductor Cinco", "seed-c4-norte"),
]


REQUEST_TEMPLATES = [
    ("seed-c4-req-01", "seed_driver_01", "seed-c4-norte", EstadoSolicitud.FINALIZADO, "Problema de bateria o sistema electrico", "Alta", 0.0, 0.0),
    ("seed-c4-req-02", "seed_driver_02", "seed-c4-centro", EstadoSolicitud.FINALIZADO, "Problema de llanta o neumatico", "Media", 0.01, -0.01),
    ("seed-c4-req-03", "seed_driver_03", "seed-c4-sur", EstadoSolicitud.FINALIZADO, "Problema de motor o recalentamiento", "Alta", -0.01, 0.01),
    ("seed-c4-req-04", "seed_driver_04", "seed-c4-elalto", EstadoSolicitud.FINALIZADO, "Incidente general", "Media", 0.015, -0.008),
    ("seed-c4-req-05", "seed_driver_05", "seed-c4-norte", EstadoSolicitud.FINALIZADO, "Problema de bateria o sistema electrico", "Alta", -0.012, 0.012),
    ("seed-c4-req-06", "seed_driver_01", "seed-c4-norte", EstadoSolicitud.FINALIZADO, "Problema de llanta o neumatico", "Media", 0.018, -0.006),
    ("seed-c4-req-07", "seed_driver_02", "seed-c4-centro", EstadoSolicitud.FINALIZADO, "Problema de motor o recalentamiento", "Alta", -0.008, 0.014),
    ("seed-c4-req-08", "seed_driver_03", "seed-c4-sur", EstadoSolicitud.FINALIZADO, "Incidente general", "Media", 0.014, 0.008),
    ("seed-c4-req-09", "seed_driver_04", "seed-c4-elalto", EstadoSolicitud.CANCELADO, "Problema de llanta o neumatico", "Media", -0.015, -0.01),
    ("seed-c4-req-10", "seed_driver_05", "seed-c4-norte", EstadoSolicitud.EN_PROCESO, "Problema de bateria o sistema electrico", "Alta", 0.006, 0.015),
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
                email=f"owner{index:02d}@seedc4.test",
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
                    email_contacto=f"contacto{index:02d}@seedc4.test",
                    horario_atencion="Lunes-Domingo 06:00-22:00",
                    descripcion=f"Taller seed para {item.nombre}.",
                    sitio_web=f"https://{item.slug}.seedc4.test",
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
                taller.email_contacto = f"contacto{index:02d}@seedc4.test"
                taller.horario_atencion = "Lunes-Domingo 06:00-22:00"
                taller.descripcion = f"Taller seed para {item.nombre}."
                taller.sitio_web = f"https://{item.slug}.seedc4.test"
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

            for tech_number in range(1, 4):
                username = f"seed_tech_{index:02d}_{tech_number:02d}"
                user = ensure_user(
                    session,
                    username=username,
                    email=f"{username}@seedc4.test",
                    full_name=f"Tecnico {index}-{tech_number}",
                    role=UserRole.TECNICO,
                    tenant_id=tenant.id,
                    telefono=f"750{index:02d}{tech_number:02d}",
                )
                ci = f"{index}{tech_number}12345"
                tecnico = session.exec(
                    select(Tecnico).where(Tecnico.id_usuario == user.id)
                ).first()
                if not tecnico:
                    tecnico = Tecnico(
                        nombre=f"Tecnico {index}-{tech_number}",
                        ci=ci,
                        direccion=f"Zona operativa {tech_number} - {item.nombre}",
                        latitud=item.lat + tech_number * 0.002,
                        longitud=item.lng - tech_number * 0.002,
                        latitud_actual=item.lat + tech_number * 0.0025,
                        longitud_actual=item.lng - tech_number * 0.0025,
                        ultima_actualizacion_ubicacion=BASE_TIME + timedelta(hours=tech_number),
                        disponible=tech_number != 3,
                        activo=True,
                        taller_id=taller.id,
                        id_usuario=user.id,
                        tenant_id=tenant.id,
                    )
                else:
                    tecnico.nombre = f"Tecnico {index}-{tech_number}"
                    tecnico.ci = ci
                    tecnico.direccion = f"Zona operativa {tech_number} - {item.nombre}"
                    tecnico.latitud = item.lat + tech_number * 0.002
                    tecnico.longitud = item.lng - tech_number * 0.002
                    tecnico.latitud_actual = item.lat + tech_number * 0.0025
                    tecnico.longitud_actual = item.lng - tech_number * 0.0025
                    tecnico.ultima_actualizacion_ubicacion = BASE_TIME + timedelta(hours=tech_number)
                    tecnico.disponible = tech_number != 3
                    tecnico.activo = True
                    tecnico.taller_id = taller.id
                    tecnico.id_usuario = user.id
                    tecnico.tenant_id = tenant.id
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
    with Session(engine) as session:
        for index, (username, _email, _full_name, _tenant_slug) in enumerate(DRIVER_ASSIGNMENTS, start=1):
            user = session.exec(select(User).where(User.username == username)).first()
            if not user:
                raise RuntimeError(f"No existe conductor {username}")
            placa = f"SC4{index:03d}LP"
            vehicle = session.exec(select(Vehiculo).where(Vehiculo.placa == placa)).first()
            if not vehicle:
                vehicle = Vehiculo(
                    placa=placa,
                    marca=["Toyota", "Nissan", "Suzuki", "Kia", "Hyundai"][index - 1],
                    modelo=["Corolla", "Frontier", "Swift", "Rio", "Accent"][index - 1],
                    color=["Blanco", "Gris", "Rojo", "Azul", "Negro"][index - 1],
                    propietario_id=user.id,
                    tenant_id=user.tenant_id,
                )
            else:
                vehicle.marca = ["Toyota", "Nissan", "Suzuki", "Kia", "Hyundai"][index - 1]
                vehicle.modelo = ["Corolla", "Frontier", "Swift", "Rio", "Accent"][index - 1]
                vehicle.color = ["Blanco", "Gris", "Rojo", "Azul", "Negro"][index - 1]
                vehicle.propietario_id = user.id
                vehicle.tenant_id = user.tenant_id
            session.add(vehicle)
            session.commit()
            log(f"Vehiculo listo: {placa}")


def _tecnico_for_taller(session: Session, taller_id: int) -> Tecnico | None:
    return session.exec(
        select(Tecnico)
        .where(Tecnico.taller_id == taller_id)
        .order_by(Tecnico.id.asc())
    ).first()


def step_requests() -> None:
    with Session(engine) as session:
        tenant_map = get_tenant_map(session)
        for index, (sync_id, driver_username, tenant_slug, state, clasificacion, prioridad, dlat, dlng) in enumerate(REQUEST_TEMPLATES, start=1):
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
            tecnico = _tecnico_for_taller(session, taller.id) if taller and taller.id else None
            created_at = BASE_TIME + timedelta(hours=index * 3)
            assigned_at = created_at + timedelta(minutes=12 + index) if state in {
                EstadoSolicitud.ASIGNADA,
                EstadoSolicitud.TECNICO_EN_CAMINO,
                EstadoSolicitud.TECNICO_LLEGO,
                EstadoSolicitud.EN_PROCESO,
                EstadoSolicitud.FINALIZADO,
            } else None
            arrived_at = assigned_at + timedelta(minutes=18 + index) if state in {
                EstadoSolicitud.TECNICO_LLEGO,
                EstadoSolicitud.EN_PROCESO,
                EstadoSolicitud.FINALIZADO,
            } and assigned_at else None
            finished_at = arrived_at + timedelta(minutes=35 + index) if state == EstadoSolicitud.FINALIZADO and arrived_at else None

            solicitud = session.exec(
                select(Solicitud).where(Solicitud.cliente_sync_id == sync_id)
            ).first()
            if not solicitud:
                solicitud = Solicitud(
                    descripcion=f"[{sync_id}] Emergencia seed ciclo 4 #{index}",
                    latitud=(taller.latitud if taller and taller.latitud is not None else tenant.lat) + dlat,
                    longitud=(taller.longitud if taller and taller.longitud is not None else tenant.lng) + dlng,
                    estado=state,
                    clasificacion_ia=clasificacion,
                    prioridad_ia=prioridad,
                    resumen_ia=f"Resumen seed para {clasificacion.lower()}",
                    especialidad_requerida_ia=infer_specialty(clasificacion),
                    distancia_estimada_km=round(2.5 + index * 0.8, 2),
                    asignacion_score=round(0.65 + index * 0.02, 2),
                    tiempo_estimado_minutos=20 + index * 3,
                    estado_pago="pendiente",
                    vehiculo_id=vehicle.id if vehicle else None,
                    taller_id=taller.id if assigned_at and taller else None,
                    tecnico_id=tecnico.id if assigned_at and tecnico else None,
                    tenant_id=tenant.id,
                    cliente_sync_id=sync_id,
                    sla_esperado_minutos=60 + (index % 3) * 15,
                    fecha_taller_asignado=assigned_at,
                    fecha_tecnico_llego=arrived_at,
                    fecha_finalizado=finished_at,
                )
                solicitud.fecha_creacion = created_at
            else:
                solicitud.descripcion = f"[{sync_id}] Emergencia seed ciclo 4 #{index}"
                solicitud.latitud = (taller.latitud if taller and taller.latitud is not None else tenant.lat) + dlat
                solicitud.longitud = (taller.longitud if taller and taller.longitud is not None else tenant.lng) + dlng
                solicitud.estado = state
                solicitud.clasificacion_ia = clasificacion
                solicitud.prioridad_ia = prioridad
                solicitud.resumen_ia = f"Resumen seed para {clasificacion.lower()}"
                solicitud.especialidad_requerida_ia = infer_specialty(clasificacion)
                solicitud.distancia_estimada_km = round(2.5 + index * 0.8, 2)
                solicitud.asignacion_score = round(0.65 + index * 0.02, 2)
                solicitud.tiempo_estimado_minutos = 20 + index * 3
                solicitud.estado_pago = "pendiente"
                solicitud.vehiculo_id = vehicle.id if vehicle else None
                solicitud.taller_id = taller.id if assigned_at and taller else None
                solicitud.tecnico_id = tecnico.id if assigned_at and tecnico else None
                solicitud.tenant_id = tenant.id
                solicitud.sla_esperado_minutos = 60 + (index % 3) * 15
                solicitud.fecha_taller_asignado = assigned_at
                solicitud.fecha_tecnico_llego = arrived_at
                solicitud.fecha_finalizado = finished_at
                solicitud.fecha_creacion = created_at
            session.add(solicitud)
            session.commit()
            log(f"Solicitud lista: {sync_id}")


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

        for index in range(1, 11):
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
                    contacto_email=f"billing{index:02d}@seedc4.test",
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
                payment.contacto_email = f"billing{index:02d}@seedc4.test"
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
        ).all()[:5]
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
            "users_seed": len(session.exec(select(User).where(User.username.like("seed_%"))).all()),
            "talleres_seed": len(session.exec(select(Taller).where(Taller.tenant_id.in_(tenant_ids))).all()),
            "tecnicos_seed": len(session.exec(select(Tecnico).where(Tecnico.nombre.like("Tecnico %"))).all()),
            "vehiculos_seed": len(session.exec(select(Vehiculo).where(Vehiculo.placa.like("SC4%"))).all()),
            "solicitudes_seed": len(seed_request_ids),
            "cotizaciones_seed": len(session.exec(select(Cotizacion).where(Cotizacion.descripcion.like("[SEED-C4-COT-%"))).all()),
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
