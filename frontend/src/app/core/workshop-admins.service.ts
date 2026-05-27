import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface WorkshopAdmin {
  id: number;
  username: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
  tenant_id?: number | null;
}

export interface WorkshopAdminPayload {
  username: string;
  email: string;
  full_name?: string | null;
  password: string;
}

@Injectable({ providedIn: 'root' })
export class WorkshopAdminsService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/workshop-admins';

  constructor(private http: HttpClient) {}

  list(): Observable<WorkshopAdmin[]> {
    return this.http.get<WorkshopAdmin[]>(`${this.apiUrl}/`);
  }

  create(payload: WorkshopAdminPayload): Observable<WorkshopAdmin> {
    return this.http.post<WorkshopAdmin>(`${this.apiUrl}/`, payload);
  }

  deactivate(id: number): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(`${this.apiUrl}/${id}`);
  }
}
