import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface KpiResponse {
  tenant_id: number | null;
  ventana_dias: number;
  total_solicitudes: number;
  tiempo_promedio_asignacion_min: number | null;
  tiempo_promedio_llegada_min: number | null;
  incidentes_por_tipo: Record<string, number>;
  talleres_mas_eficientes: Array<{
    taller_id: number;
    nombre: string | null;
    total_servicios: number;
    finalizados: number;
    tiempo_promedio_total_min: number;
    score_eficiencia: number;
  }>;
  zonas_con_mas_incidentes: Array<{
    lat: number;
    lng: number;
    incidentes: number;
  }>;
  casos_cancelados: {
    total: number;
    porcentaje: number;
  };
  sla_cumplimiento_pct: number | null;
  ingresos: {
    bruto: number;
    comision_plataforma: number;
    neto_talleres: number;
  };
}

export interface KpiSeriesResponse {
  tenant_id: number | null;
  serie: Array<{
    fecha: string;
    creadas: number;
    finalizadas: number;
    canceladas: number;
  }>;
}

@Injectable({ providedIn: 'root' })
export class KpiService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/kpis';

  constructor(private http: HttpClient) {}

  getKpis(dias = 30): Observable<KpiResponse> {
    return this.http.get<KpiResponse>(`${this.apiUrl}/?dias=${dias}`);
  }

  getSeries(dias = 14): Observable<KpiSeriesResponse> {
    return this.http.get<KpiSeriesResponse>(`${this.apiUrl}/series-temporales?dias=${dias}`);
  }
}
