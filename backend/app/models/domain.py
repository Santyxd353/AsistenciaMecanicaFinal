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
    taller_id: Optional[int] = Field(default=None, foreign_key="user.id")

class Tecnico(TecnicoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    taller: Optional["User"] = Relationship(back_populates="tecnicos")
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
    taller_id: Optional[int] = Field(default=None, foreign_key="user.id")
    tecnico_id: Optional[int] = Field(default=None, foreign_key="tecnico.id")

class Solicitud(SolicitudBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    
    vehiculo: Optional[Vehiculo] = Relationship(back_populates="solicitudes")
    taller: Optional["User"] = Relationship(back_populates="solicitudes_asignadas")
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
