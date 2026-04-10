import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Solicitud } from '../core/incident.service';
import { Tecnico } from '../core/tecnico.service';

export interface AsignacionEvento {
  estado: string;
  tecnicoId?: number;
}

@Component({
  selector: 'app-detalle-solicitud-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="modal-overlay" (click)="onOverlayClick($event)">
      <div class="modal-box" role="dialog" aria-modal="true">

        <!-- CABECERA STICKY -->
        <div class="modal-header">
          <div class="modal-title">
            <h2>Emergencia #{{ solicitud.id }}</h2>
            <span class="status-chip" [ngClass]="solicitud.estado">
              {{ etiquetaEstado(solicitud.estado) }}
            </span>
          </div>
          <button class="modal-close" (click)="cerrar.emit()">✕</button>
        </div>

        <!-- PASO: SELECCIONAR TÉCNICO -->
        <div class="asignacion-step" *ngIf="seleccionandoTecnico">
          <div class="step-header">
            <h3>¿A qué técnico asignas esta emergencia?</h3>
            <p>Solo se muestran los técnicos marcados como disponibles.</p>
          </div>

          <div class="tecnicos-disponibles" *ngIf="tecnicosDisponibles.length > 0; else sinTecnicos">
            <div
              class="tecnico-opcion"
              *ngFor="let tec of tecnicosDisponibles"
              [class.seleccionado]="tecnicoSeleccionado?.id === tec.id"
              (click)="tecnicoSeleccionado = tec"
            >
              <div class="tec-avatar">{{ tec.nombre.charAt(0) }}</div>
              <div class="tec-data">
                <strong>{{ tec.nombre }}</strong>
                <span>{{ tec.especialidad }}</span>
              </div>
              <div class="tec-check" *ngIf="tecnicoSeleccionado?.id === tec.id">✓</div>
            </div>
          </div>

          <ng-template #sinTecnicos>
            <div class="empty-state-mini">No hay técnicos disponibles en este momento.</div>
          </ng-template>

          <div class="step-actions">
            <button
              class="btn-success"
              [disabled]="!tecnicoSeleccionado"
              (click)="confirmarAsignacion()"
            >
              ✓ Confirmar Asignación
            </button>
            <button class="btn-ghost" (click)="seleccionandoTecnico = false; tecnicoSeleccionado = null">
              Cancelar
            </button>
          </div>
        </div>

        <!-- CUERPO PRINCIPAL (oculto mientras se selecciona técnico) -->
        <ng-container *ngIf="!seleccionandoTecnico">

          <div class="modal-body">

            <!-- Descripción -->
            <div class="info-section">
              <label>Descripción del Problema</label>
              <p>{{ solicitud.descripcion }}</p>
            </div>

            <!-- Técnico asignado (si aplica) -->
            <div class="info-section" *ngIf="solicitud.tecnico_id">
              <label>Técnico Asignado</label>
              <div class="tecnico-asignado">
                <div class="tec-avatar small">{{ nombreTecnicoAsignado().charAt(0) }}</div>
                <strong>{{ nombreTecnicoAsignado() }}</strong>
              </div>
            </div>

            <!-- Bloque IA -->
            <div class="ai-box">
              <div class="ai-header">
                <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
                  <path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>
                </svg>
                Análisis de Inteligencia Artificial
              </div>
              <div class="ai-chips">
                <div class="ai-chip">
                  <span>Prioridad</span>
                  <strong [ngClass]="solicitud.prioridad_ia?.toLowerCase()">
                    {{ solicitud.prioridad_ia || '—' }}
                  </strong>
                </div>
                <div class="ai-chip">
                  <span>Tipo de Falla</span>
                  <strong>{{ solicitud.clasificacion_ia || 'Analizando...' }}</strong>
                </div>
              </div>
              <div class="ai-resumen">
                <span>Resumen Automático</span>
                <p>{{ solicitud.resumen_ia || 'Procesando evidencia...' }}</p>
              </div>
            </div>

            <!-- Mapa -->
            <div class="info-section">
              <label>Ubicación del Vehículo</label>
              <p class="coords">📍 {{ solicitud.latitud | number:'1.4-5' }}, {{ solicitud.longitud | number:'1.4-5' }}</p>
              <div class="map-wrap">
                <iframe
                  width="100%"
                  height="260"
                  frameborder="0"
                  style="border:0; border-radius:8px; display:block;"
                  [src]="getMapUrl(solicitud.latitud, solicitud.longitud)"
                  allowfullscreen>
                </iframe>
              </div>
            </div>

            <!-- Desglose de pago (solo si resuelta) -->
            <div class="info-section comision-box" *ngIf="solicitud.estado === 'resuelta'">
              <label>Desglose de Pago</label>
              <div class="comision-row">
                <span>Cobrado al cliente</span><strong>Bs. 150.00</strong>
              </div>
              <div class="comision-row highlight">
                <span>Comisión de la plataforma (10%)</span><strong>− Bs. 15.00</strong>
              </div>
              <div class="comision-row total">
                <span>Ingreso neto del taller</span><strong>Bs. 135.00</strong>
              </div>
            </div>

          </div>

          <!-- FOOTER STICKY CON ACCIONES -->
          <div class="modal-footer">
            <ng-container [ngSwitch]="solicitud.estado">

              <ng-container *ngSwitchCase="'pendiente'">
                <button
                  class="btn-success"
                  [disabled]="tecnicosDisponibles.length === 0"
                  (click)="iniciarSeleccionTecnico()"
                >
                  {{ tecnicosDisponibles.length > 0 ? 'Asignar Técnico →' : 'Sin técnicos disponibles' }}
                </button>
                <button class="btn-danger" (click)="accion.emit({ estado: 'cancelada' })">Rechazar</button>
              </ng-container>

              <ng-container *ngSwitchCase="'asignada'">
                <button class="btn-primary" (click)="accion.emit({ estado: 'en_progreso' })">
                  Técnico llegó → Marcar en Progreso
                </button>
              </ng-container>

              <ng-container *ngSwitchCase="'en_progreso'">
                <button class="btn-success" (click)="accion.emit({ estado: 'resuelta' })">
                  Completar y Registrar Pago
                </button>
              </ng-container>

            </ng-container>

            <button class="btn-ghost" (click)="cerrar.emit()">Cerrar</button>
          </div>

        </ng-container>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed; inset: 0; background: rgba(17,24,39,.45);
      display: flex; align-items: center; justify-content: center;
      z-index: 1000; padding: 20px; box-sizing: border-box;
      animation: fadeIn .15s ease;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    .modal-box {
      background: #fff; border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0,0,0,.18);
      width: 100%; max-width: 640px; max-height: 90vh; overflow-y: auto;
      animation: slideUp .2s ease;
    }
    @keyframes slideUp {
      from { transform: translateY(16px); opacity: 0; }
      to   { transform: translateY(0);    opacity: 1; }
    }

    /* Cabecera */
    .modal-header {
      padding: 22px 24px 18px;
      display: flex; justify-content: space-between; align-items: flex-start;
      border-bottom: 1px solid #f3f4f6;
      position: sticky; top: 0; background: #fff; z-index: 1;
    }
    .modal-title { display: flex; flex-direction: column; gap: 8px; }
    .modal-title h2 { margin: 0; font-size: 20px; font-weight: 700; }
    .modal-close {
      background: #f3f4f6; border: none; width: 32px; height: 32px;
      border-radius: 50%; cursor: pointer; font-size: 16px;
      display: flex; align-items: center; justify-content: center;
      color: #6b7280; flex-shrink: 0;
    }
    .modal-close:hover { background: #e5e7eb; color: #111827; }

    /* PASO SELECCIÓN DE TÉCNICO */
    .asignacion-step { padding: 24px; }
    .step-header { margin-bottom: 20px; }
    .step-header h3 { margin: 0 0 6px; font-size: 17px; font-weight: 700; }
    .step-header p  { margin: 0; font-size: 14px; color: #6b7280; }

    .tecnicos-disponibles { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
    .tecnico-opcion {
      display: flex; align-items: center; gap: 14px;
      padding: 14px 16px; border: 2px solid #e5e7eb; border-radius: 10px;
      cursor: pointer; transition: all .15s;
    }
    .tecnico-opcion:hover { border-color: #a5b4fc; background: #fafbff; }
    .tecnico-opcion.seleccionado { border-color: #6366f1; background: #eef2ff; }

    .tec-avatar {
      width: 40px; height: 40px; border-radius: 50%;
      background: #e0e7ff; color: #3730a3;
      display: flex; align-items: center; justify-content: center;
      font-weight: 700; font-size: 16px; flex-shrink: 0;
    }
    .tec-avatar.small { width: 30px; height: 30px; font-size: 13px; }
    .tec-data { flex: 1; }
    .tec-data strong { display: block; font-size: 15px; }
    .tec-data span   { font-size: 13px; color: #6b7280; }
    .tec-check { width: 24px; height: 24px; background: #6366f1; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; }

    .empty-state-mini { padding: 20px; text-align: center; color: #9ca3af; font-size: 14px; background: #f9fafb; border-radius: 8px; margin-bottom: 16px; }

    .step-actions { display: flex; gap: 10px; }
    .step-actions button { flex: 1; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; border: 1px solid transparent; transition: all .15s; }

    /* Técnico asignado */
    .tecnico-asignado { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; }
    .tecnico-asignado strong { font-size: 15px; color: #166534; }

    /* Cuerpo */
    .modal-body { padding: 24px; display: flex; flex-direction: column; gap: 20px; }
    .info-section label { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #9ca3af; font-weight: 600; margin-bottom: 6px; }
    .info-section p { margin: 0; font-size: 15px; line-height: 1.6; color: #374151; }
    .coords { font-size: 13px; color: #6b7280; margin-bottom: 10px !important; }
    .map-wrap { border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb; }

    /* Status chips */
    .status-chip { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; }
    .pendiente   { background: #fef9c3; color: #854d0e; }
    .asignada    { background: #dbeafe; color: #1e40af; }
    .en_progreso { background: #e0e7ff; color: #3730a3; }
    .resuelta    { background: #dcfce7; color: #166534; }
    .cancelada   { background: #fee2e2; color: #991b1b; }

    /* AI */
    .ai-box { background: linear-gradient(135deg, #faf5ff 0%, #f0f0ff 100%); border: 1px solid #e9d5ff; border-radius: 10px; padding: 16px; }
    .ai-header { display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 700; color: #7c3aed; margin-bottom: 14px; }
    .ai-chips { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
    .ai-chip { background: rgba(255,255,255,.7); border-radius: 8px; padding: 10px 12px; }
    .ai-chip span { display: block; font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: #9333ea; font-weight: 600; margin-bottom: 4px; }
    .ai-chip strong { font-size: 14px; color: #4c1d95; }
    .ai-chip strong.alta   { color: #dc2626; }
    .ai-chip strong.media  { color: #d97706; }
    .ai-chip strong.baja   { color: #16a34a; }
    .ai-resumen { background: rgba(255,255,255,.6); border-radius: 7px; padding: 10px 12px; }
    .ai-resumen span { display: block; font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: #9333ea; font-weight: 600; margin-bottom: 4px; }
    .ai-resumen p { margin: 0; font-size: 13px; color: #4c1d95; line-height: 1.5; }

    /* Comisión */
    .comision-box { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 16px; }
    .comision-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; color: #374151; }
    .comision-row.highlight { color: #dc2626; }
    .comision-row.total { border-top: 1px solid #bbf7d0; margin-top: 4px; padding-top: 10px; font-weight: 700; font-size: 15px; color: #166534; }

    /* Footer */
    .modal-footer {
      padding: 16px 24px; border-top: 1px solid #f3f4f6;
      display: flex; gap: 10px; flex-wrap: wrap;
      position: sticky; bottom: 0; background: #fff;
    }
    .modal-footer button { flex: 1; padding: 10px 16px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; border: 1px solid transparent; transition: all .15s; min-width: 120px; }
    .btn-success { background: #16a34a; color: #fff; border-color: #16a34a; }
    .btn-success:hover:not(:disabled) { background: #15803d; }
    .btn-success:disabled { opacity: .5; cursor: not-allowed; }
    .btn-primary { background: #111827; color: #fff; }
    .btn-primary:hover { background: #000; }
    .btn-danger  { background: #fff; color: #dc2626; border-color: #fca5a5 !important; }
    .btn-danger:hover  { background: #fef2f2; }
    .btn-ghost   { background: #f9fafb; color: #6b7280; border-color: #e5e7eb !important; }
    .btn-ghost:hover   { background: #f3f4f6; color: #111827; }
  `]
})
export class DetalleSolicitudModalComponent {
  @Input() solicitud!: Solicitud;
  /** Lista completa de técnicos del taller (el modal filtra los disponibles) */
  @Input() tecnicos: Tecnico[] = [];

  @Output() cerrar = new EventEmitter<void>();
  @Output() accion = new EventEmitter<AsignacionEvento>();

  seleccionandoTecnico = false;
  tecnicoSeleccionado: Tecnico | null = null;

  constructor(private sanitizer: DomSanitizer) {}

  get tecnicosDisponibles(): Tecnico[] {
    return this.tecnicos.filter(t => t.disponible);
  }

  iniciarSeleccionTecnico() {
    this.tecnicoSeleccionado = null;
    this.seleccionandoTecnico = true;
  }

  confirmarAsignacion() {
    if (!this.tecnicoSeleccionado) return;
    this.accion.emit({ estado: 'asignada', tecnicoId: this.tecnicoSeleccionado.id });
    this.seleccionandoTecnico = false;
    this.tecnicoSeleccionado = null;
  }

  nombreTecnicoAsignado(): string {
    const tec = this.tecnicos.find(t => t.id === this.solicitud.tecnico_id);
    return tec ? `${tec.nombre} — ${tec.especialidad}` : `Técnico #${this.solicitud.tecnico_id}`;
  }

  getMapUrl(lat: number, lng: number): SafeResourceUrl {
    const url = `https://www.openstreetmap.org/export/embed.html?bbox=${lng - 0.005}%2C${lat - 0.005}%2C${lng + 0.005}%2C${lat + 0.005}&layer=mapnik&marker=${lat}%2C${lng}`;
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

  onOverlayClick(event: Event) {
    if ((event.target as HTMLElement).classList.contains('modal-overlay')) {
      this.cerrar.emit();
    }
  }

  etiquetaEstado(estado: string): string {
    const map: Record<string, string> = {
      pendiente: 'Pendiente', asignada: 'Técnico Asignado',
      en_progreso: 'En Progreso', resuelta: 'Finalizada', cancelada: 'Cancelada'
    };
    return map[estado] ?? estado;
  }
}
