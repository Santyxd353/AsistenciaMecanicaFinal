import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TipoVehiculo {
  id: number;
  nombre: string;
}

@Injectable({ providedIn: 'root' })
export class VehicleTypeService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:8000/api/v1/tipos-vehiculo';

  /** Lista todos los tipos de vehículo seedeados (Auto, Moto, Eléctrico, etc.). */
  list(): Observable<TipoVehiculo[]> {
    return this.http.get<TipoVehiculo[]>(`${this.apiUrl}/`);
  }
}
