from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

class EstadoSolicitud(str, Enum):
    PENDIENTE = "pendiente"
    ASIGNADA = "asignada"
    EN_PROGRESO = "en_progreso"
    RESUELTA = "resuelta"
    CANCELADA = "cancelada"

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

class TecnicoBase(SQLModel):
    nombre: str
    especialidad: str
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    disponible: bool = True
    taller_id: Optional[int] = Field(default=None, foreign_key="taller.id")

class Tecnico(TecnicoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    taller: Optional["Taller"] = Relationship(back_populates="tecnicos")
    solicitudes_atendidas: List["Solicitud"] = Relationship(back_populates="tecnico_asignado")

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
    tecnico_nombre: Optional[str] = None
    tecnico_especialidad: Optional[str] = None
    
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
    especialidades: str  # JSON string con lista de especialidades
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


class TallerCreate(SQLModel):
    nombre_comercial: str
    direccion: str
    telefono: str
    email_contacto: Optional[str] = None
    horario_atencion: str
    especialidades: str
    descripcion: Optional[str] = None
    sitio_web: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class TallerRead(TallerBase):
    id: int


class TallerUpdate(SQLModel):
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email_contacto: Optional[str] = None
    horario_atencion: Optional[str] = None
    especialidades: Optional[str] = None
    descripcion: Optional[str] = None
    sitio_web: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    notificaciones_nuevas_asignaciones: Optional[bool] = None
    notificaciones_push: Optional[bool] = None
    notificaciones_recordatorios: Optional[bool] = None
    notificaciones_pagos: Optional[bool] = None
    reportes_semanales: Optional[bool] = None
