import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Especialidad {
  id: number;
  nombre: string;
}

@Injectable({
  providedIn: 'root'
})
export class EspecialidadService {
  private apiUrl = 'https://backend-958497253028.europe-west1.run.app/api/v1/especialidades';

  constructor(private http: HttpClient) {}

  getEspecialidades(): Observable<Especialidad[]> {
    return this.http.get<Especialidad[]>(`${this.apiUrl}/`);
  }

  crearEspecialidad(nombre: string): Observable<Especialidad> {
    return this.http.post<Especialidad>(`${this.apiUrl}/`, { nombre });
  }
}
