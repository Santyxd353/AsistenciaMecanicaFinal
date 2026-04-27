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
  especialidad_requerida_ia?: string;
  taller_nombre?: string;
  tecnico_nombre?: string;
  tecnico_especialidad?: string;
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

  createSolicitud(solicitud: Partial<Solicitud>): Observable<Solicitud> {
    return this.http.post<Solicitud>(this.apiUrl, solicitud);
  }

  updateStatus(solicitudId: number, estado: string, tecnicoId?: number): Observable<Solicitud> {
    let url = `${this.apiUrl}${solicitudId}/estado?estado=${estado}`;
    if (tecnicoId) url += `&tecnico_id=${tecnicoId}`;
    return this.http.patch<Solicitud>(url, {});
  }
}
