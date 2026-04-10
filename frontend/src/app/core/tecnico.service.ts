import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Tecnico {
  id: number;
  nombre: string;
  especialidad: string;
  latitud?: number;
  longitud?: number;
  disponible: boolean;
  taller_id?: number;
}

@Injectable({
  providedIn: 'root'
})
export class TecnicoService {
  private apiUrl = 'http://localhost:8000/api/v1/tecnicos/';

  constructor(private http: HttpClient) {}

  getTecnicos(): Observable<Tecnico[]> {
    return this.http.get<Tecnico[]>(this.apiUrl);
  }

  createTecnico(tecnico: Partial<Tecnico>): Observable<Tecnico> {
    return this.http.post<Tecnico>(this.apiUrl, tecnico);
  }

  updateDisponibilidad(tecnicoId: number, disponible: boolean): Observable<Tecnico> {
    return this.http.patch<Tecnico>(`${this.apiUrl}/${tecnicoId}/disponibilidad?disponible=${disponible}`, {});
  }
}
