from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

class EstadoSolicitud(str, Enum):
    PENDIENTE = "pendiente"
    ASIGNADA = "asignada"
    EN_PROGRESO = "en_progreso"
    LLEGADA = "llegada"
    RESUELTA = "resuelta"
    CANCELADA = "cancelada"


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
    placa: str = Field(index=True, unique=True)
    marca: str
    modelo: str
    color: Optional[str] = None
    propietario_id: Optional[int] = Field(default=None, foreign_key="user.id")

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
    disponible: bool = True
    activo: bool = True
    taller_id: Optional[int] = Field(default=None, foreign_key="taller.id")
    id_usuario: Optional[int] = Field(default=None, foreign_key="user.id", unique=True)

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
    tiempo_estimado_minutos: Optional[int] = None
    estado_pago: Optional[str] = "pendiente"
    fecha_pago: Optional[datetime] = None
    
    vehiculo_id: Optional[int] = Field(default=None, foreign_key="vehiculo.id")
    taller_id: Optional[int] = Field(default=None, foreign_key="taller.id")
    tecnico_id: Optional[int] = Field(default=None, foreign_key="tecnico.id")

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
    
    # Configuración de notificaciones
    notificaciones_nuevas_asignaciones: bool = Field(default=True)
    notificaciones_push: bool = Field(default=True)
    notificaciones_recordatorios: bool = Field(default=True)
    notificaciones_pagos: bool = Field(default=True)
    reportes_semanales: bool = Field(default=False)
    
    # Usuario propietario (WORKSHOP)
    propietario_id: int = Field(foreign_key="user.id")


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
    notificaciones_nuevas_asignaciones: Optional[bool] = None
    notificaciones_push: Optional[bool] = None
    notificaciones_recordatorios: Optional[bool] = None
    notificaciones_pagos: Optional[bool] = None
    reportes_semanales: Optional[bool] = None
