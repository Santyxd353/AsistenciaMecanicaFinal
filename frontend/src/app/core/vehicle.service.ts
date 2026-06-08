import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Vehicle {
  id: number;
  placa: string;
  marca: string;
  modelo: string;
  color?: string | null;
  propietario_id?: number | null;
}

export interface CreateVehiclePayload {
  placa: string;
  marca: string;
  modelo: string;
  color?: string;
}

export interface UpdateVehiclePayload {
  placa?: string;
  marca?: string;
  modelo?: string;
  color?: string;
}

export interface VehiclePhotoPreview {
  placa: string;
  marca: string;
  modelo: string;
  anio?: number | null;
  color: string;
  resumen: string;
  source: string;
}

export interface VehicleRepairHistory {
  id: number;
  vehiculo_id: number;
  solicitud_id?: number | null;
  taller_id?: number | null;
  tecnico_id?: number | null;
  tenant_id?: number | null;
  titulo: string;
  diagnostico?: string | null;
  acciones_realizadas?: string | null;
  categoria?: string | null;
  prioridad?: string | null;
  costo?: number | null;
  estado_pago?: string | null;
  kilometraje?: number | null;
  observaciones?: string | null;
  fecha_servicio: string;
  fecha_creacion: string;
  fecha_actualizacion: string;
  taller_nombre?: string | null;
  tecnico_nombre?: string | null;
  solicitud_estado?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class VehicleService {
  private apiUrl = 'http://localhost:8000/api/v1/vehiculos/';

  constructor(private http: HttpClient) {}

  getVehicles(): Observable<Vehicle[]> {
    return this.http.get<Vehicle[]>(this.apiUrl);
  }

  createVehicle(payload: CreateVehiclePayload): Observable<Vehicle> {
    return this.http.post<Vehicle>(this.apiUrl, payload);
  }

  updateVehicle(vehicleId: number, payload: UpdateVehiclePayload): Observable<Vehicle> {
    return this.http.put<Vehicle>(`${this.apiUrl}${vehicleId}`, payload);
  }

  previewVehicleFromPhotos(files: File[]): Observable<VehiclePhotoPreview> {
    const form = new FormData();
    files.slice(0, 4).forEach((file) => form.append('fotos', file));
    return this.http.post<VehiclePhotoPreview>(`${this.apiUrl}preview-from-photo`, form);
  }

  getVehicleHistory(vehicleId: number): Observable<VehicleRepairHistory[]> {
    return this.http.get<VehicleRepairHistory[]>(`${this.apiUrl}${vehicleId}/historial`);
  }
}
