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
    return this.http.post<Vehicle>(this.apiUrl, payload);
  }

  updateVehicle(vehicleId: number, payload: UpdateVehiclePayload): Observable<Vehicle> {
    return this.http.put<Vehicle>(`${this.apiUrl}${vehicleId}`, payload);
  }
}
