import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Tecnico } from '../core/tecnico.service';
import { Solicitud } from '../core/incident.service';

@Component({
  selector: 'app-detalle-tecnico-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="modal-overlay" (click)="onOverlayClick($event)">
      <div class="modal-box" role="dialog" aria-modal="true">

        <!-- CABECERA -->
        <div class="modal-header">
          <div class="tec-perfil">
            <div class="tec-avatar">{{ tecnico.nombre.charAt(0) }}</div>
            <div>
              <h2>{{ tecnico.nombre }}</h2>
              <span class="especialidad">{{ getEspecialidadesTexto(tecnico) }}</span>
            </div>
          </div>
          <div class="header-right">
            <span class="disponibilidad-badge" [class.libre]="tecnico.disponible" [class.ocupado]="!tecnico.disponible">
              {{ tecnico.disponible ? '🟢 Disponible' : '🔴 En servicio' }}
            </span>
            <button class="modal-close" (click)="cerrar.emit()">✕</button>
          </div>
        </div>

        <!-- CUERPO -->
        <div class="modal-body">

          <!-- SOLICITUD ACTIVA -->
          <ng-container *ngIf="solicitudActiva; else sinAsignacion">

            <div class="seccion-titulo">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
              Emergencia Activa Asignada
            </div>

            <div class="solicitud-card">
              <div class="sol-top">
                <div class="sol-id">Emergencia #{{ solicitudActiva.id }}</div>
                <span class="status-chip" [ngClass]="solicitudActiva.estado">
                  {{ etiquetaEstado(solicitudActiva.estado) }}
                </span>
              </div>

              <div class="info-row">
                <label>Descripción</label>
                <p>{{ solicitudActiva.descripcion }}</p>
              </div>

              <!-- Bloque IA compacto -->
              <div class="ai-mini" *ngIf="solicitudActiva.clasificacion_ia">
                <div class="ai-mini-header">
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>
                  Diagnóstico IA
                </div>
                <div class="ai-mini-grid">
                  <div class="ai-mini-item">
                    <span>Tipo</span>
                    <strong>{{ solicitudActiva.clasificacion_ia }}</strong>
                  </div>
                  <div class="ai-mini-item">
                    <span>Prioridad</span>
                    <strong [ngClass]="solicitudActiva.prioridad_ia?.toLowerCase()">
                      {{ solicitudActiva.prioridad_ia }}
                    </strong>
                  </div>
                </div>
                <p class="ai-mini-resumen">{{ solicitudActiva.resumen_ia }}</p>
              </div>

              <div class="info-row">
                <label>Ubicación del Cliente</label>
                <p class="coords">
                  📍 {{ solicitudActiva.latitud | number:'1.4-5' }},
                  {{ solicitudActiva.longitud | number:'1.4-5' }}
                </p>
              </div>

              <div class="info-row">
                <label>Fecha de Solicitud</label>
                <p>{{ solicitudActiva.fecha_creacion | date:'dd MMM yyyy, HH:mm' }}</p>
              </div>
            </div>

          </ng-container>

          <!-- SIN ASIGNACIÓN -->
          <ng-template #sinAsignacion>
            <div class="sin-asignacion">
              <div class="sin-icon">🔧</div>
              <h3>Sin emergencia activa</h3>
              <p>Este técnico está disponible para ser asignado a la próxima solicitud.</p>
            </div>
          </ng-template>

          <!-- HISTORIAL (solicitudes resueltas por este técnico) -->
          <div *ngIf="historialTecnico.length > 0">
            <div class="seccion-titulo" style="margin-top: 20px;">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              Historial de Atenciones ({{ historialTecnico.length }})
            </div>
            <div class="historial-lista">
              <div class="historial-item" *ngFor="let h of historialTecnico">
                <div class="h-id">#{{ h.id }}</div>
                <div class="h-info">
                  <p>{{ h.descripcion }}</p>
                  <span>{{ h.fecha_creacion | date:'dd MMM, HH:mm' }}</span>
                </div>
                <span class="status-chip" [ngClass]="h.estado">{{ etiquetaEstado(h.estado) }}</span>
              </div>
            </div>
          </div>

        </div>

        <!-- FOOTER -->
        <div class="modal-footer">
          <button class="btn-ghost" (click)="cerrar.emit()">Cerrar</button>
        </div>

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
      width: 100%; max-width: 560px; max-height: 90vh; overflow-y: auto;
      animation: slideUp .2s ease;
    }
    @keyframes slideUp {
      from { transform: translateY(16px); opacity: 0; }
      to   { transform: translateY(0);    opacity: 1; }
    }

    /* Cabecera */
    .modal-header {
      padding: 20px 24px;
      display: flex; justify-content: space-between; align-items: center;
      border-bottom: 1px solid #f3f4f6;
      position: sticky; top: 0; background: #fff; z-index: 1;
      gap: 16px;
    }
    .tec-perfil { display: flex; align-items: center; gap: 14px; }
    .tec-avatar {
      width: 48px; height: 48px; border-radius: 50%;
      background: #e0e7ff; color: #3730a3;
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 20px; flex-shrink: 0;
    }
    .tec-perfil h2 { margin: 0 0 4px; font-size: 18px; font-weight: 700; }
    .especialidad { font-size: 13px; color: #6b7280; }
    .header-right { display: flex; align-items: center; gap: 10px; }
    .disponibilidad-badge { font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 999px; white-space: nowrap; }
    .disponibilidad-badge.libre   { background: #dcfce7; color: #166534; }
    .disponibilidad-badge.ocupado { background: #fee2e2; color: #991b1b; }
    .modal-close {
      background: #f3f4f6; border: none; width: 30px; height: 30px;
      border-radius: 50%; cursor: pointer; font-size: 14px;
      display: flex; align-items: center; justify-content: center;
      color: #6b7280; flex-shrink: 0;
    }
    .modal-close:hover { background: #e5e7eb; color: #111827; }

    /* Cuerpo */
    .modal-body { padding: 24px; display: flex; flex-direction: column; gap: 16px; }

    .seccion-titulo {
      display: flex; align-items: center; gap: 8px;
      font-size: 13px; font-weight: 700; color: #374151;
      text-transform: uppercase; letter-spacing: .04em;
      margin-bottom: 4px;
    }

    /* Solicitud Activa */
    .solicitud-card {
      border: 1px solid #e5e7eb; border-radius: 10px;
      overflow: hidden;
    }
    .sol-top {
      display: flex; justify-content: space-between; align-items: center;
      padding: 14px 16px; background: #f9fafb; border-bottom: 1px solid #f0f0f0;
    }
    .sol-id { font-size: 15px; font-weight: 700; color: #111827; }
    .info-row { padding: 12px 16px; border-bottom: 1px solid #f9fafb; }
    .info-row:last-child { border-bottom: none; }
    .info-row label { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #9ca3af; font-weight: 600; margin-bottom: 4px; }
    .info-row p { margin: 0; font-size: 14px; color: #374151; line-height: 1.5; }
    .coords { font-size: 13px; color: #6b7280; }

    /* AI mini */
    .ai-mini {
      margin: 0 16px 0;
      background: linear-gradient(135deg, #faf5ff, #f0f0ff);
      border: 1px solid #e9d5ff; border-radius: 8px;
      padding: 12px; margin-bottom: 0;
    }
    .ai-mini-header {
      display: flex; align-items: center; gap: 6px;
      font-size: 12px; font-weight: 700; color: #7c3aed; margin-bottom: 10px;
    }
    .ai-mini-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px; }
    .ai-mini-item span { display: block; font-size: 10px; text-transform: uppercase; color: #9333ea; font-weight: 600; margin-bottom: 2px; }
    .ai-mini-item strong { font-size: 13px; color: #4c1d95; }
    .ai-mini-item strong.alta   { color: #dc2626; }
    .ai-mini-item strong.media  { color: #d97706; }
    .ai-mini-item strong.baja   { color: #16a34a; }
    .ai-mini-resumen { margin: 0; font-size: 12px; color: #6d28d9; line-height: 1.5; }

    /* Sin asignacion */
    .sin-asignacion {
      text-align: center; padding: 36px 20px;
      background: #f9fafb; border-radius: 10px; border: 1px dashed #e5e7eb;
    }
    .sin-icon { font-size: 36px; margin-bottom: 12px; }
    .sin-asignacion h3 { margin: 0 0 8px; font-size: 16px; color: #374151; }
    .sin-asignacion p  { margin: 0; font-size: 14px; color: #9ca3af; }

    /* Historial */
    .historial-lista { display: flex; flex-direction: column; gap: 8px; }
    .historial-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: #f9fafb; border-radius: 8px; border: 1px solid #f3f4f6; }
    .h-id { font-size: 12px; font-weight: 700; color: #9ca3af; min-width: 28px; }
    .h-info { flex: 1; min-width: 0; }
    .h-info p { margin: 0 0 2px; font-size: 13px; color: #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .h-info span { font-size: 11px; color: #9ca3af; }

    /* Status chips */
    .status-chip { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 999px; white-space: nowrap; flex-shrink: 0; }
    .pendiente   { background: #fef9c3; color: #854d0e; }
    .asignada    { background: #dbeafe; color: #1e40af; }
    .en_progreso { background: #e0e7ff; color: #3730a3; }
    .resuelta    { background: #dcfce7; color: #166534; }
    .cancelada   { background: #fee2e2; color: #991b1b; }

    /* Footer */
    .modal-footer { padding: 14px 24px; border-top: 1px solid #f3f4f6; display: flex; justify-content: flex-end; }
    .btn-ghost { background: #f9fafb; color: #6b7280; border: 1px solid #e5e7eb; padding: 8px 20px; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; }
    .btn-ghost:hover { background: #f3f4f6; color: #111827; }
  `]
})
export class DetalleTecnicoModalComponent {
  @Input() tecnico!: Tecnico;
  /** Todas las solicitudes del sistema para cruzar con el técnico */
  @Input() solicitudes: Solicitud[] = [];

  @Output() cerrar = new EventEmitter<void>();

  /** Solicitud activa (asignada o en progreso) vinculada a este técnico */
  get solicitudActiva(): Solicitud | undefined {
    return this.solicitudes.find(
      s => s.tecnico_id === this.tecnico.id &&
           (s.estado === 'asignada' || s.estado === 'en_progreso')
    );
  }

  /** Historial: solicitudes resueltas o canceladas por este técnico */
  get historialTecnico(): Solicitud[] {
    return this.solicitudes.filter(
      s => s.tecnico_id === this.tecnico.id &&
           (s.estado === 'resuelta' || s.estado === 'cancelada')
    );
  }

  getEspecialidadesTexto(tecnico: Tecnico): string {
    const nombres = (tecnico.especialidades || [])
      .map(item => item.nombre?.trim())
      .filter((nombre): nombre is string => Boolean(nombre));

    return nombres.length > 0 ? nombres.join(', ') : 'Sin especialidades';
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
