import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Especialidad } from './especialidad.service';

export interface Tecnico {
  id: number;
  nombre: string;
  email?: string | null;
  ci: string;
  direccion: string;
  especialidades: Especialidad[];
  latitud?: number;
  longitud?: number;
  disponible: boolean;
  activo: boolean;
  taller_id?: number;
  id_usuario?: number | null;
  usuario_username?: string | null;
  usuario_email?: string | null;
  usuario_telefono?: string | null;
  password_temporal?: string | null;
}

export interface TecnicoPayload {
  nombre: string;
  /**
   * Correo del mecánico — lo usará para hacer login.
   * Obligatorio al CREAR (backend TecnicoIn lo exige), pero en updates el
   * endpoint PUT usa `TecnicoUpdate` que no lo lleva. Lo dejamos opcional
   * a nivel de tipo para que update flows compilen, y el form de creación
   * lo marca `required`.
   */
  email?: string;
  telefono?: string;
  ci: string;
  direccion: string;
  especialidad_ids: number[];
  disponible: boolean;
  activo: boolean;
  latitud?: number | null;
  longitud?: number | null;
}

export interface TecnicoUsuarioPayload {
  username: string;
  email: string;
  password: string;
}

@Injectable({
  providedIn: 'root'
})
export class TecnicoService {
  private apiUrl = 'http://localhost:8000/api/v1/tecnicos';

  constructor(private http: HttpClient) {}

  getTecnicos(): Observable<Tecnico[]> {
    return this.http.get<Tecnico[]>(`${this.apiUrl}/`);
  }

  getMiPerfilTecnico(): Observable<Tecnico> {
    return this.http.get<Tecnico>(`${this.apiUrl}/mi-perfil`);
  }

  actualizarMiDisponibilidad(disponible: boolean): Observable<Tecnico> {
    return this.http.patch<Tecnico>(`${this.apiUrl}/mi-disponibilidad?disponible=${disponible}`, {});
  }

  createTecnico(tecnico: TecnicoPayload): Observable<Tecnico> {
    return this.http.post<Tecnico>(`${this.apiUrl}/`, tecnico);
  }

  crearTecnico(tecnico: TecnicoPayload): Observable<Tecnico> {
    return this.createTecnico(tecnico);
  }

  actualizarTecnico(id: number, data: TecnicoPayload): Observable<Tecnico> {
    return this.http.put<Tecnico>(`${this.apiUrl}/${id}`, data);
  }

  convertirATecnicoUsuario(id: number, data: TecnicoUsuarioPayload): Observable<Tecnico> {
    return this.http.post<Tecnico>(`${this.apiUrl}/${id}/convertir-a-usuario`, data);
  }

  eliminarTecnico(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  updateDisponibilidad(tecnicoId: number, disponible: boolean): Observable<Tecnico> {
    return this.http.patch<Tecnico>(`${this.apiUrl}/${tecnicoId}/disponibilidad?disponible=${disponible}`, {});
  }

  cambiarDisponibilidad(tecnicoId: number, disponible: boolean): Observable<Tecnico> {
    return this.updateDisponibilidad(tecnicoId, disponible);
  }
}
