"""Inicialización de la base de datos.

Estrategia:
* `SQLModel.metadata.create_all` para crear tablas nuevas.
* `ensure_legacy_schema` aplica ALTERs idempotentes (`ADD COLUMN IF NOT EXISTS`)
  para evolucionar la BD sin migrar Alembic todavía. Cada vez que se agrega
  una columna nueva al dominio, se añade aquí el statement correspondiente.
* `seed_default_tenant` crea el Tenant `default` y back-fillea los registros
  legacy (tenant_id NULL) hacia ese tenant. Esto garantiza que al introducir
  multi-tenant sobre datos existentes nada quede huérfano.
* `seed_admin` crea el usuario admin si no existe (sin tenant — admin global).
"""

import os
import time

import bcrypt
from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine, select

from app.models.user import User, UserRole

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


def ensure_legacy_schema():
    """ALTERs idempotentes para evolucionar la BD sin Alembic.

    Cada bloque corresponde a una migración mental. El orden importa solo
    cuando hay dependencias; en general estos statements son safe-to-rerun.
    """
    statements = [
        # Columnas que evolucionaron en `solicitud` durante el MVP.
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS tiempo_estimado_minutos INTEGER",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS estado_pago VARCHAR(20) DEFAULT 'pendiente'",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS fecha_pago TIMESTAMP NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS especialidad_requerida_ia VARCHAR NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS distancia_estimada_km DOUBLE PRECISION NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS asignacion_score DOUBLE PRECISION NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS cliente_sync_id VARCHAR NULL",
        "ALTER TABLE taller ADD COLUMN IF NOT EXISTS capacidad_operativa INTEGER DEFAULT 3",
        "ALTER TABLE taller ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE",
        "ALTER TABLE taller ADD COLUMN IF NOT EXISTS especialidades VARCHAR DEFAULT 'General'",
        "UPDATE taller SET especialidades = 'General' WHERE especialidades IS NULL",
        "ALTER TABLE taller ALTER COLUMN especialidades SET DEFAULT 'General'",
        "ALTER TABLE taller ALTER COLUMN especialidades DROP NOT NULL",
        # Multi-tenant SaaS.
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL',
        "ALTER TABLE taller ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE tecnico ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE pago ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE calificacion_servicio ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE chat_mensaje ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE notificacion ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE analisis_ia ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE cotizacion ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE solicitud_candidato ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE solicitud_historial ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        "ALTER TABLE tracking_ping ADD COLUMN IF NOT EXISTS tenant_id INTEGER NULL",
        # Solicitud: campos para KPIs (tiempos por etapa) + cotización seleccionada.
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS sla_esperado_minutos INTEGER DEFAULT 60",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS fecha_taller_asignado TIMESTAMP NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS fecha_tecnico_llego TIMESTAMP NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS fecha_finalizado TIMESTAMP NULL",
        "ALTER TABLE solicitud ADD COLUMN IF NOT EXISTS cotizacion_seleccionada_id INTEGER NULL",
        # Tracking de técnico vivo en `tecnico`.
        "ALTER TABLE tecnico ADD COLUMN IF NOT EXISTS latitud_actual DOUBLE PRECISION NULL",
        "ALTER TABLE tecnico ADD COLUMN IF NOT EXISTS longitud_actual DOUBLE PRECISION NULL",
        "ALTER TABLE tecnico ADD COLUMN IF NOT EXISTS ultima_actualizacion_ubicacion TIMESTAMP NULL",
        "ALTER TABLE tecnico ADD COLUMN IF NOT EXISTS ci VARCHAR(10) NULL",
        "ALTER TABLE tecnico ADD COLUMN IF NOT EXISTS direccion VARCHAR NULL",
        "ALTER TABLE tecnico ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE",
        "ALTER TABLE tecnico ADD COLUMN IF NOT EXISTS id_usuario INTEGER NULL",
        # placa: pasamos de UNIQUE global a índice no único (la unicidad pasa a
        # ser por (tenant_id, placa) verificada en aplicación).
        "ALTER TABLE vehiculo DROP CONSTRAINT IF EXISTS vehiculo_placa_key",
        # ESTADOSOLICITUD: la columna se persiste como VARCHAR pero SQLAlchemy
        # mapea por NOMBRE de miembro (mayúsculas), no por valor. Tras consolidar
        # el enum a 8 canónicos con aliases retro-compat, normalizamos los
        # valores almacenados (mezcla de mayúsculas/minúsculas históricas) a la
        # forma uppercase canónica que SQLAlchemy espera.
        "ALTER TABLE solicitud ALTER COLUMN estado TYPE VARCHAR USING estado::text",
        # Primero, alias retro-compat (CANCELADA → CANCELADO, etc.).
        "UPDATE solicitud SET estado = 'cancelado' WHERE LOWER(estado) IN ('cancelada')",
        "UPDATE solicitud SET estado = 'finalizado' WHERE LOWER(estado) IN ('resuelta')",
        "UPDATE solicitud SET estado = 'en_proceso' WHERE LOWER(estado) IN ('en_progreso')",
        "UPDATE solicitud SET estado = 'tecnico_llego' WHERE LOWER(estado) IN ('llegada')",
        # Después, todos los valores en lowercase a UPPERCASE (formato esperado
        # por SQLAlchemy NAME-based enum lookup).
        "UPDATE solicitud SET estado = UPPER(estado)",
        # Eliminamos el tipo enum legacy si quedó huérfano.
        "DROP TYPE IF EXISTS estadosolicitud CASCADE",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def seed_default_tenant():
    """Crea el Tenant `default` si no existe y back-fillea registros legacy."""
    from app.models.domain import Tenant  # import diferido: evita ciclos

    with Session(engine) as session:
        default = session.exec(select(Tenant).where(Tenant.slug == "default")).first()
        if not default:
            default = Tenant(
                nombre="Plataforma Default",
                slug="default",
                descripcion="Tenant base creado automáticamente para datos legacy.",
            )
            session.add(default)
            session.commit()
            session.refresh(default)
            print(f"Tenant 'default' creado con id={default.id}")

        # Backfill: datos operativos legacy sin tenant van al tenant default.
        # El usuario seed `admin` se promueve a superadmin global en `seed_admin`.
        backfill_tables = [
            '"user"',
            "taller",
            "tecnico",
            "vehiculo",
            "solicitud",
            "pago",
            "calificacion_servicio",
            "chat_mensaje",
            "notificacion",
            "audit_log",
            "analisis_ia",
            "cotizacion",
            "solicitud_candidato",
            "solicitud_historial",
            "tracking_ping",
        ]
        with engine.begin() as connection:
            for table in backfill_tables:
                connection.execute(text(
                    f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL"
                ), {"tid": default.id})


def seed_saas_plans():
    """Crea/actualiza los planes SaaS comerciales del sistema."""
    from app.models.domain import SaaSPlan

    plans = [
        {
            "codigo": "gratis",
            "nombre": "Gratis",
            "descripcion": "Plan inicial para validar un taller pequeno.",
            "precio_mensual": 0.0,
            "max_administradores": 1,
            "max_mecanicos": 5,
            "max_solicitudes_mes": 30,
            "beneficios": "1 administrador|5 mecanicos|30 solicitudes al mes|Dashboard basico|Tracking en tiempo real|Cotizaciones basicas",
        },
        {
            "codigo": "intermedio",
            "nombre": "Intermedio",
            "descripcion": "Operacion diaria con mas equipo y analitica.",
            "precio_mensual": 149.0,
            "max_administradores": 3,
            "max_mecanicos": 10,
            "max_solicitudes_mes": 200,
            "beneficios": "3 administradores|10 mecanicos|200 solicitudes al mes|KPIs operativos|Historial avanzado|Soporte por correo",
        },
        {
            "codigo": "premium",
            "nombre": "Premium",
            "descripcion": "Para talleres con alto volumen operativo.",
            "precio_mensual": 299.0,
            "max_administradores": 10,
            "max_mecanicos": 20,
            "max_solicitudes_mes": 1000,
            "beneficios": "10 administradores|20 mecanicos|1000 solicitudes al mes|Dashboard avanzado|Auditoria|Reportes exportables|Soporte prioritario",
        },
        {
            "codigo": "pro",
            "nombre": "Pro",
            "descripcion": "Escala completa sin limites de usuarios operativos.",
            "precio_mensual": 599.0,
            "max_administradores": None,
            "max_mecanicos": None,
            "max_solicitudes_mes": None,
            "beneficios": "Administradores ilimitados|Mecanicos ilimitados|Solicitudes ilimitadas|Analitica avanzada|Auditoria completa|Integraciones futuras|Soporte premium",
        },
    ]

    with Session(engine) as session:
        for data in plans:
            plan = session.exec(select(SaaSPlan).where(SaaSPlan.codigo == data["codigo"])).first()
            if not plan:
                plan = SaaSPlan(**data)
            else:
                for key, value in data.items():
                    setattr(plan, key, value)
                plan.activo = True
            session.add(plan)
        session.commit()


def seed_default_subscriptions():
    """Asigna plan gratis activo a tenants existentes sin suscripcion activa."""
    from app.models.domain import SaaSPlan, Tenant, TenantSubscription

    with Session(engine) as session:
        free_plan = session.exec(select(SaaSPlan).where(SaaSPlan.codigo == "gratis")).first()
        if not free_plan or free_plan.id is None:
            return

        tenants = session.exec(select(Tenant)).all()
        for tenant in tenants:
            if tenant.id is None:
                continue
            active = session.exec(
                select(TenantSubscription)
                .where(TenantSubscription.tenant_id == tenant.id)
                .where(TenantSubscription.estado == "activa")
            ).first()
            if active:
                continue
            session.add(TenantSubscription(
                tenant_id=tenant.id,
                plan_id=free_plan.id,
                estado="activa",
            ))
        session.commit()


def seed_default_specialties():
    """Crea especialidades base para onboarding y gestion de mecanicos."""
    from app.models.domain import Especialidad, EspecialidadTaller

    names = [
        "Bateria",
        "Llantas",
        "Motor",
        "Frenos",
        "Electricidad",
        "Auxilio general",
    ]
    with Session(engine) as session:
        for name in names:
            if not session.exec(select(EspecialidadTaller).where(EspecialidadTaller.nombre == name)).first():
                session.add(EspecialidadTaller(nombre=name))
            if not session.exec(select(Especialidad).where(Especialidad.nombre == name)).first():
                session.add(Especialidad(nombre=name))
        session.commit()


def seed_admin():
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            admin_user = User(
                username="admin",
                email="admin@sistemamecanico.com",
                full_name="Administrador",
                role=UserRole.ADMIN,
                is_active=True,
                tenant_id=None,  # admin global multi-tenant
            )
            admin_user.hashed_password = bcrypt.hashpw(
                "admin123".encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            session.add(admin_user)
            session.commit()
            print("Usuario admin creado con éxito!")
        elif admin.role == UserRole.ADMIN and admin.tenant_id is not None:
            admin.tenant_id = None
            session.add(admin)
            session.commit()
            print("Usuario admin promovido a superadmin global.")


def init_db():
    max_retries = int(os.getenv("DB_INIT_MAX_RETRIES", "10"))
    retry_delay = int(os.getenv("DB_INIT_RETRY_DELAY_SECONDS", "3"))

    for attempt in range(1, max_retries + 1):
        try:
            SQLModel.metadata.create_all(engine)
            ensure_legacy_schema()
            break
        except OperationalError:
            if attempt == max_retries:
                raise
            print(
                f"Base de datos no disponible. Reintento {attempt}/{max_retries} en {retry_delay}s..."
            )
            time.sleep(retry_delay)

    seed_default_tenant()
    seed_saas_plans()
    seed_default_subscriptions()
    seed_default_specialties()
    seed_admin()


def get_session():
    with Session(engine) as session:
        yield session
