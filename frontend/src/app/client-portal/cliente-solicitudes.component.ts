import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { timeout } from 'rxjs/operators';
import { AuthService } from '../core/auth.service';
import { Cotizacion, CotizacionService } from '../core/cotizacion.service';
import { Solicitud, SolicitudService } from '../core/incident.service';
import { VehicleService } from '../core/vehicle.service';
import { ClienteNavbarComponent } from './cliente-navbar.component';

@Component({
  selector: 'app-cliente-solicitudes',
  standalone: true,
  imports: [CommonModule, ClienteNavbarComponent],
  template: `
    <div class="portal-shell">
      <app-cliente-navbar></app-cliente-navbar>

      <section class="page-heading">
        <h1>Mis solicitudes</h1>
        <p class="lede">Estado de las solicitudes de auxilio, cotizaciones de talleres y pagos pendientes.</p>
      </section>

      <p class="empty" *ngIf="!reports.length">Aún no tienes solicitudes registradas.</p>

      <section class="panel" *ngFor="let r of reports">
        <div class="panel-head">
          <div>
            <p class="section-kicker">Solicitud #{{ r.id }}</p>
            <h2>{{ r.descripcion || 'Sin descripción' }}</h2>
          </div>
          <span class="status-chip" [class]="r.estado">{{ labelForStatus(r.estado) }}</span>
        </div>

        <div class="report-meta">
          <div><span>Taller</span><strong>{{ r.taller_nombre || 'Pendiente' }}</strong></div>
          <div><span>Técnico</span><strong>{{ r.tecnico_nombre || '-' }}</strong></div>
          <div><span>ETA</span><strong>{{ r.tiempo_estimado_minutos ? r.tiempo_estimado_minutos + ' min' : '-' }}</strong></div>
          <div><span>Costo</span><strong>{{ r.precio_cobrado ? ('Bs ' + r.precio_cobrado) : 'Pendiente' }}</strong></div>
        </div>

        <div class="cotizacion-block" *ngIf="isPending(r) && cotizacionesPorReporte[r.id]?.length">
          <p class="section-kicker">Cotizaciones disponibles</p>
          <div class="cotizacion-list">
            <div class="cotizacion-card" *ngFor="let cot of cotizacionesPorReporte[r.id]">
              <div class="cotizacion-head">
                <strong>{{ cot.taller_nombre || 'Taller' }}</strong>
                <span *ngIf="cot.taller_calificacion != null">★ {{ cot.taller_calificacion | number:'1.1-1' }}</span>
              </div>
              <div class="cotizacion-grid">
                <div><span>Costo</span><strong>Bs {{ cot.costo_estimado }}</strong></div>
                <div><span>Reparación</span><strong>{{ cot.tiempo_reparacion_horas }} h</strong></div>
                <div><span>Llegada</span><strong>{{ cot.eta_llegada_minutos }} min</strong></div>
                <div><span>Garantía</span><strong>{{ cot.garantia_dias }} días</strong></div>
              </div>
              <button class="btn-primary" type="button"
                [disabled]="selectingId === cot.id"
                (click)="seleccionar(cot, r.id)">
                {{ selectingId === cot.id ? 'Seleccionando...' : 'Seleccionar este taller' }}
              </button>
            </div>
          </div>
        </div>

        <p class="cotizacion-empty" *ngIf="isPending(r) && !cotizacionesPorReporte[r.id]?.length && !cotizacionesLoading[r.id]">
          Aún no hay cotizaciones para esta solicitud.
        </p>

        <div class="panel-actions" *ngIf="canPay(r)">
          <button class="btn-primary" type="button" (click)="pagar(r)">Pagar Bs {{ r.precio_cobrado }}</button>
        </div>
      </section>

      <p class="message success" *ngIf="msg">{{ msg }}</p>
      <p class="message error" *ngIf="err">{{ err }}</p>
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh;
      background: radial-gradient(circle at top left, rgba(214,149,82,0.16), transparent 28%),
        linear-gradient(180deg,#f8f2ea 0%,#f6f7fb 46%,#fff 100%);
      color: #18120e; font-family: "Segoe UI", sans-serif;}
    .portal-shell { max-width: 1100px; margin: 0 auto; padding: 28px 20px 44px; }
    .page-heading { padding: 6px 4px 22px; }
    h1 { margin: 0; font-size: clamp(2rem,3.5vw,3rem); }
    h2 { margin: 0; font-size: 1.3rem; }
    .lede { margin: 10px 0 0; color: #685a4b; }
    .empty { padding: 16px; color: #685a4b; }
    .section-kicker {
      margin: 0 0 4px; text-transform: uppercase; letter-spacing: 0.14em;
      font-size: 11px; font-weight: 800; color: #9a6133;
    }
    .panel {
      background: rgba(255,255,255,0.95); border: 1px solid #eadcca;
      border-radius: 22px; padding: 20px; margin-bottom: 14px;
      box-shadow: 0 18px 42px rgba(64,37,18,0.08);
    }
    .panel-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
    .status-chip {
      padding: 6px 12px; border-radius: 999px; font-size: 11px; font-weight: 800;
      text-transform: uppercase; letter-spacing: 0.1em;
      background: #eadcca; color: #5a3a22;
    }
    .status-chip.finalizado, .status-chip.resuelta { background: #b9e0b9; color: #2e7d32; }
    .status-chip.cancelado, .status-chip.cancelada { background: #f0c0c0; color: #c62828; }
    .status-chip.asignada { background: #d8c4a8; color: #5a3a22; }
    .report-meta {
      display: grid; grid-template-columns: repeat(4,1fr); gap: 10px;
      margin-bottom: 12px;
    }
    .report-meta > div span {
      display: block; font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: #8a6647;
    }
    .report-meta > div strong { font-size: 0.95rem; }
    .cotizacion-block { padding: 12px; background: #fdf6ec; border-radius: 14px; margin-top: 8px; }
    .cotizacion-list { display: grid; gap: 10px; margin-top: 8px; }
    .cotizacion-card { background: #fff; border-radius: 12px; padding: 12px; border: 1px solid #eadcca; }
    .cotizacion-head { display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: 700; }
    .cotizacion-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; margin-bottom: 8px; }
    .cotizacion-grid > div span { display: block; font-size: 10px; color: #8a6647; text-transform: uppercase; letter-spacing: 0.12em; }
    .cotizacion-empty { padding: 10px 14px; color: #685a4b; font-style: italic; }
    .btn-primary {
      padding: 10px 18px; border-radius: 10px;
      background: linear-gradient(180deg,#b5651d 0%,#8a4a16 100%);
      color: #fff8ef; border: none; font-weight: 800; cursor: pointer;
    }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .panel-actions { margin-top: 10px; }
    .message { margin-top: 10px; font-size: 13px; }
    .message.success { color: #2e7d32; }
    .message.error { color: #c62828; }
  `]
})
export class ClienteSolicitudesComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly solicitudService = inject(SolicitudService);
  private readonly cotizacionService = inject(CotizacionService);
  private readonly vehicleService = inject(VehicleService);

  reports: Solicitud[] = [];
  cotizacionesPorReporte: Record<number, Cotizacion[]> = {};
  cotizacionesLoading: Record<number, boolean> = {};
  selectingId: number | null = null;
  msg = '';
  err = '';

  ngOnInit(): void {
    if (!this.auth.isLoggedIn()) { this.router.navigate(['/login']); return; }
    this.load();
  }

  load(): void {
    this.vehicleService.getVehicles().pipe(timeout(10000)).subscribe({
      next: (vehicles) => {
        const ownIds = new Set(vehicles.map(v => v.id));
        this.solicitudService.getSolicitudes().pipe(timeout(10000)).subscribe({
          next: (reports) => {
            this.reports = reports
              .filter(r => !!r.vehiculo_id && ownIds.has(r.vehiculo_id))
              .sort((a, b) => b.id - a.id);
            this.reports.filter(r => this.isPending(r)).forEach(r => this.loadCotizaciones(r.id));
          },
          error: () => { this.err = 'No se pudieron cargar tus solicitudes.'; },
        });
      },
    });
  }

  loadCotizaciones(reportId: number): void {
    this.cotizacionesLoading[reportId] = true;
    this.cotizacionService.listarPorSolicitud(reportId).pipe(timeout(10000)).subscribe({
      next: (cots) => {
        this.cotizacionesPorReporte[reportId] = cots.filter(c => c.estado === 'enviada');
        this.cotizacionesLoading[reportId] = false;
      },
      error: () => { this.cotizacionesLoading[reportId] = false; },
    });
  }

  seleccionar(cot: Cotizacion, reportId: number): void {
    this.selectingId = cot.id;
    this.err = '';
    this.cotizacionService.seleccionar(cot.id).pipe(timeout(10000)).subscribe({
      next: () => {
        this.selectingId = null;
        this.msg = `Taller ${cot.taller_nombre ?? ''} asignado.`.trim();
        delete this.cotizacionesPorReporte[reportId];
        this.load();
      },
      error: (error) => {
        this.selectingId = null;
        this.err = error?.error?.detail || 'No se pudo seleccionar la cotización.';
        this.loadCotizaciones(reportId);
      },
    });
  }

  pagar(report: Solicitud): void {
    this.solicitudService.pagarSolicitud(report.id, report.precio_cobrado).subscribe({
      next: (updated) => {
        this.msg = 'Pago registrado.';
        this.reports = this.reports.map(r => r.id === updated.id ? updated : r);
      },
      error: (error) => { this.err = error?.error?.detail || 'No se pudo pagar.'; },
    });
  }

  isPending(r: Solicitud): boolean {
    return ['pendiente', 'buscando_taller'].includes(r.estado);
  }

  canPay(r: Solicitud): boolean {
    return !!r.precio_cobrado && r.estado_pago !== 'pagado'
      && ['en_proceso', 'tecnico_llego', 'finalizado', 'resuelta'].includes(r.estado);
  }

  labelForStatus(s: string): string {
    const m: Record<string, string> = {
      pendiente: 'Pendiente',
      buscando_taller: 'Buscando taller',
      asignada: 'Asignada',
      tecnico_en_camino: 'En camino',
      tecnico_llego: 'Técnico llegó',
      en_proceso: 'En proceso',
      finalizado: 'Finalizado',
      cancelado: 'Cancelado',
      resuelta: 'Finalizado',
      cancelada: 'Cancelado',
    };
    return m[s] ?? s;
  }
}
