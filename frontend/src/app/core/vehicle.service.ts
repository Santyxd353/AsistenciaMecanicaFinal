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
}
