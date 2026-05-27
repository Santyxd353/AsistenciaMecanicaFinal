import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { EspecialidadTaller } from './workshop-profile.service';

@Injectable({
  providedIn: 'root'
})
export class WorkshopSpecialtyService {
  private apiUrl = 'http://localhost:8000/api/v1/especialidades-taller';

  constructor(private http: HttpClient) {}

  getSpecialties(): Observable<EspecialidadTaller[]> {
    return this.http.get<EspecialidadTaller[]>(`${this.apiUrl}/`);
  }

  createSpecialty(nombre: string): Observable<EspecialidadTaller> {
    return this.http.post<EspecialidadTaller>(`${this.apiUrl}/`, { nombre });
  }
}
