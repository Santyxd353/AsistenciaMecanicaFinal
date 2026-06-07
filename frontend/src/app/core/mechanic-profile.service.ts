import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { Especialidad } from './especialidad.service';

export interface MechanicProfile {
  id: number;
  nombre: string;
  foto_url: string | null;
  taller_id: number | null;
  taller_nombre: string | null;
  disponible: boolean;
  activo: boolean;
  especialidades: Especialidad[];
  calificacion_promedio: number;
  total_calificaciones: number;
  total_servicios_finalizados: number;
}

export interface MechanicRating {
  id: number;
  tecnico_id: number;
  cliente_id: number;
  solicitud_id: number;
  puntaje: number;
  comentario: string | null;
  fecha_creacion: string;
  cliente_nombre: string | null;
}

export interface MechanicRatingPayload {
  puntaje: number;
  comentario?: string | null;
}

@Injectable({ providedIn: 'root' })
export class MechanicProfileService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:8000/api/v1/tecnicos';

  /** Datos públicos del mecánico (sin CI, dirección, email). */
  getProfile(id: number): Observable<MechanicProfile> {
    return this.http.get<MechanicProfile>(`${this.apiUrl}/${id}/perfil`);
  }

  /** Listado paginado de calificaciones recibidas. */
  listRatings(id: number, skip = 0, limit = 20): Observable<MechanicRating[]> {
    return this.http.get<MechanicRating[]>(
      `${this.apiUrl}/${id}/calificaciones?skip=${skip}&limit=${limit}`,
    );
  }

  /** El cliente califica al mecánico por una solicitud finalizada concreta. */
  createRating(
    id: number,
    solicitudId: number,
    payload: MechanicRatingPayload,
  ): Observable<MechanicRating> {
    return this.http.post<MechanicRating>(
      `${this.apiUrl}/${id}/calificaciones?solicitud_id=${solicitudId}`,
      payload,
    );
  }
}
