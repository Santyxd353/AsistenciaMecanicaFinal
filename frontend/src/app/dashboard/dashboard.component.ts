import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../core/auth.service';
import { SolicitudService, Solicitud } from '../core/incident.service';
import { TecnicoService, Tecnico } from '../core/tecnico.service';
import { DetalleSolicitudModalComponent, AsignacionEvento } from './detalle-solicitud-modal.component';
import { DetalleTecnicoModalComponent } from './detalle-tecnico-modal.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, DetalleSolicitudModalComponent, DetalleTecnicoModalComponent],
  template: `
    <div class="dashboard">
      <header class="header">
        <div class="logo">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
          </svg>
          <h1>Sistema Mecánico</h1>
        </div>
        <div class="user-actions">
          <span class="role-badge">Admin de Taller</span>
          <button (click)="logout()" class="btn-logout">Cerrar Sesión</button>
        </div>
      </header>

      <main class="main-content">
        <div class="dashboard-grid">

          <!-- Panel Solicitudes -->
          <div class="panel">
            <div class="panel-header">
              <div>
                <h2>Solicitudes</h2>
                <span class="subtitle">{{ solicitudes.length }} registradas</span>
              </div>
              <button class="btn-secondary" (click)="reportarIncidente()">+ Simular Reporte</button>
            </div>

            <div class="solicitudes-lista" *ngIf="solicitudes.length > 0; else noSolicitudes">
              <div
                class="solicitud-row"
                *ngFor="let sol of solicitudes"
                (click)="abrirModal(sol)"
              >
                <div class="sol-left">
                  <span class="sol-id">#{{ sol.id }}</span>
                  <div class="sol-info">
                    <p class="sol-desc">{{ sol.descripcion }}</p>
                    <span class="sol-fecha">{{ sol.fecha_creacion | date:'dd MMM, HH:mm' }}</span>
                  </div>
                </div>
                <div class="sol-right">
                  <span class="status-chip" [ngClass]="sol.estado">{{ etiquetaEstado(sol.estado) }}</span>
                  <svg class="chevron" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="m9 18 6-6-6-6"/>
                  </svg>
                </div>
              </div>
            </div>
            <ng-template #noSolicitudes>
              <div class="empty-state">
                <p>No hay solicitudes aún. Simula un reporte con el botón de arriba.</p>
              </div>
            </ng-template>
          </div>

          <!-- Panel Técnicos -->
          <div class="panel">
            <div class="panel-header">
              <div>
                <h2>Mis Técnicos</h2>
                <span class="subtitle">{{ tecnicosLibres() }} disponibles de {{ tecnicos.length }}</span>
              </div>
              <button class="btn-secondary" (click)="mostrarFormTecnico = !mostrarFormTecnico">
                {{ mostrarFormTecnico ? 'Cancelar' : '+ Añadir' }}
              </button>
            </div>

            <div class="tech-form-container" *ngIf="mostrarFormTecnico">
              <input type="text" [(ngModel)]="nuevoTecnicoNombre" placeholder="Nombre completo del técnico" class="input-field" />
              <select [(ngModel)]="nuevoTecnicoEspecialidad" class="input-field">
                <option value="" disabled selected>Selecciona su especialidad</option>
                <option value="Mecánica General">Mecánica General</option>
                <option value="Llantas y Suspensión">Llantas y Suspensión</option>
                <option value="Eléctrico y Baterías">Eléctrico y Baterías</option>
                <option value="Grúa y Remolque">Grúa y Remolque</option>
              </select>
              <button class="btn-confirm" [disabled]="!nuevoTecnicoNombre || !nuevoTecnicoEspecialidad" (click)="guardarTecnico()">
                Registrar Técnico
              </button>
            </div>

            <div class="tech-grid" *ngIf="tecnicos.length > 0; else noTechs">
              <div
                class="tech-card"
                *ngFor="let tec of tecnicos"
                (click)="abrirModalTecnico(tec)"
                title="Ver detalles del técnico"
              >
                <div class="tech-avatar">{{ tec.nombre.charAt(0) }}</div>
                <div class="tech-info">
                  <strong>{{ tec.nombre }}</strong>
                  <span>{{ tec.especialidad }}</span>
                </div>
                <button
                  class="toggle-btn"
                  [class.libre]="tec.disponible"
                  [class.ocupado]="!tec.disponible"
                  (click)="$event.stopPropagation(); toggleDisponibilidad(tec)"
                >
                  {{ tec.disponible ? 'Libre' : 'Ocupado' }}
                </button>
              </div>
            </div>
            <ng-template #noTechs>
              <div class="empty-state">
                <p>No hay técnicos registrados. Añade uno para asignar solicitudes.</p>
              </div>
            </ng-template>
          </div>

        </div>
      </main>

      <!-- Modal de detalle de solicitud -->
      <app-detalle-solicitud-modal
        *ngIf="solicitudSeleccionada"
        [solicitud]="solicitudSeleccionada"
        [tecnicos]="tecnicos"
        (cerrar)="cerrarModal()"
        (accion)="manejarAccion($event)"
      />

      <!-- Modal de detalle de técnico -->
      <app-detalle-tecnico-modal
        *ngIf="tecnicoSeleccionado"
        [tecnico]="tecnicoSeleccionado"
        [solicitudes]="solicitudes"
        (cerrar)="tecnicoSeleccionado = null"
      />
    </div>
  `,
  styles: [`
    :host { font-family: 'Inter', system-ui, sans-serif; display: block; min-height: 100vh; background: #f4f5f7; color: #111827; }

    .dashboard { display: flex; flex-direction: column; min-height: 100vh; }

    /* HEADER */
    .header {
      background: #fff; padding: 14px 28px;
      display: flex; justify-content: space-between; align-items: center;
      border-bottom: 1px solid #e5e7eb; position: sticky; top: 0; z-index: 50;
    }
    .logo { display: flex; align-items: center; gap: 10px; }
    .logo h1 { margin: 0; font-size: 17px; font-weight: 700; }
    .user-actions { display: flex; align-items: center; gap: 12px; }
    .role-badge { font-size: 12px; padding: 3px 10px; border-radius: 999px; background: #f3f4f6; border: 1px solid #d1d5db; color: #4b5563; }
    .btn-logout { background: transparent; color: #6b7280; border: 1px solid #e5e7eb; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all .15s; }
    .btn-logout:hover { background: #f9fafb; color: #111827; }

    /* GRID */
    .main-content { padding: 28px; flex: 1; max-width: 1300px; margin: 0 auto; width: 100%; box-sizing: border-box; }
    .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }

    /* PANELS */
    .panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.04); overflow: hidden; }
    .panel-header { padding: 18px 22px; border-bottom: 1px solid #f3f4f6; display: flex; justify-content: space-between; align-items: center; }
    .panel-header h2 { margin: 0; font-size: 15px; font-weight: 700; }
    .subtitle { font-size: 12px; color: #9ca3af; margin-top: 2px; display: block; }
    .btn-secondary { background: #f9fafb; color: #374151; border: 1px solid #e5e7eb; padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; }
    .btn-secondary:hover { background: #f3f4f6; }

    /* SOLICITUDES */
    .solicitudes-lista { overflow-y: auto; max-height: calc(100vh - 220px); }
    .solicitud-row { display: flex; align-items: center; padding: 16px 22px; border-bottom: 1px solid #f9fafb; cursor: pointer; transition: background .15s; }
    .solicitud-row:hover { background: #fafbfc; }
    .solicitud-row:last-child { border-bottom: none; }
    .sol-left { display: flex; align-items: center; gap: 14px; flex: 1; min-width: 0; }
    .sol-id { font-size: 13px; font-weight: 700; color: #9ca3af; min-width: 34px; }
    .sol-info { min-width: 0; }
    .sol-desc { margin: 0 0 4px; font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 320px; }
    .sol-fecha { font-size: 12px; color: #9ca3af; }
    .sol-right { display: flex; align-items: center; gap: 10px; margin-left: 12px; }
    .chevron { color: #d1d5db; }

    /* STATUS */
    .status-chip { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; white-space: nowrap; }
    .pendiente   { background: #fef9c3; color: #854d0e; }
    .asignada    { background: #dbeafe; color: #1e40af; }
    .en_progreso { background: #e0e7ff; color: #3730a3; }
    .resuelta    { background: #dcfce7; color: #166534; }
    .cancelada   { background: #fee2e2; color: #991b1b; }

    /* TÉCNICOS */
    .tech-form-container { padding: 14px 22px; background: #f9fafb; border-bottom: 1px solid #f0f0f0; display: flex; flex-direction: column; gap: 8px; }
    .input-field { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; font-family: inherit; outline: none; }
    .input-field:focus { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,.15); }
    .btn-confirm { background: #111827; color: #fff; border: none; padding: 9px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }
    .btn-confirm:hover:not(:disabled) { background: #000; }
    .btn-confirm:disabled { opacity: .5; cursor: not-allowed; }
    .tech-grid { padding: 14px 22px; display: flex; flex-direction: column; gap: 10px; max-height: calc(100vh - 250px); overflow-y: auto; }
    .tech-card { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid #f3f4f6; border-radius: 8px; }
    .tech-avatar { width: 36px; height: 36px; background: #e0e7ff; color: #3730a3; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px; flex-shrink: 0; }
    .tech-info { flex: 1; min-width: 0; }
    .tech-info strong { display: block; font-size: 14px; }
    .tech-info span { font-size: 12px; color: #6b7280; }
    .toggle-btn { padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; border: none; transition: all .15s; }
    .toggle-btn.libre   { background: #dcfce7; color: #166534; }
    .toggle-btn.libre:hover   { background: #bbf7d0; }
    .toggle-btn.ocupado { background: #fee2e2; color: #991b1b; }
    .toggle-btn.ocupado:hover { background: #fecaca; }
    .empty-state { padding: 36px 22px; text-align: center; color: #9ca3af; font-size: 14px; }
    .empty-state p { margin: 0; }
  `]
})
export class DashboardComponent implements OnInit {
  solicitudes: Solicitud[] = [];
  tecnicos: Tecnico[] = [];
  solicitudSeleccionada: Solicitud | null = null;
  tecnicoSeleccionado: Tecnico | null = null;

