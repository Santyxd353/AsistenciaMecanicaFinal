import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import {
  AdminDashboardService,
  AdminSolicitud,
  AdminTaller,
  AdminTecnico,
  SuperDashboard,
} from '../core/admin-dashboard.service';
import { AuthService } from '../core/auth.service';
import { KpiDashboardComponent } from '../shared/kpi-dashboard/kpi-dashboard.component';
import {
  MapaGeolocalizacionComponent,
  PuntoMapaGeolocalizacion,
} from '../mapa/geolocalizacion/mapa-geolocalizacion.component';

type AdminTab = 'overview' | 'tenants' | 'talleres' | 'solicitudes' | 'tecnicos' | 'pagos' | 'auditoria';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, KpiDashboardComponent, MapaGeolocalizacionComponent],
  template: `
    <div class="admin-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark">SM</div>
          <div>
            <strong>Super Admin</strong>
            <span>SaaS vehicular</span>
          </div>
        </div>

        <nav>
          <button *ngFor="let item of tabs" type="button" [class.active]="activeTab === item.id" (click)="activeTab = item.id">
            <span>{{ item.icon }}</span>
            {{ item.label }}
          </button>
        </nav>

        <div class="sidebar-footer">
          <span>{{ currentUserLabel }}</span>
          <button type="button" (click)="logout()">Cerrar sesión</button>
        </div>
      </aside>

      <main class="content">
        <header class="topbar">
          <div>
            <p class="kicker">Vista global</p>
            <h1>Dashboard Super Admin</h1>
            <span>Todos los tenants, talleres, técnicos, reportes, pagos y auditoría.</span>
          </div>
          <div class="actions">
            <a routerLink="/taller" class="ghost">Panel taller</a>
            <button type="button" class="primary" (click)="load()">{{ loading ? 'Cargando...' : 'Actualizar' }}</button>
          </div>
        </header>

        <section *ngIf="error" class="error">{{ error }}</section>

        <ng-container *ngIf="data; else loadingTpl">
          <section class="metric-grid">
            <article class="metric-card strong">
              <span>Tenants</span>
              <strong>{{ data.resumen.tenants }}</strong>
              <small>Redes activas del SaaS</small>
            </article>
            <article class="metric-card">
              <span>Talleres</span>
              <strong>{{ data.resumen.talleres }}</strong>
              <small>{{ data.resumen.tecnicos }} técnicos registrados</small>
            </article>
            <article class="metric-card">
              <span>Reportes</span>
              <strong>{{ data.resumen.solicitudes }}</strong>
              <small>{{ estadoCount('pendiente') + estadoCount('buscando_taller') }} en búsqueda</small>
            </article>
            <article class="metric-card">
              <span>Comisión plataforma</span>
              <strong>Bs {{ data.resumen.comision_plataforma | number:'1.0-0' }}</strong>
              <small>Bruto Bs {{ data.resumen.ingreso_bruto | number:'1.0-0' }}</small>
            </article>
          </section>

          <section *ngIf="activeTab === 'overview'" class="overview-grid">
            <article class="panel map-panel">
              <div class="panel-head">
                <div>
                  <p class="kicker">Mapa operativo</p>
                  <h2>Red en vivo</h2>
                </div>
                <span>{{ mapaPuntos.length }} puntos</span>
              </div>
              <app-mapa-geolocalizacion [puntos]="mapaPuntos" [alto]="'420px'" />
            </article>

            <article class="panel">
              <div class="panel-head">
                <div>
                  <p class="kicker">Estados</p>
                  <h2>Reportes por flujo</h2>
                </div>
              </div>
              <div class="bar-list">
                <div class="bar-row" *ngFor="let item of estadoRows">
                  <div>
                    <strong>{{ estadoLabel(item.key) }}</strong>
                    <span>{{ item.value }} reportes</span>
                  </div>
                  <div class="bar"><span [style.width.%]="barWidth(item.value)"></span></div>
                </div>
              </div>
            </article>

            <article class="panel wide">
              <app-kpi-dashboard></app-kpi-dashboard>
            </article>
          </section>

          <section *ngIf="activeTab === 'tenants'" class="table-panel">
            <div class="panel-head">
              <div><p class="kicker">SaaS</p><h2>Tenants</h2></div>
            </div>
            <table>
              <thead><tr><th>Tenant</th><th>Slug</th><th>Usuarios</th><th>Talleres</th><th>Reportes</th><th>Estado</th></tr></thead>
              <tbody>
                <tr *ngFor="let tenant of data.tenants">
                  <td><strong>{{ tenant.nombre }}</strong></td>
                  <td>{{ tenant.slug }}</td>
                  <td>{{ tenant.usuarios }}</td>
                  <td>{{ tenant.talleres }}</td>
                  <td>{{ tenant.solicitudes }}</td>
                  <td><span class="pill" [class.ok]="tenant.activo">{{ tenant.activo ? 'Activo' : 'Pausado' }}</span></td>
                </tr>
              </tbody>
            </table>
          </section>

          <section *ngIf="activeTab === 'talleres'" class="card-list">
            <article class="workshop-card" *ngFor="let taller of filteredTalleres">
              <div>
                <p class="kicker">{{ taller.tenant }}</p>
                <h3>{{ taller.nombre_comercial }}</h3>
                <span>{{ taller.direccion }}</span>
              </div>
              <div class="workshop-meta">
                <span>{{ taller.tecnicos }} técnicos</span>
                <span>{{ taller.solicitudes }} reportes</span>
                <span>{{ taller.calificacion_promedio | number:'1.1-1' }} ★</span>
              </div>
              <small>Propietario: {{ taller.propietario }} · Capacidad {{ taller.capacidad_operativa }}</small>
            </article>
          </section>

          <section *ngIf="activeTab === 'solicitudes'" class="table-panel">
            <div class="panel-head">
              <div><p class="kicker">Emergencias</p><h2>Reportes recientes</h2></div>
              <input [(ngModel)]="search" placeholder="Buscar reporte, taller o tenant" />
            </div>
            <table>
              <thead><tr><th>ID</th><th>Tenant</th><th>Descripción</th><th>Estado</th><th>Tipo IA</th><th>Taller</th><th>Técnico</th><th>Fecha</th></tr></thead>
              <tbody>
                <tr *ngFor="let solicitud of filteredSolicitudes">
                  <td>#{{ solicitud.id }}</td>
                  <td>{{ solicitud.tenant }}</td>
                  <td class="truncate">{{ solicitud.descripcion }}</td>
                  <td><span class="status" [ngClass]="solicitud.estado">{{ estadoLabel(solicitud.estado) }}</span></td>
                  <td>{{ solicitud.clasificacion_ia || 'Sin clasificar' }}</td>
                  <td>{{ solicitud.taller }}</td>
                  <td>{{ solicitud.tecnico }}</td>
                  <td>{{ solicitud.fecha_creacion | date:'dd/MM HH:mm' }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section *ngIf="activeTab === 'tecnicos'" class="card-list">
            <article class="tech-card" *ngFor="let tecnico of filteredTecnicos">
              <div class="avatar">{{ tecnico.nombre.charAt(0) }}</div>
              <div>
                <h3>{{ tecnico.nombre }}</h3>
                <span>{{ tecnico.taller }} · {{ tecnico.tenant }}</span>
              </div>
              <strong [class.available]="tecnico.disponible">{{ tecnico.disponible ? 'Disponible' : 'Ocupado' }}</strong>
            </article>
          </section>

          <section *ngIf="activeTab === 'pagos'" class="table-panel">
            <div class="panel-head"><div><p class="kicker">Finanzas</p><h2>Pagos mock</h2></div></div>
            <table>
              <thead><tr><th>ID</th><th>Tenant</th><th>Solicitud</th><th>Monto</th><th>Comisión</th><th>Estado</th><th>Método</th><th>Fecha</th></tr></thead>
              <tbody>
                <tr *ngFor="let pago of data.pagos">
                  <td>#{{ pago.id }}</td><td>{{ pago.tenant }}</td><td>#{{ pago.solicitud_id }}</td>
                  <td>Bs {{ pago.monto | number:'1.2-2' }}</td><td>Bs {{ pago.comision_plataforma | number:'1.2-2' }}</td>
                  <td>{{ pago.estado }}</td><td>{{ pago.metodo }}</td><td>{{ pago.fecha_creacion | date:'dd/MM HH:mm' }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section *ngIf="activeTab === 'auditoria'" class="timeline">
            <article class="audit-item" *ngFor="let item of data.auditoria">
              <span>{{ item.fecha_creacion | date:'dd/MM HH:mm:ss' }}</span>
              <strong>{{ item.accion }}</strong>
              <p>{{ item.tenant }} · {{ item.entidad }} #{{ item.entidad_id || '-' }} · {{ item.detalle || 'Sin detalle' }}</p>
            </article>
          </section>
        </ng-container>

        <ng-template #loadingTpl>
          <section class="skeleton-grid">
            <span></span><span></span><span></span><span></span>
          </section>
        </ng-template>
      </main>
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; font-family: Inter, "Segoe UI", Arial, sans-serif; color: #2f241d; }
    .admin-shell { min-height: 100vh; display: grid; grid-template-columns: 280px 1fr; background: #f5efe7; }
    .sidebar { background: #ffffff; color: #2f241d; border-right: 1px solid #ead7c4; padding: 20px; display: flex; flex-direction: column; gap: 24px; position: sticky; top: 0; height: 100vh; }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-mark { width: 44px; height: 44px; border-radius: 10px; display: grid; place-items: center; background: #f3e6d7; color: #7c4a24; font-weight: 900; }
    .brand span, .sidebar-footer span { display: block; color: #7a6554; font-size: 12px; margin-top: 3px; }
    nav { display: grid; gap: 8px; }
    nav button, .sidebar-footer button { border: 0; border-radius: 8px; padding: 12px; background: transparent; color: #4b3528; text-align: left; cursor: pointer; font-weight: 800; }
    nav button { display: flex; align-items: center; gap: 10px; }
    nav button.active, nav button:hover { background: #f3e6d7; color: #8b5e34; }
    .sidebar-footer { margin-top: auto; border-top: 1px solid #ead7c4; padding-top: 14px; }
    .sidebar-footer button { width: 100%; margin-top: 10px; background: #fff8ef; border: 1px solid #ead7c4; text-align: center; }
    .content { padding: 26px; overflow: hidden; }
    .topbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 18px; }
    .topbar h1 { margin: 0; font-size: 34px; letter-spacing: 0; }
    .topbar span { color: #7a6554; }
    .kicker { margin: 0 0 4px; color: #8b5e34; font-size: 11px; text-transform: uppercase; letter-spacing: .14em; font-weight: 900; }
    .actions { display: flex; gap: 10px; }
    .primary, .ghost { border: 0; border-radius: 999px; padding: 11px 16px; font-weight: 900; cursor: pointer; text-decoration: none; }
    .primary { background: #8b5e34; color: #fff; }
    .ghost { background: #fff; color: #2f241d; border: 1px solid #ead7c4; }
    .metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
    .metric-card, .panel, .table-panel, .workshop-card, .tech-card, .audit-item { background: #fff; border: 1px solid #ead7c4; border-radius: 14px; box-shadow: 0 10px 30px rgba(86,52,28,.08); }
    .metric-card { padding: 18px; display: grid; gap: 6px; min-height: 128px; }
    .metric-card.strong { background: #fff; color: #2f241d; border-left: 4px solid #8b5e34; }
    .metric-card span { color: #7a6554; font-weight: 800; }
    .metric-card.strong span, .metric-card.strong small { color: #7a6554; }
    .metric-card strong { font-size: 32px; }
    .metric-card small { color: #7a6554; }
    .overview-grid { display: grid; grid-template-columns: 1.4fr .8fr; gap: 16px; }
    .wide { grid-column: 1 / -1; padding: 0; border: 0; background: transparent; box-shadow: none; }
    .panel { padding: 18px; }
    .panel-head { display: flex; justify-content: space-between; align-items: center; gap: 14px; margin-bottom: 14px; }
    .panel-head h2 { margin: 0; }
    .panel-head input { border: 1px solid #ead7c4; border-radius: 999px; padding: 10px 14px; min-width: 280px; }
    .bar-list { display: grid; gap: 14px; }
    .bar-row { display: grid; gap: 7px; }
    .bar-row div:first-child { display: flex; justify-content: space-between; color: #6f5745; }
    .bar { height: 12px; background: #ead7c4; border-radius: 999px; overflow: hidden; }
    .bar span { display: block; height: 100%; background: #8b5e34; }
    .table-panel { overflow: auto; }
    .table-panel .panel-head { padding: 18px; margin: 0; border-bottom: 1px solid #ead7c4; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 13px 16px; text-align: left; border-bottom: 1px solid #ead7c4; font-size: 13px; vertical-align: top; }
    th { color: #7a6554; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }
    .truncate { max-width: 340px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .pill, .status { display: inline-flex; border-radius: 999px; padding: 4px 9px; background: #ead7c4; font-weight: 900; font-size: 12px; }
    .pill.ok { background: #dcfce7; color: #166534; }
    .pendiente, .buscando_taller { background: #fef9c3; color: #854d0e; }
    .asignada, .tecnico_en_camino, .tecnico_llego { background: #f3e6d7; color: #8b5e34; }
    .en_proceso { background: #e0e7ff; color: #3730a3; }
    .finalizado, .resuelta { background: #dcfce7; color: #166534; }
    .cancelado, .cancelada { background: #fee2e2; color: #991b1b; }
    .card-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 14px; }
    .workshop-card, .tech-card { padding: 16px; display: grid; gap: 12px; }
    .workshop-card h3, .tech-card h3 { margin: 0 0 4px; }
    .workshop-card span, .tech-card span { color: #7a6554; }
    .workshop-meta { display: flex; flex-wrap: wrap; gap: 8px; }
    .workshop-meta span { background: #eef2ff; color: #3730a3; padding: 6px 9px; border-radius: 999px; font-weight: 900; font-size: 12px; }
    .tech-card { grid-template-columns: auto 1fr auto; align-items: center; }
    .avatar { width: 42px; height: 42px; border-radius: 50%; background: #8b5e34; color: #fff; display: grid; place-items: center; font-weight: 900; }
    .tech-card strong.available { color: #15803d; }
    .timeline { display: grid; gap: 10px; }
    .audit-item { padding: 14px 16px; }
    .audit-item span { color: #7a6554; font-size: 12px; }
    .audit-item strong { display: block; margin: 4px 0; }
    .audit-item p { margin: 0; color: #6f5745; }
    .error { padding: 12px 14px; background: #fee2e2; color: #991b1b; border-radius: 12px; margin-bottom: 14px; }
    .skeleton-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .skeleton-grid span { height: 130px; border-radius: 14px; background: linear-gradient(90deg, #ead7c4, #fff8ef, #ead7c4); background-size: 220% 100%; animation: pulse 1.5s infinite; }
    @keyframes pulse { to { background-position: -220% 0; } }
    @media (max-width: 980px) {
      .admin-shell { grid-template-columns: 1fr; }
      .sidebar { position: static; height: auto; }
      .metric-grid, .overview-grid, .skeleton-grid { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; }
    }
  `],
})
export class DashboardComponent implements OnInit {
  data: SuperDashboard | null = null;
  loading = false;
  error = '';
  activeTab: AdminTab = 'overview';
  search = '';

