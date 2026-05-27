import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { of } from 'rxjs';

export interface SaaSPlan {
  id: number;
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  precio_mensual: number;
  max_administradores: number | null;
  max_mecanicos: number | null;
  max_solicitudes_mes: number | null;
  beneficios: string[];
  activo: boolean;
}

export const DEFAULT_SAAS_PLANS: SaaSPlan[] = [
  {
    id: 1,
    codigo: 'gratis',
    nombre: 'Gratis',
    descripcion: 'Plan inicial para validar un taller pequeño.',
    precio_mensual: 0,
    max_administradores: 1,
    max_mecanicos: 5,
    max_solicitudes_mes: 30,
    beneficios: ['1 administrador', '5 mecánicos', '30 solicitudes al mes', 'Dashboard básico', 'Tracking en tiempo real'],
    activo: true,
  },
  {
    id: 2,
    codigo: 'intermedio',
    nombre: 'Intermedio',
    descripcion: 'Operación diaria con más equipo y analítica.',
    precio_mensual: 149,
    max_administradores: 3,
    max_mecanicos: 10,
    max_solicitudes_mes: 200,
    beneficios: ['3 administradores', '10 mecánicos', 'KPIs operativos', 'Historial avanzado', 'Soporte por correo'],
    activo: true,
  },
  {
    id: 3,
    codigo: 'premium',
    nombre: 'Premium',
    descripcion: 'Para talleres con alto volumen operativo.',
    precio_mensual: 299,
    max_administradores: 10,
    max_mecanicos: 20,
    max_solicitudes_mes: 1000,
    beneficios: ['10 administradores', '20 mecánicos', 'Dashboard avanzado', 'Auditoría', 'Reportes exportables'],
    activo: true,
  },
  {
    id: 4,
    codigo: 'pro',
    nombre: 'Pro',
    descripcion: 'Escala completa sin límites de usuarios operativos.',
    precio_mensual: 599,
    max_administradores: null,
    max_mecanicos: null,
    max_solicitudes_mes: null,
    beneficios: ['Administradores ilimitados', 'Mecánicos ilimitados', 'Solicitudes ilimitadas', 'Analítica avanzada', 'Soporte premium'],
    activo: true,
  },
];

@Injectable({ providedIn: 'root' })
export class PlansService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/plans';

  constructor(private http: HttpClient) {}

  getPlans(): Observable<SaaSPlan[]> {
    return this.http.get<SaaSPlan[]>(`${this.apiUrl}/`).pipe(
      map((plans) => Array.isArray(plans) && plans.length ? plans : DEFAULT_SAAS_PLANS),
      catchError(() => of(DEFAULT_SAAS_PLANS)),
    );
  }

  getPlan(codigo: string): Observable<SaaSPlan> {
    return this.http.get<SaaSPlan>(`${this.apiUrl}/${codigo}`);
  }
}
