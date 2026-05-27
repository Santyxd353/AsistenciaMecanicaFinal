import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Cotizacion {
  id: number;
  solicitud_id: number;
  taller_id: number;
  tenant_id?: number | null;
  costo_estimado: number;
  tiempo_reparacion_horas: number;
  eta_llegada_minutos: number;
  descripcion?: string | null;
  incluye_repuestos: boolean;
  garantia_dias: number;
  estado: 'enviada' | 'aceptada' | 'rechazada' | 'expirada';
  fecha_creacion: string;
  fecha_seleccion?: string | null;
  taller_nombre?: string | null;
  taller_calificacion?: number | null;
}

export interface CotizacionCreate {
  costo_estimado: number;
  tiempo_reparacion_horas: number;
  eta_llegada_minutos: number;
  descripcion?: string;
  incluye_repuestos: boolean;
  garantia_dias: number;
}

@Injectable({ providedIn: 'root' })
export class CotizacionService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/cotizaciones';

  constructor(private http: HttpClient) {}

  crear(solicitudId: number, payload: CotizacionCreate): Observable<Cotizacion> {
    return this.http.post<Cotizacion>(`${this.apiUrl}/solicitudes/${solicitudId}`, payload);
  }

  listarPorSolicitud(solicitudId: number): Observable<Cotizacion[]> {
    return this.http.get<Cotizacion[]>(`${this.apiUrl}/solicitudes/${solicitudId}`);
  }

  seleccionar(cotizacionId: number): Observable<Cotizacion> {
    return this.http.post<Cotizacion>(`${this.apiUrl}/${cotizacionId}/seleccionar`, {});
  }
}
