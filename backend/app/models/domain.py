from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum


# ============================================================================
# MULTI-TENANT SaaS
# ----------------------------------------------------------------------------
# Cada organización (red de talleres, empresa) es un Tenant. Todos los
# recursos transaccionales del sistema (talleres, técnicos, solicitudes,
# vehículos, pagos, calificaciones, chat, notificaciones, audit log) llevan
# un `tenant_id` que aísla los datos lógicamente. El backend usa middleware
# + dependencias FastAPI para garantizar que cada request opere solo dentro
# del tenant del usuario autenticado.
#
# Decisiones:
# * `tenant_id` es Optional para retrocompatibilidad con datos pre-tenant.
#   En el seed se crea un tenant "default" y se backfilea.
# * El usuario ADMIN puede pertenecer a un tenant operativo o ser global
#   (tenant_id NULL) para poder gestionar varios tenants desde un panel.
# * Slug único legible (`tenant.slug`) para URLs subdomain-style si en el
#   futuro queremos `auxilio-norte.app.com`.
# ============================================================================


class TenantBase(SQLModel):
    nombre: str = Field(index=True)
    slug: str = Field(index=True, unique=True, max_length=60)
    descripcion: Optional[str] = None
    activo: bool = Field(default=True, index=True)


class Tenant(TenantBase, table=True):
    __tablename__ = "tenant"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)


class TenantCreate(SQLModel):
    nombre: str
    slug: str
    descripcion: Optional[str] = None


class TenantUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


class TenantRead(TenantBase):
    id: int
    fecha_creacion: datetime


class SaaSPlan(SQLModel, table=True):
    """Plan comercial del SaaS.

    Los limites en `None` significan uso ilimitado (plan Pro). Se usan enteros
    positivos para planes limitados porque el servicio de limites compara contra
    conteos reales de usuarios/mecanicos por tenant.
    """

    __tablename__ = "saas_plan"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True, max_length=30)
    nombre: str
    descripcion: Optional[str] = None
    precio_mensual: float = Field(default=0.0)
    max_administradores: Optional[int] = Field(default=None)
    max_mecanicos: Optional[int] = Field(default=None)
    max_solicitudes_mes: Optional[int] = Field(default=None)
    beneficios: str = Field(default="")
    activo: bool = Field(default=True, index=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)


