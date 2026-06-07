import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { timeout } from 'rxjs/operators';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthService } from '../core/auth.service';
import { Cotizacion, CotizacionService } from '../core/cotizacion.service';
import { Solicitud, SolicitudService } from '../core/incident.service';
import { VehicleService } from '../core/vehicle.service';
import { MechanicProfileService } from '../core/mechanic-profile.service';
import { ClienteNavbarComponent } from './cliente-navbar.component';

@Component({
  selector: 'app-cliente-solicitudes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, ClienteNavbarComponent],
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

        <!-- Calificación al mecánico: aparece solo cuando la solicitud está
             FINALIZADA, tiene tecnico_id, y el cliente aún no calificó. -->
        <div class="rating-cta" *ngIf="canRateMechanic(r)">
          <div class="rating-cta-text">
            <p class="section-kicker">Califica al mecánico</p>
            <strong>¿Cómo fue tu experiencia con {{ r.tecnico_nombre || 'el mecánico' }}?</strong>
          </div>
          <div class="rating-cta-actions">
            <a class="btn-ghost" [routerLink]="['/mecanicos', r.tecnico_id]" *ngIf="r.tecnico_id">Ver perfil</a>
            <button class="btn-primary" type="button" (click)="abrirCalificacion(r)">
              Calificar
            </button>
          </div>
        </div>
        <div class="rating-done" *ngIf="ratedRequestIds.has(r.id)">
          ✓ Gracias por tu calificación.
        </div>
      </section>

      <p class="message success" *ngIf="msg">{{ msg }}</p>
      <p class="message error" *ngIf="err">{{ err }}</p>

      <!-- Dialog: calificar mecánico (puntaje 1-5 + comentario opcional) -->
      <div class="rating-overlay" *ngIf="ratingDialog" (click)="cerrarCalificacion()">
        <div class="rating-modal" (click)="$event.stopPropagation()">
          <header>
            <p class="section-kicker">Calificación</p>
            <h2>{{ ratingDialog.tecnicoNombre }}</h2>
            <p class="rating-sub">Solicitud #{{ ratingDialog.solicitudId }}</p>
          </header>

          <div class="rating-stars-pick" role="radiogroup" aria-label="Puntaje">
            <button *ngFor="let star of [1,2,3,4,5]" type="button"
                    class="rating-star"
                    [class.filled]="star <= ratingDialog.puntaje"
                    (click)="ratingDialog && (ratingDialog.puntaje = star)">★</button>
          </div>

          <textarea class="rating-textarea"
                    rows="3"
                    placeholder="Comentario opcional (calidad, puntualidad, trato…)"
                    [(ngModel)]="ratingDialog.comentario"
                    name="comentario"
                    maxlength="500"></textarea>

          <div class="rating-error" *ngIf="ratingError">{{ ratingError }}</div>

          <div class="rating-actions">
            <button class="btn-ghost" type="button" (click)="cerrarCalificacion()">Cancelar</button>
            <button class="btn-primary" type="button"
                    [disabled]="ratingDialog.puntaje < 1 || ratingDialog.saving"
                    (click)="enviarCalificacion()">
              {{ ratingDialog.saving ? 'Enviando...' : 'Enviar calificación' }}
            </button>
          </div>
        </div>
      </div>
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
    .btn-ghost { background: transparent; border: 1px solid #b89a72; color: #6c4a2a;
                 padding: 9px 14px; border-radius: 10px; font-weight: 800;
                 cursor: pointer; text-decoration: none; display: inline-block; }
    .btn-ghost:hover { background: #f5e6cf; }

    /* CTA inline para calificar al mecánico tras finalizar la solicitud. */
    .rating-cta { display: flex; gap: 14px; align-items: center; flex-wrap: wrap;
                  margin-top: 12px; padding: 14px 16px;
                  background: #fff8ef; border: 1px solid #eadcca;
                  border-radius: 14px; }
    .rating-cta-text { flex: 1 1 auto; min-width: 200px; }
    .rating-cta-text strong { display: block; margin-top: 2px; color: #2f241d; }
    .rating-cta-actions { display: flex; gap: 8px; }
    .rating-done { margin-top: 10px; color: #2e7d32; font-weight: 800; }

    /* Modal de calificación (overlay + card centrada). */
    .rating-overlay { position: fixed; inset: 0; background: rgba(31,18,8,0.55);
                      display: flex; align-items: center; justify-content: center;
                      padding: 20px; z-index: 1000; }
    .rating-modal { background: #fff; border-radius: 18px; max-width: 480px;
                    width: 100%; padding: 22px;
                    box-shadow: 0 30px 80px rgba(20,10,4,0.32); }
    .rating-modal h2 { margin: 4px 0 0; font-size: 1.4rem; }
    .rating-sub { margin: 4px 0 14px; color: #7a6554; font-size: 13px; }
    .rating-stars-pick { display: flex; gap: 6px; justify-content: center;
                         margin: 6px 0 12px; }
    .rating-star { background: transparent; border: none; cursor: pointer;
                   font-size: 36px; line-height: 1; color: #dcd2c2;
                   transition: color .15s ease, transform .12s ease; }
    .rating-star:hover { transform: scale(1.12); }
    .rating-star.filled { color: #f5a524; }
    .rating-textarea { width: 100%; resize: vertical; border-radius: 12px;
                       border: 1px solid #eadcca; padding: 10px 12px;
                       font: inherit; background: #fffaf2; }
    .rating-error { background: #fee2e2; color: #991b1b; padding: 10px;
                    border-radius: 10px; margin-top: 10px; }
    .rating-actions { display: flex; justify-content: flex-end; gap: 8px;
                      margin-top: 14px; }
  `]
})
export class ClienteSolicitudesComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly solicitudService = inject(SolicitudService);
  private readonly cotizacionService = inject(CotizacionService);
  private readonly vehicleService = inject(VehicleService);
  private readonly mechanicProfile = inject(MechanicProfileService);

  reports: Solicitud[] = [];
  cotizacionesPorReporte: Record<number, Cotizacion[]> = {};
  cotizacionesLoading: Record<number, boolean> = {};
  selectingId: number | null = null;
  msg = '';
  err = '';

  /**
   * IDs de solicitudes que el cliente ya calificó en esta sesión. Se popula
   * tras enviar la calificación. Persistencia más allá del refresh requeriría
   * un endpoint `GET /tecnicos/{id}/calificaciones?solicitud_id=` — fuera de
   * scope ahora; al refrescar el cliente verá el CTA de nuevo y el backend
   * rechazará con 409 si ya existe, manteniendo la integridad.
   */
  ratedRequestIds = new Set<number>();

  ratingDialog: {
    solicitudId: number;
    tecnicoId: number;
    tecnicoNombre: string;
    puntaje: number;
    comentario: string;
    saving: boolean;
  } | null = null;
  ratingError = '';

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

  /** Habilita el CTA "Calificar mecánico" tras finalizar el servicio. */
  canRateMechanic(r: Solicitud): boolean {
    return (
      !!r.tecnico_id &&
      ['finalizado', 'resuelta'].includes((r.estado || '').toLowerCase()) &&
      !this.ratedRequestIds.has(r.id)
    );
  }

  abrirCalificacion(r: Solicitud): void {
    if (!r.tecnico_id) return;
    this.ratingDialog = {
      solicitudId: r.id,
      tecnicoId: r.tecnico_id,
      tecnicoNombre: r.tecnico_nombre || 'Mecánico',
      puntaje: 0,
      comentario: '',
      saving: false,
    };
    this.ratingError = '';
  }

  cerrarCalificacion(): void {
    this.ratingDialog = null;
    this.ratingError = '';
  }

  enviarCalificacion(): void {
    const dialog = this.ratingDialog;
    if (!dialog || dialog.puntaje < 1 || dialog.puntaje > 5 || dialog.saving) {
      return;
    }
    dialog.saving = true;
    this.ratingError = '';
    this.mechanicProfile.createRating(
      dialog.tecnicoId,
      dialog.solicitudId,
      {
        puntaje: dialog.puntaje,
        comentario: (dialog.comentario || '').trim() || null,
      },
    ).subscribe({
      next: () => {
        this.ratedRequestIds.add(dialog.solicitudId);
        this.msg = 'Calificación enviada. ¡Gracias por tu feedback!';
        this.ratingDialog = null;
      },
      error: (error) => {
        dialog.saving = false;
        this.ratingError =
          error?.error?.detail || 'No se pudo enviar la calificación.';
      },
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
