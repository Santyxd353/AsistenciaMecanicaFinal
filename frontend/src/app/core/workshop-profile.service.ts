import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface EspecialidadTaller {
  id: number;
  nombre: string;
}

export interface Taller {
  id: number;
  nombre_comercial: string;
  direccion: string;
  telefono: string;
  email_contacto?: string;
  horario_atencion: string;
  especialidades: EspecialidadTaller[];
  descripcion?: string;
  sitio_web?: string;
  latitud?: number;
  longitud?: number;
  calificacion_promedio: number;
  total_servicios_completados: number;
  tiempo_respuesta_promedio?: number;
  notificaciones_nuevas_asignaciones: boolean;
  notificaciones_push: boolean;
  notificaciones_recordatorios: boolean;
  notificaciones_pagos: boolean;
  reportes_semanales: boolean;
}

export interface WorkshopStats {
  taller_info: {
    id: number;
    nombre_comercial: string;
    calificacion_promedio: number;
    total_servicios_completados: number;
  };
  servicios: {
    total_completados: number;
    ingreso_promedio_por_servicio: number;
    comisiones_totales_pagadas: number;
  };
  tecnicos: {
    total_tecnicos: number;
    tecnicos_disponibles: number;
  };
  tiempo_respuesta_promedio?: number;
}

export interface CreateTallerPayload {
  nombre_comercial: string;
  direccion: string;
  telefono: string;
  email_contacto?: string;
  horario_atencion: string;
  especialidad_ids: number[];
  descripcion?: string;
  sitio_web?: string;
  latitud?: number;
  longitud?: number;
}

export interface UpdateTallerPayload {
  nombre_comercial?: string;
  direccion?: string;
  telefono?: string;
  email_contacto?: string;
  horario_atencion?: string;
  especialidad_ids?: number[];
  descripcion?: string;
  sitio_web?: string;
  latitud?: number;
  longitud?: number;
  notificaciones_nuevas_asignaciones?: boolean;
  notificaciones_push?: boolean;
  notificaciones_recordatorios?: boolean;
  notificaciones_pagos?: boolean;
  reportes_semanales?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class WorkshopProfileService {
  private apiUrl = 'https://backend-958497253028.europe-west1.run.app/api/v1/talleres';

  constructor(private http: HttpClient) {}

  /**
   * Crear un nuevo taller para el usuario actual
   */
  createWorkshop(tallerData: CreateTallerPayload): Observable<Taller> {
    return this.http.post<Taller>(`${this.apiUrl}/`, tallerData);
  }

  /**
   * Obtener el taller del usuario actual
   */
  getMyWorkshop(): Observable<Taller> {
    return this.http.get<Taller>(`${this.apiUrl}/mi-taller`);
  }

  /**
   * Actualizar el taller del usuario actual
   */
  updateMyWorkshop(updates: UpdateTallerPayload): Observable<Taller> {
    return this.http.put<Taller>(`${this.apiUrl}/mi-taller`, updates);
  }

  /**
   * Obtener estadísticas del taller del usuario actual
   */
  getWorkshopStats(): Observable<WorkshopStats | null> {
    /*
    return this.http.get<WorkshopStats>(`${this.apiUrl}/workshop/stats`).pipe(
      catchError((error : unknown) => {
        console.error('Error loading stats:', error);
        return of(null);
      })
    );
    */
    return of(null);
  }
  
}
