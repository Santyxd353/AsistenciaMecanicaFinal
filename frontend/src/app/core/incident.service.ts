import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { OfflineQueueService } from './offline-queue.service';

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
  tecnico_telefono?: string;
  tecnico_foto_url?: string;
  tecnico_latitud?: number;
  tecnico_longitud?: number;
  distancia_tecnico_km?: number;
  vehiculo_placa?: string;
  vehiculo_descripcion?: string;
  audio_url?: string;
  audio_resumen_ia?: string;
  ruta_recomendada_ia?: string;
  imagenes?: string[];
  cliente_sync_id?: string;
  cotizacion_seleccionada_id?: number;
  fecha_creacion: string;
}

@Injectable({
  providedIn: 'root'
})
export class SolicitudService {
  private apiUrl = 'http://localhost:8000/api/v1/solicitudes/';

  constructor(private http: HttpClient, private offlineQueue: OfflineQueueService) {}

  getSolicitudes(): Observable<Solicitud[]> {
    return this.http.get<Solicitud[]>(this.apiUrl);
  }

  getMisReportesCliente(): Observable<Solicitud[]> {
    return this.http.get<Solicitud[]>(`${this.apiUrl}mis-reportes`);
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
    if (!navigator.onLine) {
      return this.queueSolicitud(solicitud);
    }

    return this.http.post<Solicitud>(this.apiUrl, solicitud).pipe(
      catchError((err) => {
        if (err?.status === 0) {
          return this.queueSolicitud(solicitud);
        }
        return throwError(() => err);
      }),
    );
  }

  private queueSolicitud(solicitud: Partial<Solicitud>): Observable<Solicitud> {
    return this.offlineQueue.enqueue(this.apiUrl, solicitud).pipe(
      map((localId) => ({
        id: -Date.now(),
        descripcion: solicitud.descripcion ?? 'Emergencia pendiente de sincronización',
        latitud: solicitud.latitud ?? 0,
        longitud: solicitud.longitud ?? 0,
        estado: 'pendiente_sync',
        vehiculo_id: solicitud.vehiculo_id,
        fecha_creacion: new Date().toISOString(),
        cliente_sync_id: localId,
      })),
      catchError(() => of({
        id: -Date.now(),
        descripcion: solicitud.descripcion ?? 'Emergencia pendiente de sincronización',
        latitud: solicitud.latitud ?? 0,
        longitud: solicitud.longitud ?? 0,
        estado: 'pendiente_sync',
        vehiculo_id: solicitud.vehiculo_id,
        fecha_creacion: new Date().toISOString(),
      })),
    );
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

  uploadAudio(solicitudId: number, audioBlob: Blob): Observable<Solicitud> {
    const formData = new FormData();
    formData.append('audio', audioBlob, `audio_${Date.now()}.webm`);
    return this.http.post<Solicitud>(`${this.apiUrl}${solicitudId}/audio`, formData);
  }
}