class SaaSPlanRead(SQLModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    precio_mensual: float
    max_administradores: Optional[int] = None
    max_mecanicos: Optional[int] = None
    max_solicitudes_mes: Optional[int] = None
    beneficios: List[str] = Field(default_factory=list)
    activo: bool


class TenantSubscription(SQLModel, table=True):
    __tablename__ = "tenant_subscription"

    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    plan_id: int = Field(foreign_key="saas_plan.id", index=True)
    estado: str = Field(default="activa", index=True)
    fecha_inicio: datetime = Field(default_factory=datetime.utcnow)
    fecha_fin: Optional[datetime] = None
    pago_mock_id: Optional[int] = Field(default=None, foreign_key="subscription_payment_mock.id")
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionPaymentMock(SQLModel, table=True):
    __tablename__ = "subscription_payment_mock"

    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="saas_plan.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    monto: float = Field(default=0.0)
    moneda: str = Field(default="BOB", max_length=10)
    estado: str = Field(default="pendiente_pago", index=True)
    referencia: str = Field(index=True, unique=True)
    metodo: str = Field(default="mock")
    contacto_email: Optional[str] = None
    contacto_nombre: Optional[str] = None
    onboarding_token: Optional[str] = Field(default=None, index=True, unique=True)
    usado: bool = Field(default=False, index=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    fecha_pago: Optional[datetime] = None


class PlanCheckoutCreate(SQLModel):
    plan_codigo: str
    email: str
    nombre_contacto: Optional[str] = None


class PlanCheckoutRead(SQLModel):
    checkout_id: int
    referencia: str
    estado: str
    monto: float
    moneda: str
    plan: SaaSPlanRead


class PlanPaymentRead(SQLModel):
    checkout_id: int
    estado: str
    onboarding_token: str
    plan_codigo: str


class OnboardingAdminCreate(SQLModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str


class SubscriptionCurrentRead(SQLModel):
    plan: SaaSPlanRead
    estado: str
    uso: dict
    limites: dict


class WorkshopAdminCreate(SQLModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str


class WorkshopAdminRead(SQLModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    tenant_id: Optional[int] = None

class EstadoSolicitud(str, Enum):
    # Canonical 8 states (per spec Uber/Yango-style flow).
    PENDIENTE = "pendiente"
    BUSCANDO_TALLER = "buscando_taller"
    ASIGNADA = "asignada"
    TECNICO_EN_CAMINO = "tecnico_en_camino"
    TECNICO_LLEGO = "tecnico_llego"
    EN_PROCESO = "en_proceso"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"
    # Backwards-compat aliases: re-using the same string value makes Python
    # Enum treat them as alias members pointing to the canonical one above.
    # Existing code that references `.RESUELTA`/`.CANCELADA`/`.EN_PROGRESO`/`.LLEGADA`
    # keeps working, but the DB only ever stores the canonical value.
    RESUELTA = "finalizado"
    CANCELADA = "cancelado"
    EN_PROGRESO = "en_proceso"
    LLEGADA = "tecnico_llego"


class TipoNotificacion(str, Enum):
    NUEVA_SOLICITUD_TALLER = "nueva_solicitud_taller"
    SOLICITUD_ACEPTADA_CONDUCTOR = "solicitud_aceptada_conductor"
    TECNICO_ASIGNADO = "tecnico_asignado"
    TECNICO_EN_CAMINO = "tecnico_en_camino"
    TECNICO_LLEGO = "tecnico_llego"
    SOLICITUD_CANCELADA_CONDUCTOR = "solicitud_cancelada_conductor"
    SOLICITUD_CANCELADA_TALLER = "solicitud_cancelada_taller"
    SOLICITUD_CANCELADA_MECANICO = "solicitud_cancelada_mecanico"
    SERVICIO_TERMINADO = "servicio_terminado"
    SERVICIO_CONCLUIDO_PAGO = "servicio_concluido_pago"
    GENERAL = "general"


class NotificacionBase(SQLModel):
    destinatario_id: int = Field(foreign_key="user.id", index=True)
    tipo: TipoNotificacion = Field(default=TipoNotificacion.GENERAL, index=True)
    titulo: str
    mensaje: str
    solicitud_id: Optional[int] = Field(default=None, foreign_key="solicitud.id", index=True)
    leida: bool = Field(default=False, index=True)
    accion_url: Optional[str] = None
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)


class Notificacion(NotificacionBase, table=True):
    __tablename__ = "notificacion"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)


class NotificacionCreate(SQLModel):
    destinatario_id: int
    tipo: TipoNotificacion = TipoNotificacion.GENERAL
    titulo: str
    mensaje: str
    solicitud_id: Optional[int] = None
    accion_url: Optional[str] = None


class NotificacionRead(NotificacionBase):
    id: int
    fecha_creacion: datetime


class NotificacionesNoLeidasRead(SQLModel):
    total: int


class DispositivoTokenBase(SQLModel):
    usuario_id: int = Field(foreign_key="user.id", index=True)
    token: str = Field(index=True, unique=True)
    plataforma: str = Field(default="android", max_length=30)
    activo: bool = Field(default=True, index=True)


class DispositivoToken(DispositivoTokenBase, table=True):
    __tablename__ = "dispositivo_token"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow)


class DispositivoTokenCreate(SQLModel):
    token: str
    plataforma: str = "android"


class DispositivoTokenRead(DispositivoTokenBase):
    id: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime

class VehiculoBase(SQLModel):
    # NOTE: la placa NO es globalmente única en una plataforma multi-tenant
    # porque la misma placa puede registrarse en dos tenants distintos. Se
    # mantiene índice no único; la unicidad se verifica al nivel de aplicación
    # por (tenant_id, placa) en el repositorio.
    placa: str = Field(index=True)
    marca: str
    modelo: str
    color: Optional[str] = None
    propietario_id: Optional[int] = Field(default=None, foreign_key="user.id")
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)

class Vehiculo(VehiculoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    propietario: Optional["User"] = Relationship(back_populates="vehiculos")
    solicitudes: List["Solicitud"] = Relationship(back_populates="vehiculo")


class VehiculoCreate(VehiculoBase):
    pass


class VehiculoRead(VehiculoBase):
    id: int


class VehiculoUpdate(SQLModel):
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    color: Optional[str] = None


class EspecialidadBase(SQLModel):
    nombre: str = Field(index=True, unique=True)


class TecnicosEspecialidades(SQLModel, table=True):
    __tablename__ = "tecnicos_especialidades"

    tecnico_id: Optional[int] = Field(default=None, foreign_key="tecnico.id", primary_key=True)
    especialidad_id: Optional[int] = Field(default=None, foreign_key="especialidad.id", primary_key=True)


class Especialidad(EspecialidadBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tecnicos: List["Tecnico"] = Relationship(
        back_populates="especialidades",
        link_model=TecnicosEspecialidades
    )

class EspecialidadCreate(SQLModel):
    nombre: str

class EspecialidadRead(SQLModel):
    id: int
    nombre: str

class TalleresEspecialidades(SQLModel, table=True):
    __tablename__ = "talleres_especialidades"

    taller_id: Optional[int] = Field(default=None, foreign_key="taller.id", primary_key=True)
    especialidad_id: Optional[int] = Field(default=None, foreign_key="especialidades_taller.id", primary_key=True)


class EspecialidadTallerBase(SQLModel):
    nombre: str


class EspecialidadTaller(EspecialidadTallerBase, table=True):
    __tablename__ = "especialidades_taller"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True)
    talleres: List["Taller"] = Relationship(
        back_populates="especialidades",
        link_model=TalleresEspecialidades
    )

class EspecialidadTallerRead(SQLModel):
    id: int
    nombre: str

class TecnicoBase(SQLModel):
    nombre: str
    ci: str = Field(index=True, unique=True, max_length=10)
    direccion: str
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    # Last known live tracking position (updated via tracking endpoint / WS).
    # Kept separate from base latitud/longitud so the "home" coords remain stable
    # even when the technician is moving.
    latitud_actual: Optional[float] = None
    longitud_actual: Optional[float] = None
    ultima_actualizacion_ubicacion: Optional[datetime] = None
    disponible: bool = True
    activo: bool = True
    taller_id: Optional[int] = Field(default=None, foreign_key="taller.id")
    id_usuario: Optional[int] = Field(default=None, foreign_key="user.id", unique=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)

class Tecnico(TecnicoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    taller: Optional["Taller"] = Relationship(back_populates="tecnicos")
    usuario: Optional["User"] = Relationship(back_populates="tecnico_perfil")
    especialidades: List[Especialidad] = Relationship(
        back_populates="tecnicos",
        link_model=TecnicosEspecialidades
    )
    solicitudes_atendidas: List["Solicitud"] = Relationship(back_populates="tecnico_asignado")


class TecnicoRead(TecnicoBase):
    id: int
    especialidades: List[EspecialidadRead] = Field(default_factory=list)
    usuario_username: Optional[str] = None
    password_temporal: Optional[str] = None

class SolicitudBase(SQLModel):
    descripcion: str
    latitud: float
    longitud: float
    estado: EstadoSolicitud = Field(default=EstadoSolicitud.PENDIENTE)
    
    # Costos para la pasarela de pago (Comisión 10%)
    precio_cobrado: Optional[float] = None
    comision_plataforma: Optional[float] = None # 10%
    
    # Información enriquecida por IA
    clasificacion_ia: Optional[str] = None
    prioridad_ia: Optional[str] = None
    resumen_ia: Optional[str] = None
    especialidad_requerida_ia: Optional[str] = Field(default=None, index=True)
    distancia_estimada_km: Optional[float] = None
    asignacion_score: Optional[float] = None
    tiempo_estimado_minutos: Optional[int] = None
    estado_pago: Optional[str] = "pendiente"
    fecha_pago: Optional[datetime] = None
    cliente_sync_id: Optional[str] = Field(default=None, index=True)
    
    vehiculo_id: Optional[int] = Field(default=None, foreign_key="vehiculo.id")
    taller_id: Optional[int] = Field(default=None, foreign_key="taller.id")
    tecnico_id: Optional[int] = Field(default=None, foreign_key="tecnico.id")
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)

    # Cotización seleccionada por el cliente (denormalizado para queries rápidas).
    cotizacion_seleccionada_id: Optional[int] = Field(
        default=None, foreign_key="cotizacion.id"
    )
    # SLA esperado: usado por el KPI de cumplimiento.
    sla_esperado_minutos: Optional[int] = Field(default=60)
    fecha_taller_asignado: Optional[datetime] = None
    fecha_tecnico_llego: Optional[datetime] = None
    fecha_finalizado: Optional[datetime] = None

class Solicitud(SolicitudBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    
    vehiculo: Optional[Vehiculo] = Relationship(back_populates="solicitudes")
    taller: Optional["Taller"] = Relationship(back_populates="solicitudes_asignadas")
    tecnico_asignado: Optional[Tecnico] = Relationship(back_populates="solicitudes_atendidas")
    evidencias: List["Evidencia"] = Relationship(back_populates="solicitud")

class SolicitudRead(SolicitudBase):
    id: int
    fecha_creacion: datetime
    taller_nombre: Optional[str] = None
    taller_latitud: Optional[float] = None
    taller_longitud: Optional[float] = None
    tecnico_nombre: Optional[str] = None
    tecnico_especialidad: Optional[str] = None
    tecnico_latitud: Optional[float] = None
    tecnico_longitud: Optional[float] = None
    distancia_tecnico_km: Optional[float] = None
    vehiculo_placa: Optional[str] = None
    vehiculo_descripcion: Optional[str] = None
    audio_url: Optional[str] = None
    audio_resumen_ia: Optional[str] = None
    ruta_recomendada_ia: Optional[str] = None
    
class SolicitudCreate(SolicitudBase):
    pass

class TipoEvidencia(str, Enum):
    IMAGEN = "imagen"
    AUDIO = "audio"

class Evidencia(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: Optional[int] = Field(default=None, foreign_key="solicitud.id")
    tipo_evidencia: TipoEvidencia
    ruta_archivo: str
    fecha_subida: datetime = Field(default_factory=datetime.utcnow)
    
    solicitud: Optional[Solicitud] = Relationship(back_populates="evidencias")


class TallerBase(SQLModel):
    nombre_comercial: str = Field(index=True)
    direccion: str
    telefono: str
    email_contacto: Optional[str] = None
    horario_atencion: str  # Ej: "Lunes-Domingo 6:00-22:00"
    descripcion: Optional[str] = None
    sitio_web: Optional[str] = None
    
    # Ubicación geográfica
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    
    # Información adicional
    calificacion_promedio: float = Field(default=0.0)
    total_servicios_completados: int = Field(default=0)
    tiempo_respuesta_promedio: Optional[int] = None  # en minutos
    capacidad_operativa: int = Field(default=3)
    activo: bool = Field(default=True, index=True)
    
    # Configuración de notificaciones
    notificaciones_nuevas_asignaciones: bool = Field(default=True)
    notificaciones_push: bool = Field(default=True)
    notificaciones_recordatorios: bool = Field(default=True)
    notificaciones_pagos: bool = Field(default=True)
    reportes_semanales: bool = Field(default=False)
    
    # Usuario propietario (WORKSHOP)
    propietario_id: int = Field(foreign_key="user.id")
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)


class Taller(TallerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    propietario: "User" = Relationship(back_populates="taller")
    tecnicos: List["Tecnico"] = Relationship(back_populates="taller")
    solicitudes_asignadas: List["Solicitud"] = Relationship(back_populates="taller")
    especialidades: List["EspecialidadTaller"] = Relationship(
        back_populates="talleres",
        link_model=TalleresEspecialidades
    )


class TallerCreate(SQLModel):
    nombre_comercial: str
    direccion: str
    telefono: str
    email_contacto: Optional[str] = None
    horario_atencion: str
    especialidad_ids: List[int]
    descripcion: Optional[str] = None
    sitio_web: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class TallerRead(TallerBase):
    id: int
    especialidades: List[EspecialidadTallerRead] = Field(default_factory=list)


class TallerUpdate(SQLModel):
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email_contacto: Optional[str] = None
    horario_atencion: Optional[str] = None
    especialidad_ids: Optional[List[int]] = None
    descripcion: Optional[str] = None
    sitio_web: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    capacidad_operativa: Optional[int] = None
    activo: Optional[bool] = None
    notificaciones_nuevas_asignaciones: Optional[bool] = None
    notificaciones_push: Optional[bool] = None
    notificaciones_recordatorios: Optional[bool] = None
    notificaciones_pagos: Optional[bool] = None
    reportes_semanales: Optional[bool] = None


class EstadoCandidato(str, Enum):
    PENDIENTE = "pendiente"
    NOTIFICADO = "notificado"
    ACEPTADO = "aceptado"
    RECHAZADO = "rechazado"
    EXPIRADO = "expirado"


class SolicitudCandidato(SQLModel, table=True):
    __tablename__ = "solicitud_candidato"

    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitud.id", index=True)
    taller_id: int = Field(foreign_key="taller.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    posicion: int = Field(default=0, index=True)
    score: float = Field(default=0.0, index=True)
    distancia_km: Optional[float] = None
    eta_minutos: Optional[int] = None
    estado: EstadoCandidato = Field(default=EstadoCandidato.PENDIENTE, index=True)
    razon: Optional[str] = None
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow)


class SolicitudCandidatoRead(SQLModel):
    id: int
    solicitud_id: int
    taller_id: int
    tenant_id: Optional[int] = None
    posicion: int
    score: float
    distancia_km: Optional[float] = None
    eta_minutos: Optional[int] = None
    estado: EstadoCandidato
    razon: Optional[str] = None
    fecha_creacion: datetime


class SolicitudHistorial(SQLModel, table=True):
    __tablename__ = "solicitud_historial"

    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitud.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    estado_anterior: Optional[str] = Field(default=None, index=True)
    estado_nuevo: str = Field(index=True)
    actor_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    actor_rol: Optional[str] = Field(default=None, index=True)
    comentario: Optional[str] = None
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)


class SolicitudHistorialRead(SQLModel):
    id: int
    solicitud_id: int
    tenant_id: Optional[int] = None
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    actor_id: Optional[int] = None
    actor_rol: Optional[str] = None
    comentario: Optional[str] = None
    fecha_creacion: datetime


class ChatMensaje(SQLModel, table=True):
    __tablename__ = "chat_mensaje"

    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitud.id", index=True)
    remitente_id: int = Field(foreign_key="user.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    mensaje: str
    leido: bool = Field(default=False, index=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)


class ChatMensajeCreate(SQLModel):
    mensaje: str


class ChatMensajeRead(SQLModel):
    id: int
    solicitud_id: int
    remitente_id: int
    mensaje: str
    leido: bool
    fecha_creacion: datetime


class Pago(SQLModel, table=True):
    __tablename__ = "pago"

    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitud.id", index=True)
    usuario_id: int = Field(foreign_key="user.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    monto: float
    comision_plataforma: float = Field(default=0.0)
    metodo: str = Field(default="simulado")
    estado: str = Field(default="pagado", index=True)
    referencia: Optional[str] = Field(default=None, index=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)


class PagoRead(SQLModel):
    id: int
    solicitud_id: int
    usuario_id: int
    monto: float
    comision_plataforma: float
    metodo: str
    estado: str
    referencia: Optional[str] = None
    fecha_creacion: datetime


class CalificacionServicio(SQLModel, table=True):
    __tablename__ = "calificacion_servicio"

    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitud.id", index=True)
    taller_id: Optional[int] = Field(default=None, foreign_key="taller.id", index=True)
    cliente_id: int = Field(foreign_key="user.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    puntaje: int = Field(index=True)
    comentario: Optional[str] = None
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)


class CalificacionCreate(SQLModel):
    puntaje: int
    comentario: Optional[str] = None


class CalificacionRead(SQLModel):
    id: int
    solicitud_id: int
    taller_id: Optional[int] = None
    cliente_id: int
    puntaje: int
    comentario: Optional[str] = None
    fecha_creacion: datetime


class AnalisisIA(SQLModel, table=True):
    __tablename__ = "analisis_ia"

    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitud.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    modalidad: str = Field(default="texto", index=True)
    clasificacion: str
    prioridad: str
    resumen: str
    especialidad_requerida: Optional[str] = Field(default=None, index=True)
    confianza: Optional[float] = None
    proveedor: str = Field(default="mvp-local", index=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)


class EstadoCotizacion(str, Enum):
    ENVIADA = "enviada"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"
    EXPIRADA = "expirada"


class CotizacionBase(SQLModel):
    """Propuesta de un taller para atender una solicitud.

    Flujo:
    * El cliente crea una solicitud (auto-asigna talleres candidatos por scoring).
    * Cada taller candidato puede emitir UNA `Cotizacion` con costo, ETA y
      tiempo estimado de reparación.
    * El cliente compara cotizaciones y selecciona una → se setea
      `solicitud.cotizacion_seleccionada_id` y la solicitud pasa a `ASIGNADA`
      con el taller dueño de la cotización.
    """
    solicitud_id: int = Field(foreign_key="solicitud.id", index=True)
    taller_id: int = Field(foreign_key="taller.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    costo_estimado: float
    tiempo_reparacion_horas: float
    eta_llegada_minutos: int
    descripcion: Optional[str] = None
    incluye_repuestos: bool = Field(default=False)
    garantia_dias: int = Field(default=30)
    estado: EstadoCotizacion = Field(default=EstadoCotizacion.ENVIADA, index=True)


class Cotizacion(CotizacionBase, table=True):
    __tablename__ = "cotizacion"

    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)
    fecha_seleccion: Optional[datetime] = None


class CotizacionCreate(SQLModel):
    costo_estimado: float
    tiempo_reparacion_horas: float
    eta_llegada_minutos: int
    descripcion: Optional[str] = None
    incluye_repuestos: bool = False
    garantia_dias: int = 30


class CotizacionRead(CotizacionBase):
    id: int
    fecha_creacion: datetime
    fecha_seleccion: Optional[datetime] = None
    taller_nombre: Optional[str] = None
    taller_calificacion: Optional[float] = None


class TrackingPing(SQLModel, table=True):
    """Histórico de pings de ubicación del técnico durante una solicitud.

    Razón: necesitamos historial para reconstruir rutas, no solo la posición
    instantánea (que vive en Tecnico.latitud_actual). Esto permite auditoría
    y replay del recorrido para soporte/disputas.
    """
    __tablename__ = "tracking_ping"

    id: Optional[int] = Field(default=None, primary_key=True)
    solicitud_id: int = Field(foreign_key="solicitud.id", index=True)
    tecnico_id: int = Field(foreign_key="tecnico.id", index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    latitud: float
    longitud: float
    velocidad_kmh: Optional[float] = None
    rumbo_grados: Optional[float] = None
    distancia_restante_km: Optional[float] = None
    eta_minutos: Optional[int] = None
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)


class TrackingPingCreate(SQLModel):
    latitud: float
    longitud: float
    velocidad_kmh: Optional[float] = None
    rumbo_grados: Optional[float] = None


class TrackingPingRead(SQLModel):
    id: int
    solicitud_id: int
    tecnico_id: int
    tenant_id: Optional[int] = None
    latitud: float
    longitud: float
    velocidad_kmh: Optional[float] = None
    rumbo_grados: Optional[float] = None
    distancia_restante_km: Optional[float] = None
    eta_minutos: Optional[int] = None
    fecha_creacion: datetime


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    actor_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    actor_rol: Optional[str] = Field(default=None, index=True)
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id", index=True)
    accion: str = Field(index=True)
    entidad: str = Field(index=True)
    entidad_id: Optional[int] = Field(default=None, index=True)
    detalle: Optional[str] = None
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow, index=True)
