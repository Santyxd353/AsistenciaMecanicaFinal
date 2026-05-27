import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { forkJoin, Subscription } from 'rxjs';

import { KpiResponse, KpiSeriesResponse, KpiService } from '../../core/kpi.service';

Chart.register(...registerables);

@Component({
  selector: 'app-kpi-dashboard',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="kpi-shell" *ngIf="!loading; else loadingTpl">
      <header class="kpi-head">
        <div>
          <p class="kicker">KPIs operacionales</p>
          <h2>Rendimiento en tiempo real</h2>
        </div>
        <button type="button" class="refresh-btn" (click)="load()">Actualizar</button>
      </header>

      <div class="kpi-grid" *ngIf="kpis">
        <article class="metric">
          <span>Solicitudes</span>
          <strong>{{ kpis.total_solicitudes }}</strong>
          <small>Últimos {{ kpis.ventana_dias }} días</small>
        </article>
        <article class="metric">
          <span>Asignación</span>
          <strong>{{ minutes(kpis.tiempo_promedio_asignacion_min) }}</strong>
          <small>Promedio creación a taller</small>
        </article>
        <article class="metric">
          <span>Llegada</span>
          <strong>{{ minutes(kpis.tiempo_promedio_llegada_min) }}</strong>
          <small>Promedio taller a técnico</small>
        </article>
        <article class="metric">
          <span>SLA</span>
          <strong>{{ percent(kpis.sla_cumplimiento_pct) }}</strong>
          <small>Cumplimiento operativo</small>
        </article>
      </div>

      <div class="chart-grid">
        <article class="chart-panel">
          <div class="panel-title">
            <strong>Flujo diario</strong>
            <span>Creadas, finalizadas y canceladas</span>
          </div>
          <canvas #seriesCanvas height="120"></canvas>
        </article>

        <article class="chart-panel">
          <div class="panel-title">
            <strong>Tipos de incidente</strong>
            <span>Clasificación IA desde PostgreSQL</span>
          </div>
          <canvas #typesCanvas height="120"></canvas>
        </article>
      </div>

      <div class="insight-grid" *ngIf="kpis">
        <article class="table-panel">
          <div class="panel-title">
            <strong>Talleres eficientes</strong>
            <span>Ranking por tiempo y finalización</span>
          </div>
          <div class="row" *ngFor="let taller of kpis.talleres_mas_eficientes; let i = index">
            <b>{{ i + 1 }}</b>
            <span>{{ taller.nombre || ('Taller #' + taller.taller_id) }}</span>
            <strong>{{ taller.score_eficiencia | number:'1.0-1' }}</strong>
          </div>
          <p class="empty" *ngIf="!kpis.talleres_mas_eficientes.length">Sin servicios finalizados todavía.</p>
        </article>

        <article class="table-panel">
          <div class="panel-title">
            <strong>Zonas calientes</strong>
            <span>Clusters por lat/lng</span>
          </div>
          <div class="row" *ngFor="let zona of kpis.zonas_con_mas_incidentes">
            <b>{{ zona.incidentes }}</b>
            <span>{{ zona.lat }}, {{ zona.lng }}</span>
            <strong>casos</strong>
          </div>
          <p class="empty" *ngIf="!kpis.zonas_con_mas_incidentes.length">Sin coordenadas recientes.</p>
        </article>
      </div>
    </section>

    <ng-template #loadingTpl>
      <section class="kpi-shell skeleton">
        <div class="skeleton-line"></div>
        <div class="skeleton-grid">
          <span></span><span></span><span></span><span></span>
        </div>
      </section>
    </ng-template>
  `,
  styles: [`
    .kpi-shell {
      border: 1px solid #1f2a3a;
      background: #0f172a;
      color: #e5e7eb;
      border-radius: 18px;
      padding: 20px;
      margin: 18px 0;
      box-shadow: 0 22px 60px rgba(2, 6, 23, 0.28);
    }

    .kpi-head,
    .chart-grid,
    .insight-grid,
    .kpi-grid {
      display: grid;
      gap: 14px;
    }

    .kpi-head {
      grid-template-columns: 1fr auto;
      align-items: center;
      margin-bottom: 14px;
    }

    .kicker {
      margin: 0 0 4px;
      color: #67e8f9;
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 800;
      letter-spacing: 0.14em;
    }

    h2 {
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }

    .refresh-btn {
      border: 1px solid #334155;
      background: #111827;
      color: #f8fafc;
      border-radius: 999px;
      padding: 10px 14px;
      font-weight: 800;
      cursor: pointer;
    }

    .kpi-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin-bottom: 14px;
    }

    .metric,
    .chart-panel,
    .table-panel {
      border: 1px solid #253348;
      background: #111827;
      border-radius: 12px;
      padding: 14px;
    }

    .metric {
      display: grid;
      gap: 6px;
      min-height: 110px;
    }

    .metric span,
    .panel-title span {
      color: #94a3b8;
      font-size: 12px;
      font-weight: 700;
    }

    .metric strong {
      font-size: 28px;
      color: #f8fafc;
    }

    .metric small,
    .empty {
      color: #64748b;
    }

    .chart-grid {
      grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.7fr);
      margin-bottom: 14px;
    }

    .panel-title {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 12px;
    }

    .panel-title strong {
      color: #f8fafc;
    }

    .insight-grid {
      grid-template-columns: 1fr 1fr;
    }

    .row {
      display: grid;
      grid-template-columns: 34px 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 10px 0;
      border-top: 1px solid #1f2937;
    }

    .row b {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: #0e7490;
      color: #ecfeff;
      font-size: 12px;
    }

    .row span {
      color: #cbd5e1;
    }

    .row strong {
      color: #a7f3d0;
      font-size: 13px;
    }

    .skeleton-line,
    .skeleton-grid span {
      display: block;
      border-radius: 12px;
      background: linear-gradient(90deg, #172033, #26364f, #172033);
      background-size: 220% 100%;
      animation: pulse 1.5s infinite;
    }

    .skeleton-line {
      height: 28px;
      width: 280px;
      margin-bottom: 18px;
    }

    .skeleton-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }

    .skeleton-grid span {
      height: 96px;
    }

    @keyframes pulse {
      to { background-position: -220% 0; }
    }

    @media (max-width: 900px) {
      .kpi-head,
      .chart-grid,
      .insight-grid,
      .kpi-grid,
      .skeleton-grid {
        grid-template-columns: 1fr;
      }
    }
  `],
})
export class KpiDashboardComponent implements AfterViewInit, OnDestroy {
  @ViewChild('seriesCanvas') private seriesCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('typesCanvas') private typesCanvas?: ElementRef<HTMLCanvasElement>;

  kpis: KpiResponse | null = null;
  loading = true;

  private seriesChart: Chart | null = null;
  private typesChart: Chart | null = null;
  private subscription?: Subscription;

  constructor(
    private kpiService: KpiService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngAfterViewInit(): void {
    this.load();
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
    this.seriesChart?.destroy();
    this.typesChart?.destroy();
  }

  load(): void {
    this.loading = true;
    this.cdr.markForCheck();
    this.subscription?.unsubscribe();
    this.subscription = forkJoin({
      kpis: this.kpiService.getKpis(30),
      series: this.kpiService.getSeries(14),
    }).subscribe({
      next: ({ kpis, series }) => {
        this.kpis = kpis;
        this.loading = false;
        this.cdr.markForCheck();
        queueMicrotask(() => this.renderCharts(kpis, series));
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  minutes(value: number | null): string {
    return value === null ? '--' : `${Math.round(value)} min`;
  }

  percent(value: number | null): string {
    return value === null ? '--' : `${Math.round(value)}%`;
  }

  private renderCharts(kpis: KpiResponse, series: KpiSeriesResponse): void {
    const seriesCtx = this.seriesCanvas?.nativeElement.getContext('2d');
    const typesCtx = this.typesCanvas?.nativeElement.getContext('2d');
    if (!seriesCtx || !typesCtx) return;

    this.seriesChart?.destroy();
    this.typesChart?.destroy();

    const seriesConfig: ChartConfiguration = {
      type: 'line',
      data: {
        labels: series.serie.map((item) => item.fecha.slice(5)),
        datasets: [
          { label: 'Creadas', data: series.serie.map((item) => item.creadas), borderColor: '#67e8f9', backgroundColor: 'rgba(103,232,249,.12)', tension: 0.35, fill: true },
          { label: 'Finalizadas', data: series.serie.map((item) => item.finalizadas), borderColor: '#34d399', backgroundColor: 'rgba(52,211,153,.08)', tension: 0.35 },
          { label: 'Canceladas', data: series.serie.map((item) => item.canceladas), borderColor: '#fb7185', backgroundColor: 'rgba(251,113,133,.08)', tension: 0.35 },
        ],
      },
      options: this.chartOptions(),
    };

    const labels = Object.keys(kpis.incidentes_por_tipo);
    const values = Object.values(kpis.incidentes_por_tipo);
    const typesConfig: ChartConfiguration = {
      type: 'doughnut',
      data: {
        labels: labels.length ? labels : ['Sin datos'],
        datasets: [{
          data: values.length ? values : [1],
          backgroundColor: ['#67e8f9', '#34d399', '#fbbf24', '#fb7185', '#a78bfa'],
          borderColor: '#111827',
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { labels: { color: '#cbd5e1' } },
        },
      },
    };

    this.seriesChart = new Chart(seriesCtx, seriesConfig);
    this.typesChart = new Chart(typesCtx, typesConfig);
  }

  private chartOptions(): ChartConfiguration['options'] {
    return {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#cbd5e1' } },
      },
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: '#1f2937' } },
        y: { ticks: { color: '#94a3b8', precision: 0 }, grid: { color: '#1f2937' }, beginAtZero: true },
      },
    };
  }
}
