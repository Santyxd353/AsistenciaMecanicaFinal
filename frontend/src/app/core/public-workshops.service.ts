import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PublicWorkshop {
  id: number;
  nombre_comercial: string;
  direccion: string;
  tenant_id: number | null;
  tenant_nombre?: string | null;
}

@Injectable({ providedIn: 'root' })
export class PublicWorkshopsService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/talleres/public/search';

  constructor(private http: HttpClient) {}

  search(query: string): Observable<PublicWorkshop[]> {
    return this.http.get<PublicWorkshop[]>(`${this.apiUrl}?q=${encodeURIComponent(query)}`);
  }
}