  mostrarFormTecnico = false;
  nuevoTecnicoNombre = '';
  nuevoTecnicoEspecialidad = '';

  constructor(
    private authService: AuthService,
    private solicitudService: SolicitudService,
    private tecnicoService: TecnicoService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.cargarSolicitudes();
    this.cargarTecnicos();
  }

  cargarSolicitudes() {
    this.solicitudService.getSolicitudes().subscribe({
      next: (data) => {
        this.solicitudes = data.sort((a, b) => b.id - a.id);
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error cargando solicitudes:', err)
    });
  }

  cargarTecnicos() {
    this.tecnicoService.getTecnicos().subscribe({
      next: (data) => {
        this.tecnicos = data;
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error cargando técnicos:', err)
    });
  }

  abrirModal(sol: Solicitud) {
    this.solicitudSeleccionada = sol;
    this.cdr.detectChanges();
  }

  cerrarModal() {
    this.solicitudSeleccionada = null;
    this.cdr.detectChanges();
  }

  abrirModalTecnico(tec: Tecnico) {
    this.tecnicoSeleccionado = tec;
    this.cdr.detectChanges();
  }

  guardarTecnico() {
    if (!this.nuevoTecnicoNombre || !this.nuevoTecnicoEspecialidad) return;
    this.tecnicoService.createTecnico({
      nombre: this.nuevoTecnicoNombre,
      especialidad: this.nuevoTecnicoEspecialidad,
      disponible: true
    }).subscribe({
      next: (tec: Tecnico) => {
        this.tecnicos = [...this.tecnicos, tec];
        this.nuevoTecnicoNombre = '';
        this.nuevoTecnicoEspecialidad = '';
        this.mostrarFormTecnico = false;
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Error al registrar técnico:', err)
    });
  }

  toggleDisponibilidad(tec: Tecnico) {
    const nuevo = !tec.disponible;
    this.tecnicos = this.tecnicos.map(t => t.id === tec.id ? { ...t, disponible: nuevo } : t);
    this.cdr.detectChanges();
    this.tecnicoService.updateDisponibilidad(tec.id, nuevo).subscribe({
      error: () => {
        this.tecnicos = this.tecnicos.map(t => t.id === tec.id ? { ...t, disponible: tec.disponible } : t);
        this.cdr.detectChanges();
      }
    });
  }

  tecnicosLibres(): number {
    return this.tecnicos.filter(t => t.disponible).length;
  }

  reportarIncidente() {
    const problemas = [
      "El auto no enciende, el tablero se prendió pero escucho un click click cuando giro la llave. Parece batería muerta.",
      "Me quedé en una zanja y mi llanta trasera derecha está pinchada por completo.",
      "Estaba conduciendo y de repente salió un humo muy raro del motor que huele muy feo."
    ];
    const desc = problemas[Math.floor(Math.random() * problemas.length)];
    this.solicitudService.createSolicitud({
      descripcion: desc,
      latitud: -16.489 + Math.random() * 0.1,
      longitud: -68.119 + Math.random() * 0.1,
      estado: 'pendiente'
    }).subscribe({
      next: (nueva) => {
        this.solicitudes = [nueva, ...this.solicitudes];
        this.cdr.detectChanges();
      }
    });
  }

  manejarAccion(evento: AsignacionEvento) {
    if (!this.solicitudSeleccionada) return;

    // Si asigna, marcar el técnico como ocupado localmente
    if (evento.estado === 'asignada' && evento.tecnicoId) {
      this.tecnicos = this.tecnicos.map(t =>
        t.id === evento.tecnicoId ? { ...t, disponible: false } : t
      );
    }

    // Si resuelve o cancela, liberar al técnico asignado localmente
    if ((evento.estado === 'resuelta' || evento.estado === 'cancelada') && this.solicitudSeleccionada.tecnico_id) {
      this.tecnicos = this.tecnicos.map(t =>
        t.id === this.solicitudSeleccionada!.tecnico_id ? { ...t, disponible: true } : t
      );
    }

    this.solicitudService.updateStatus(
      this.solicitudSeleccionada.id,
      evento.estado,
      evento.tecnicoId
    ).subscribe({
      next: (actualizada) => {
        this.solicitudes = this.solicitudes.map(s => s.id === actualizada.id ? actualizada : s);
        this.solicitudSeleccionada = actualizada;
        this.cdr.detectChanges();
      }
    });
  }

  etiquetaEstado(estado: string): string {
    const map: Record<string, string> = {
      pendiente: 'Pendiente', asignada: 'Técnico Asignado',
      en_progreso: 'En Progreso', resuelta: 'Finalizada', cancelada: 'Cancelada'
    };
    return map[estado] ?? estado;
  }

  logout() {
    this.authService.logout();
  }
}
