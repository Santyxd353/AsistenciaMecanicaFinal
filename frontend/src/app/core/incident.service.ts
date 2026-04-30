import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Solicitud {
  id: number;
  descripcion: string;
  latitud: number;
  longitud: number;
  estado: string;
  vehiculo_id?: number;
  taller_id?: number;
  tecnico_id?: number;
  precio_cobrado?: number;
  comision_plataforma?: number;
  clasificacion_ia?: string;
  prioridad_ia?: string;
  resumen_ia?: string;
  tiempo_estimado_minutos?: number;
  estado_pago?: string;
  fecha_pago?: string;
  taller_nombre?: string;
  taller_latitud?: number;
  taller_longitud?: number;
  tecnico_nombre?: string;
  tecnico_especialidad?: string;
  tecnico_latitud?: number;
  tecnico_longitud?: number;
  vehiculo_placa?: string;
  vehiculo_descripcion?: string;
  audio_url?: string;
  audio_resumen_ia?: string;
  ruta_recomendada_ia?: string;
  fecha_creacion: string;
}

@Injectable({
  providedIn: 'root'
})
export class SolicitudService {
  private apiUrl = 'https://backend-958497253028.europe-west1.run.app/api/v1/solicitudes/';

  constructor(private http: HttpClient) {}

  getSolicitudes(): Observable<Solicitud[]> {
    return this.http.get<Solicitud[]>(this.apiUrl);
  }

  getSolicitudesPendientesTaller(): Observable<Solicitud[]> {
    return this.http.get<Solicitud[]>(`${this.apiUrl}taller/pendientes`);
  }

  getMisSolicitudesTaller(): Observable<Solicitud[]> {
    return this.http.get<Solicitud[]>(`${this.apiUrl}taller/mis-solicitudes`);
  }

  getMisAsignaciones(): Observable<Solicitud[]> {
    return this.http.get<Solicitud[]>(`${this.apiUrl}mis-asignaciones`);
  }

  createSolicitud(solicitud: Partial<Solicitud>): Observable<Solicitud> {
    return this.http.post<Solicitud>(this.apiUrl, solicitud);
  }

  aceptarSolicitud(solicitudId: number): Observable<Solicitud> {
    return this.http.patch<Solicitud>(`${this.apiUrl}${solicitudId}/aceptar`, {});
  }

  asignarTecnico(solicitudId: number, tecnicoId: number): Observable<Solicitud> {
    return this.http.patch<Solicitud>(`${this.apiUrl}${solicitudId}/asignar-tecnico?tecnico_id=${tecnicoId}`, {});
  }

  cancelarSolicitud(solicitudId: number): Observable<Solicitud> {
    return this.http.patch<Solicitud>(`${this.apiUrl}${solicitudId}/cancelar`, {});
  }

  actualizarMiAsignacionEstado(solicitudId: number, estado: string): Observable<Solicitud> {
    return this.http.patch<Solicitud>(`${this.apiUrl}mis-asignaciones/${solicitudId}/estado?estado=${estado}`, {});
  }

  actualizarCosto(solicitudId: number, monto: number): Observable<Solicitud> {
    return this.http.patch<Solicitud>(`${this.apiUrl}${solicitudId}/costo`, { monto });
  }

  pagarSolicitud(solicitudId: number, monto?: number): Observable<Solicitud> {
    return this.http.post<Solicitud>(`${this.apiUrl}${solicitudId}/pago`, monto ? { monto } : {});
  }
}
