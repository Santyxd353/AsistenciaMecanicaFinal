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
  fecha_pago?: string | null;
  taller_nombre?: string | null;
  tecnico_nombre?: string | null;
  tecnico_especialidad?: string | null;
  vehiculo_placa?: string | null;
  vehiculo_descripcion?: string | null;
  fecha_creacion: string;
}

@Injectable({
  providedIn: 'root'
})
export class SolicitudService {
  private apiUrl = 'http://localhost:8000/api/v1/solicitudes/';

  constructor(private http: HttpClient) {}

  getSolicitudes(): Observable<Solicitud[]> {
    return this.http.get<Solicitud[]>(this.apiUrl);
  }

  getMyReports(): Observable<Solicitud[]> {
    return this.http.get<Solicitud[]>(`${this.apiUrl}mis-reportes`);
  }

  createSolicitud(solicitud: Partial<Solicitud>): Observable<Solicitud> {
    return this.http.post<Solicitud>(this.apiUrl, solicitud);
  }

  updateStatus(solicitudId: number, estado: string, tecnicoId?: number): Observable<Solicitud> {
    let url = `${this.apiUrl}${solicitudId}/estado?estado=${estado}`;
    if (tecnicoId) url += `&tecnico_id=${tecnicoId}`;
    return this.http.patch<Solicitud>(url, {});
  }

  cancelSolicitud(solicitudId: number): Observable<Solicitud> {
    return this.http.patch<Solicitud>(`${this.apiUrl}${solicitudId}/cancelar`, {});
  }

  paySolicitud(solicitudId: number, monto?: number): Observable<Solicitud> {
    return this.http.post<Solicitud>(`${this.apiUrl}${solicitudId}/pago`, {
      monto
    });
  }
}
