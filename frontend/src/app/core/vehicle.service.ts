import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Vehicle {
  id: number;
  placa: string;
  marca: string;
  modelo: string;
  anio?: number | null;
  color?: string | null;
  foto_url?: string | null;
  propietario_id?: number | null;
}

export interface VehiclePreview {
  placa: string;
  marca: string;
  modelo: string;
  anio?: number | null;
  color: string;
  resumen: string;
  source: string;
}

export interface CreateVehiclePayload {
  placa: string;
  marca: string;
  modelo: string;
  anio?: number | null;
  color?: string;
  foto?: File | null;
}

export interface UpdateVehiclePayload {
  placa?: string;
  marca?: string;
  modelo?: string;
  anio?: number | null;
  color?: string;
  foto?: File | null;
}

@Injectable({
  providedIn: 'root'
})
export class VehicleService {
  private apiUrl = 'http://127.0.0.1:8000/api/v1/vehiculos/';

  constructor(private http: HttpClient) {}

  getVehicles(): Observable<Vehicle[]> {
    return this.http.get<Vehicle[]>(this.apiUrl);
  }

  createVehicle(payload: CreateVehiclePayload): Observable<Vehicle> {
    const body = new FormData();
    body.append('placa', payload.placa);
    body.append('marca', payload.marca);
    body.append('modelo', payload.modelo);
    body.append('anio', payload.anio?.toString() ?? '');
    body.append('color', payload.color ?? '');
    if (payload.foto) {
      body.append('foto', payload.foto);
    }
    return this.http.post<Vehicle>(this.apiUrl, body);
  }

  updateVehicle(vehicleId: number, payload: UpdateVehiclePayload): Observable<Vehicle> {
    const body = new FormData();
    if (payload.placa != null) body.append('placa', payload.placa);
    if (payload.marca != null) body.append('marca', payload.marca);
    if (payload.modelo != null) body.append('modelo', payload.modelo);
    if (payload.anio != null) body.append('anio', payload.anio.toString());
    if (payload.color != null) body.append('color', payload.color);
    if (payload.foto) body.append('foto', payload.foto);
    return this.http.put<Vehicle>(`${this.apiUrl}${vehicleId}`, body);
  }

  previewVehicleFromPhotos(files: File[]): Observable<VehiclePreview> {
    const body = new FormData();
    files.slice(0, 4).forEach((file) => body.append('fotos', file));
    return this.http.post<VehiclePreview>(`${this.apiUrl}preview-from-photo`, body);
  }
}
