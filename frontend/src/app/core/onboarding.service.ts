import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AuthResponse } from './auth.service';

export interface OnboardingPayload {
  onboarding_token: string;
  admin: {
    username: string;
    email: string;
    full_name?: string | null;
    password: string;
  };
  taller: {
    nombre_comercial: string;
    direccion: string;
    telefono: string;
    email_contacto?: string | null;
    horario_atencion: string;
    especialidad_ids: number[];
    /** IDs del catálogo `/api/v1/tipos-vehiculo/`. Opcional para retrocompat. */
    tipo_vehiculo_ids?: number[];
    descripcion?: string | null;
    sitio_web?: string | null;
    latitud?: number | null;
    longitud?: number | null;
  };
}

@Injectable({ providedIn: 'root' })
export class OnboardingService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/onboarding';

  constructor(private http: HttpClient) {}

  createWorkshop(payload: OnboardingPayload): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.apiUrl}/workshop`, payload);
  }
}
