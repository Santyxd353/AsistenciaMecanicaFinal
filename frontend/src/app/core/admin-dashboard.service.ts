import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SuperDashboard {
  resumen: {
    tenants: number;
    usuarios: number;
    talleres: number;
    tecnicos: number;
    solicitudes: number;
    pagos: number;
    ingreso_bruto: number;
    comision_plataforma: number;
    neto_talleres: number;
  };
  solicitudes: {
    por_estado: Record<string, number>;
    por_tipo: Record<string, number>;
    recientes: AdminSolicitud[];
  };
  tenants: AdminTenant[];
  talleres: AdminTaller[];
  tecnicos: AdminTecnico[];
  pagos: AdminPago[];
  auditoria: AdminAudit[];
  mapa: {
    talleres: AdminMapPoint[];
    tecnicos: AdminMapPoint[];
    solicitudes: AdminMapPoint[];
  };
}

export interface AdminTenant {
  id: number;
  nombre: string;
  slug: string;
  activo: boolean;
  usuarios: number;
  talleres: number;
  solicitudes: number;
}

export interface AdminTaller {
  id: number;
  tenant_id: number | null;
  tenant: string;
  nombre_comercial: string;
  direccion: string;
  telefono: string;
  propietario: string;
  activo: boolean;
  calificacion_promedio: number;
  capacidad_operativa: number;
  latitud: number | null;
  longitud: number | null;
  tecnicos: number;
  solicitudes: number;
}

export interface AdminTecnico {
  id: number;
  tenant_id: number | null;
  tenant: string;
  nombre: string;
  taller: string;
  disponible: boolean;
  activo: boolean;
  latitud: number | null;
  longitud: number | null;
}

export interface AdminSolicitud {
  id: number;
  tenant_id: number | null;
  tenant: string;
  descripcion: string;
  estado: string;
  clasificacion_ia: string | null;
  prioridad_ia: string | null;
  taller: string;
  tecnico: string;
  latitud: number | null;
  longitud: number | null;
  fecha_creacion: string | null;
}

export interface AdminPago {
  id: number;
  tenant_id: number | null;
  tenant: string;
  solicitud_id: number;
  usuario_id: number;
  monto: number;
  comision_plataforma: number;
  estado: string;
  metodo: string;
  fecha_creacion: string | null;
}

export interface AdminAudit {
  id: number;
  tenant_id: number | null;
  tenant: string;
  actor_id: number | null;
  actor_rol: string | null;
  accion: string;
  entidad: string;
  entidad_id: number | null;
  detalle: string | null;
  fecha_creacion: string | null;
}

export interface AdminMapPoint {
  id: number;
  nombre?: string;
  descripcion?: string;
  estado?: string;
  latitud: number | null;
  longitud: number | null;
}

@Injectable({ providedIn: 'root' })
export class AdminDashboardService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/admin';

  constructor(private http: HttpClient) {}

  getSuperDashboard(): Observable<SuperDashboard> {
    return this.http.get<SuperDashboard>(`${this.apiUrl}/super-dashboard`);
  }
}