  readonly tabs: Array<{ id: AdminTab; label: string; icon: string }> = [
    { id: 'overview', label: 'Resumen', icon: '▦' },
    { id: 'tenants', label: 'Tenants', icon: '□' },
    { id: 'talleres', label: 'Talleres', icon: '⚙' },
    { id: 'solicitudes', label: 'Reportes', icon: '!' },
    { id: 'tecnicos', label: 'Técnicos', icon: '●' },
    { id: 'pagos', label: 'Pagos', icon: '$' },
    { id: 'auditoria', label: 'Auditoría', icon: '≡' },
  ];

  constructor(
    private adminDashboard: AdminDashboardService,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }
    if (this.authService.getCurrentRole() !== 'admin') {
      this.router.navigate([this.authService.getDefaultRouteForRole()]);
      return;
    }
    this.load();
  }

  get currentUserLabel(): string {
    const user = this.authService.getCurrentUser();
    return user?.full_name || user?.username || 'Superadmin';
  }

  get estadoRows(): Array<{ key: string; value: number }> {
    return Object.entries(this.data?.solicitudes.por_estado ?? {})
      .map(([key, value]) => ({ key, value }))
      .sort((a, b) => b.value - a.value);
  }

  get mapaPuntos(): PuntoMapaGeolocalizacion[] {
    if (!this.data) return [];
    const talleres = this.data.mapa.talleres.map((item) => ({
      latitud: item.latitud,
      longitud: item.longitud,
      etiqueta: `Taller #${item.id} ${item.nombre ?? ''}`,
      tipo: 'taller' as const,
    }));
    const tecnicos = this.data.mapa.tecnicos.map((item) => ({
      latitud: item.latitud,
      longitud: item.longitud,
      etiqueta: `Técnico #${item.id} ${item.nombre ?? ''}`,
      tipo: 'tecnico' as const,
    }));
    const solicitudes = this.data.mapa.solicitudes.map((item) => ({
      latitud: item.latitud,
      longitud: item.longitud,
      etiqueta: `Reporte #${item.id}: ${item.descripcion ?? item.estado ?? ''}`,
      tipo: 'incidente' as const,
    }));
    return [...talleres, ...tecnicos, ...solicitudes];
  }

  get filteredSolicitudes(): AdminSolicitud[] {
    const q = this.search.trim().toLowerCase();
    const items = this.data?.solicitudes.recientes ?? [];
    if (!q) return items;
    return items.filter((item) =>
      [item.descripcion, item.tenant, item.taller, item.tecnico, item.estado, item.clasificacion_ia ?? '']
        .join(' ')
        .toLowerCase()
        .includes(q),
    );
  }

  get filteredTalleres(): AdminTaller[] {
    return this.data?.talleres ?? [];
  }

  get filteredTecnicos(): AdminTecnico[] {
    return this.data?.tecnicos ?? [];
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.adminDashboard.getSuperDashboard().subscribe({
      next: (data) => {
        this.data = data;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = err?.error?.detail || 'No se pudo cargar el dashboard superadmin.';
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  estadoCount(estado: string): number {
    return this.data?.solicitudes.por_estado?.[estado] ?? 0;
  }

  estadoLabel(estado: string): string {
    const map: Record<string, string> = {
      pendiente: 'Pendiente',
      buscando_taller: 'Buscando taller',
      asignada: 'Asignado',
      tecnico_en_camino: 'En camino',
      tecnico_llego: 'Llegó',
      en_proceso: 'En proceso',
      finalizado: 'Finalizado',
      cancelado: 'Cancelado',
      resuelta: 'Finalizado',
      cancelada: 'Cancelado',
    };
    return map[estado] ?? estado;
  }

  barWidth(value: number): number {
    const max = Math.max(...this.estadoRows.map((item) => item.value), 1);
    return Math.max(6, Math.round((value / max) * 100));
  }

  logout(): void {
    this.authService.logout();
  }
}


