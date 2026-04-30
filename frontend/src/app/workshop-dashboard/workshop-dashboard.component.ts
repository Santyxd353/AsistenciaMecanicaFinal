import { Component, OnInit, ChangeDetectorRef  } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { timeout } from 'rxjs';

import { AuthService } from '../core/auth.service';
import { WorkshopProfileService, Taller, WorkshopStats } from '../core/workshop-profile.service';

@Component({
  selector: 'app-workshop-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dashboard-shell">
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
          </div>
          <div>
            <p class="eyebrow">Centro de operaciones</p>
            <h1>Panel de Taller</h1>
          </div>
        </div>

        <div class="topbar-actions">
          <button class="btn-ghost" (click)="cargarDatos()">Actualizar</button>
          <button class="btn-ghost" (click)="logout()">Cerrar sesión</button>
        </div>
      </header>

      <main class="content" *ngIf="taller; else loading">
        <section class="hero-card">
          <div class="hero-copy">
            <p class="eyebrow">Resumen del taller</p>
            <h2>{{ taller.nombre_comercial }}</h2>
            <p class="hero-text">
              {{ taller.descripcion || 'Completa la descripción comercial del taller para mejorar la presentación del perfil y el contexto operativo.' }}
            </p>

            <div class="hero-meta">
              <div class="meta-chip">
                <span>Horario</span>
                <strong>{{ taller.horario_atencion }}</strong>
              </div>
              <div class="meta-chip">
                <span>Contacto</span>
                <strong>{{ taller.telefono }}</strong>
              </div>
              <div class="meta-chip">
                <span>Estado</span>
                <strong>{{ workshopHealthLabel }}</strong>
              </div>
            </div>

            <div class="hero-actions">
              <button class="btn-primary" (click)="editarPerfil()">Editar perfil</button>
              <button class="btn-secondary" (click)="mostrarPerfil = !mostrarPerfil">
                {{ mostrarPerfil ? 'Ocultar detalles' : 'Ver detalles' }}
              </button>
            </div>
          </div>

          <aside class="hero-side">
            <div class="health-card">
              <span class="health-label">Lectura rápida</span>
              <strong>{{ workshopHealthTitle }}</strong>
              <p>{{ workshopHealthDescription }}</p>
              <div class="progress-track" aria-hidden="true">
                <span class="progress-fill" [style.width.%]="profileScore"></span>
              </div>
            </div>
          </aside>
        </section>

        <section class="stats-strip" *ngIf="estadisticas; else statsPlaceholder">
          <article class="stat-card stat-card-strong">
            <span>Servicios completados</span>
            <strong>{{ estadisticas.servicios.total_completados }}</strong>
            <p>Atenciones marcadas como resueltas.</p>
          </article>
          <article class="stat-card">
            <span>Calificación promedio</span>
            <strong>{{ estadisticas.taller_info.calificacion_promedio | number:'1.1-1' }}</strong>
            <p>Percepción acumulada del servicio.</p>
          </article>
          <article class="stat-card">
            <span>Técnicos disponibles</span>
            <strong>{{ estadisticas.tecnicos.tecnicos_disponibles }}/{{ estadisticas.tecnicos.total_tecnicos }}</strong>
            <p>Capacidad operativa actual.</p>
          </article>
          <article class="stat-card">
            <span>Ingreso promedio</span>
            <strong>\${{ estadisticas.servicios.ingreso_promedio_por_servicio | number:'1.0-0' }}</strong>
            <p>Promedio por servicio completado.</p>
          </article>
        </section>
        <ng-template #statsPlaceholder>
          <section class="stats-strip">
            <article class="stat-card">
              <span>Estadísticas</span>
              <strong>En proceso</strong>
              <p>Las métricas se cargarán cuando estén disponibles.</p>
            </article>
          </section>
        </ng-template>

        <section class="dashboard-grid">
          <article class="panel detail-panel" *ngIf="mostrarPerfil">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Perfil</p>
                <h3>Información del taller</h3>
              </div>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <span>Dirección</span>
                <strong>{{ taller.direccion }}</strong>
              </div>
              <div class="info-item">
                <span>Email</span>
                <strong>{{ taller.email_contacto || 'No registrado' }}</strong>
              </div>
              <div class="info-item">
                <span>Sitio web</span>
                <strong>{{ taller.sitio_web || 'No registrado' }}</strong>
              </div>
              <div class="info-item">
                <span>Tiempo de respuesta</span>
                <strong>{{ responseTimeLabel }}</strong>
              </div>
            </div>

            <div class="tag-list" *ngIf="specialtyTags.length">
              <span class="tag" *ngFor="let tag of specialtyTags">{{ tag }}</span>
            </div>
          </article>

          <article class="panel analytics-panel" *ngIf="estadisticas">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Estadísticas</p>
                <h3>Análisis de rendimiento</h3>
              </div>
              <p>Una lectura más útil del desempeño actual del taller a partir de las métricas del sistema.</p>
            </div>

            <div class="analytics-grid">
              <div class="analytics-card analytics-card-strong">
                <span>Disponibilidad técnica</span>
                <strong>{{ technicianAvailabilityPercent }}%</strong>
                <p>{{ estadisticas.tecnicos.tecnicos_disponibles }} de {{ estadisticas.tecnicos.total_tecnicos }} técnicos están libres.</p>
              </div>

              <div class="analytics-card">
                <span>Ingreso neto estimado</span>
                <strong>\${{ netAverageIncome | number:'1.0-0' }}</strong>
                <p>Promedio por servicio luego de restar la comisión media de la plataforma.</p>
              </div>

              <div class="analytics-card">
                <span>Comisión promedio</span>
                <strong>\${{ averageCommissionPerService | number:'1.0-0' }}</strong>
                <p>Promedio de comisión pagada por cada servicio resuelto.</p>
              </div>

              <div class="analytics-card">
                <span>Madurez operativa</span>
                <strong>{{ operationalStageLabel }}</strong>
                <p>{{ operationalStageDescription }}</p>
              </div>
            </div>

            <div class="insight-strip">
              <div class="insight-callout">
                <span class="insight-label">Lectura principal</span>
                <strong>{{ mainInsightTitle }}</strong>
                <p>{{ mainInsightDescription }}</p>
              </div>

              <ul class="insight-list">
                <li>{{ completionInsight }}</li>
                <li>{{ availabilityInsight }}</li>
                <li>{{ financeInsight }}</li>
              </ul>
            </div>
          </article>

          <article class="panel action-panel">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Operación</p>
                <h3>Accesos rápidos</h3>
              </div>
              <p>Usa el panel legacy mientras terminamos de migrar toda la operación al nuevo flujo.</p>
            </div>

            <div class="action-grid">
              <button class="action-card" (click)="irATecnicos()">
                <span class="action-badge">Equipo</span>
                <strong>Gestionar técnicos</strong>
                <p>Administra disponibilidad y especialidades del personal.</p>
              </button>
              <button class="action-card" (click)="irASolicitudes()">
                <span class="action-badge">Atención</span>
                <strong>Revisar solicitudes</strong>
                <p>Consulta los casos pendientes y su avance operativo.</p>
              </button>
              <button class="action-card" (click)="editarPerfil()">
                <span class="action-badge">Perfil</span>
                <strong>Editar perfil</strong>
                <p>Ajusta datos comerciales, ubicación y notificaciones.</p>
              </button>
            </div>
          </article>

          <article class="panel summary-panel">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Finanzas</p>
                <h3>Resumen económico</h3>
              </div>
            </div>

            <div class="mini-metrics" *ngIf="estadisticas; else emptyStats">
              <div class="mini-metric">
                <span>Comisiones pagadas</span>
                <strong>\${{ estadisticas.servicios.comisiones_totales_pagadas | number:'1.0-0' }}</strong>
              </div>
              <div class="mini-metric">
                <span>Total histórico</span>
                <strong>{{ taller.total_servicios_completados }}</strong>
              </div>
              <div class="mini-metric">
                <span>Ingreso neto medio</span>
                <strong>\${{ netAverageIncome | number:'1.0-0' }}</strong>
              </div>
              <div class="mini-metric">
                <span>Reportes semanales</span>
                <strong>{{ taller.reportes_semanales ? 'Activos' : 'Inactivos' }}</strong>
              </div>
            </div>

            <ng-template #emptyStats>
              <p class="empty-copy">Las métricas aparecerán aquí cuando existan estadísticas del taller.</p>
            </ng-template>
          </article>

          <article class="panel notification-panel">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Preferencias</p>
                <h3>Notificaciones y reportes</h3>
              </div>
              <p>Ajusta cómo quieres enterarte de nuevas asignaciones, pagos y recordatorios sin salir del panel.</p>
            </div>

            <div class="notification-editor">
              <label class="notification-toggle" [class.enabled]="notificationDraft.notificaciones_nuevas_asignaciones">
                <input type="checkbox" [(ngModel)]="notificationDraft.notificaciones_nuevas_asignaciones" />
                <div>
                  <strong>Nuevas asignaciones</strong>
                  <span>Alertas cuando entren nuevos servicios al flujo del taller.</span>
                </div>
              </label>

              <label class="notification-toggle" [class.enabled]="notificationDraft.notificaciones_push">
                <input type="checkbox" [(ngModel)]="notificationDraft.notificaciones_push" />
                <div>
                  <strong>Push del sistema</strong>
                  <span>Canal rápido para eventos relevantes dentro del panel operativo.</span>
                </div>
              </label>

              <label class="notification-toggle" [class.enabled]="notificationDraft.notificaciones_recordatorios">
                <input type="checkbox" [(ngModel)]="notificationDraft.notificaciones_recordatorios" />
                <div>
                  <strong>Recordatorios operativos</strong>
                  <span>Avisos de pendientes y seguimientos importantes.</span>
                </div>
              </label>

              <label class="notification-toggle" [class.enabled]="notificationDraft.notificaciones_pagos">
                <input type="checkbox" [(ngModel)]="notificationDraft.notificaciones_pagos" />
                <div>
                  <strong>Alertas de pagos</strong>
                  <span>Actualizaciones sobre cobros, comisiones y movimientos financieros.</span>
                </div>
              </label>

              <label class="notification-toggle" [class.enabled]="notificationDraft.reportes_semanales">
                <input type="checkbox" [(ngModel)]="notificationDraft.reportes_semanales" />
                <div>
                  <strong>Reportes semanales</strong>
                  <span>Resumen periódico del rendimiento general del taller.</span>
                </div>
              </label>
            </div>

            <div class="notification-actions">
              <button class="btn-secondary" type="button" (click)="resetNotificationDraft()" [disabled]="savingNotifications || !notificationsDirty">
                Revertir cambios
              </button>
              <button class="btn-primary" type="button" (click)="saveNotificationSettings()" [disabled]="savingNotifications || !notificationsDirty">
                {{ savingNotifications ? 'Guardando...' : 'Guardar preferencias' }}
              </button>
            </div>

            <p class="helper-line" *ngIf="notificationsDirty">Tienes cambios sin guardar en las preferencias del taller.</p>
            <p class="message success" *ngIf="notificationSuccessMessage">{{ notificationSuccessMessage }}</p>
            <p class="message error" *ngIf="notificationErrorMessage">{{ notificationErrorMessage }}</p>
          </article>
        </section>

        <p class="error-banner" *ngIf="errorCarga">{{ errorCarga }}</p>
      </main>

      <ng-template #loading>
        <div class="loading-state">
          <div class="loading-card">
            <p class="eyebrow">Panel de taller</p>
            <div class="error-banner" *ngIf="errorCarga">
              {{ errorCarga }}
              <div class="hero-actions">
                <button class="btn-primary" (click)="cargarDatos()">Reintentar</button>
                <button class="btn-secondary" (click)="editarPerfil()">Editar perfil</button>
              </div>
            </div>
            <h2>Cargando información operativa...</h2>
            <p>Estamos preparando el resumen del taller y sus métricas principales.</p>
          </div>
        </div>
      </ng-template>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif;
    }

    h1,
    h2,
    h3 {
      font-family: inherit;
      font-weight: 800;
      letter-spacing: -0.02em;
    }

    .dashboard-shell {
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(218, 119, 30, 0.18), transparent 28%),
        linear-gradient(180deg, #f9efe2 0%, #f5f7fb 46%, #ffffff 100%);
      color: #18120e;
    }

    .topbar,
    .hero-card,
    .panel,
    .loading-card {
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid #eadcca;
      box-shadow: 0 16px 42px rgba(64, 37, 18, 0.08);
    }

    .topbar {
      max-width: 1240px;
      margin: 0 auto;
      padding: 20px 22px;
      border-radius: 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 18px;
      position: sticky;
      top: 14px;
      z-index: 20;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .brand-mark {
      width: 48px;
      height: 48px;
      border-radius: 16px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, #201510 0%, #d26b1c 100%);
      color: #fff7ef;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.18);
    }

    .eyebrow {
      margin: 0 0 4px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: #9f6b3d;
      font-weight: 800;
    }

    .brand h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.05;
    }

    .topbar-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .content {
      max-width: 1240px;
      margin: 0 auto;
      padding: 24px 20px 40px;
    }

    .btn-primary,
    .btn-secondary,
    .btn-ghost,
    .action-card {
      border: none;
      font: inherit;
      cursor: pointer;
      transition: transform 0.15s ease, opacity 0.15s ease, background-color 0.15s ease;
    }

    .btn-primary,
    .btn-secondary,
    .btn-ghost {
      border-radius: 999px;
      padding: 12px 18px;
      font-weight: 700;
    }

    .btn-primary {
      background: #171411;
      color: #ffffff;
    }

    .btn-secondary {
      background: #f4ebdf;
      color: #4d3d2f;
    }

    .btn-ghost {
      background: #fff7ef;
      color: #3e2e22;
      border: 1px solid #ead7c2;
    }

    .btn-primary:hover,
    .btn-secondary:hover,
    .btn-ghost:hover,
    .action-card:hover {
      transform: translateY(-1px);
    }

    .hero-card {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(290px, 0.75fr);
      gap: 18px;
      border-radius: 32px;
      overflow: hidden;
      margin-bottom: 18px;
    }

    .hero-copy,
    .hero-side {
      padding: 30px;
    }

    .hero-side {
      background: linear-gradient(180deg, rgba(255, 248, 238, 0.9) 0%, rgba(255, 255, 255, 0.98) 100%);
      display: flex;
      align-items: stretch;
    }

    .hero-copy h2 {
      margin: 0 0 12px;
      font-size: 42px;
      line-height: 0.98;
    }

    .hero-text {
      margin: 0;
      color: #6a594b;
      line-height: 1.6;
      max-width: 760px;
    }

    .hero-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 22px;
    }

    .meta-chip {
      min-width: 170px;
      padding: 14px 16px;
      border-radius: 18px;
      background: #fff8ef;
      border: 1px solid #efdfcd;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .meta-chip span {
      color: #8d6b4f;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .meta-chip strong {
      font-size: 15px;
      color: #231912;
      line-height: 1.35;
    }

    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 24px;
    }

    .health-card {
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.68);
      border: 1px solid #efdfcd;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      width: 100%;
    }

    .health-label {
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: #9d6d42;
    }

    .health-card strong {
      font-size: 24px;
      line-height: 1.1;
    }

    .health-card p {
      margin: 0;
      color: #68584b;
      line-height: 1.6;
    }

    .progress-track {
      height: 12px;
      border-radius: 999px;
      background: #ead7bf;
      overflow: hidden;
      margin-top: 6px;
    }

    .progress-fill {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #c65a16 0%, #e1922f 100%);
    }

    .stats-strip {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }

    .stat-card {
      border-radius: 24px;
      padding: 20px;
      background: rgba(255,255,255,0.86);
      border: 1px solid #eadcca;
      box-shadow: 0 12px 34px rgba(64, 37, 18, 0.06);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .stat-card-strong {
      background: linear-gradient(145deg, #1c1612 0%, #64411f 100%);
      color: #fff8f1;
    }

    .stat-card span {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-weight: 800;
      color: #9a6b40;
    }

    .stat-card-strong span,
    .stat-card-strong p,
    .stat-card-strong strong {
      color: inherit;
    }

    .stat-card strong {
      font-size: 28px;
      line-height: 1.05;
      color: #261c15;
    }

    .stat-card p {
      margin: 0;
      color: #6d5c4d;
      line-height: 1.5;
      font-size: 13px;
    }

    .dashboard-grid {
      display: grid;
      grid-template-columns: 1.1fr 1fr;
      gap: 18px;
      align-items: start;
    }

    .panel {
      border-radius: 28px;
      padding: 24px;
    }

    .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 18px;
    }

    .panel-head h3 {
      margin: 4px 0 0;
      font-size: 24px;
    }

    .panel-head p:last-child {
      max-width: 320px;
      margin: 0;
      color: #6c5b4d;
      line-height: 1.6;
      font-size: 14px;
    }

    .panel-kicker {
      margin: 0;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: #a3632b;
    }

    .detail-panel {
      grid-column: 1 / -1;
    }

    .analytics-panel {
      grid-column: 1 / -1;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }

    .info-item {
      padding: 16px;
      border-radius: 18px;
      background: #fff8ef;
      border: 1px solid #efdfcd;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .info-item span {
      color: #8d6b4f;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .info-item strong {
      font-size: 14px;
      line-height: 1.45;
      color: #271d15;
    }

    .tag-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .tag {
      padding: 8px 12px;
      border-radius: 999px;
      background: #f5ecdf;
      color: #7b582f;
      font-size: 12px;
      font-weight: 700;
    }

    .action-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }

    .action-card {
      text-align: left;
      padding: 18px;
      border-radius: 22px;
      background: #fffaf4;
      border: 1px solid #efdfcd;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .action-badge {
      align-self: flex-start;
      padding: 7px 10px;
      border-radius: 999px;
      background: #f4ebdf;
      color: #8a5b31;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }

    .action-card strong {
      font-size: 20px;
      line-height: 1.1;
      color: #211811;
    }

    .action-card p {
      margin: 0;
      color: #6f5d4e;
      line-height: 1.6;
      font-size: 14px;
    }

    .mini-metrics {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }

    .analytics-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .analytics-card {
      padding: 18px;
      border-radius: 20px;
      background: #fff8ef;
      border: 1px solid #efdfcd;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .analytics-card-strong {
      background: linear-gradient(145deg, #1c1612 0%, #64411f 100%);
      color: #fff8f1;
      border-color: transparent;
    }

    .analytics-card span {
      color: #8d6b4f;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .analytics-card-strong span,
    .analytics-card-strong strong,
    .analytics-card-strong p {
      color: inherit;
    }

    .analytics-card strong {
      font-size: 26px;
      line-height: 1.05;
      color: #241a13;
    }

    .analytics-card p {
      margin: 0;
      color: #6d5c4d;
      line-height: 1.55;
      font-size: 13px;
    }

    .insight-strip {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(280px, 0.9fr);
      gap: 14px;
    }

    .insight-callout,
    .insight-list {
      border-radius: 20px;
      background: #fffaf4;
      border: 1px solid #efdfcd;
      padding: 18px;
    }

    .insight-label {
      display: inline-block;
      margin-bottom: 8px;
      color: #9a6b40;
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }

    .insight-callout strong {
      display: block;
      font-size: 22px;
      line-height: 1.1;
      color: #241a13;
      margin-bottom: 8px;
    }

    .insight-callout p {
      margin: 0;
      color: #6d5c4d;
      line-height: 1.6;
    }

    .insight-list {
      list-style: none;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .insight-list li {
      color: #6d5c4d;
      line-height: 1.55;
      padding-left: 18px;
      position: relative;
    }

    .insight-list li::before {
      content: '';
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #d26b1c;
      position: absolute;
      left: 0;
      top: 8px;
    }

    .mini-metric {
      padding: 16px;
      border-radius: 18px;
      background: #fff8ef;
      border: 1px solid #efdfcd;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .mini-metric span {
      color: #8d6b4f;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .mini-metric strong {
      font-size: 22px;
      line-height: 1.1;
      color: #251b14;
    }

    .notification-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .notification-list li {
      padding: 14px 16px;
      border-radius: 16px;
      background: #fffaf4;
      border: 1px solid #efdfcd;
      color: #7a6653;
      font-weight: 700;
    }

    .notification-list li.enabled {
      background: #eef8f0;
      border-color: #cfe6d4;
      color: #29643a;
    }

    .notification-editor {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .notification-toggle {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 14px 16px;
      border-radius: 18px;
      background: #fffaf4;
      border: 1px solid #efdfcd;
      cursor: pointer;
      transition: transform 0.15s ease, background-color 0.15s ease, border-color 0.15s ease;
    }

    .notification-toggle.enabled {
      background: #eef8f0;
      border-color: #cfe6d4;
    }

    .notification-toggle:hover {
      transform: translateY(-1px);
    }

    .notification-toggle input {
      margin-top: 4px;
    }

    .notification-toggle div {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .notification-toggle strong {
      font-size: 15px;
      line-height: 1.2;
      color: #231912;
    }

    .notification-toggle span {
      color: #6d5c4d;
      font-size: 13px;
      line-height: 1.5;
    }

    .notification-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 14px;
      flex-wrap: wrap;
    }

    .helper-line,
    .message {
      margin: 12px 0 0;
      line-height: 1.5;
      font-size: 13px;
    }

    .helper-line {
      color: #7b6755;
    }

    .message.success {
      color: #1e7b41;
    }

    .message.error {
      color: #b3261e;
    }

    .empty-copy,
    .error-banner {
      margin: 0;
      color: #6a5a4c;
      line-height: 1.6;
    }

    .error-banner {
      margin-top: 16px;
      padding: 14px 16px;
      border-radius: 18px;
      background: #fff4f1;
      border: 1px solid #efd4cd;
      color: #a03a2d;
    }

    .loading-state {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 24px;
    }

    .loading-card {
      max-width: 520px;
      border-radius: 28px;
      padding: 28px;
      text-align: center;
    }

    .loading-card h2 {
      margin: 10px 0 12px;
      font-size: 30px;
      line-height: 1.1;
    }

    .loading-card p:last-child {
      margin: 0;
      color: #6c5b4d;
      line-height: 1.6;
    }

    @media (max-width: 1120px) {
      .hero-card,
      .dashboard-grid,
      .stats-strip {
        grid-template-columns: 1fr 1fr;
      }

      .hero-card {
        grid-template-columns: 1fr;
      }

      .detail-panel {
        grid-column: auto;
      }

      .info-grid {
        grid-template-columns: 1fr 1fr;
      }

      .analytics-grid,
      .insight-strip {
        grid-template-columns: 1fr 1fr;
      }
    }

    @media (max-width: 820px) {
      .topbar {
        margin: 0 14px;
        padding: 18px;
        border-radius: 24px;
        flex-direction: column;
        align-items: flex-start;
      }

      .content {
        padding: 18px 14px 32px;
      }

      .stats-strip,
      .dashboard-grid,
      .info-grid,
      .analytics-grid,
      .insight-strip {
        grid-template-columns: 1fr;
      }

      .hero-copy,
      .hero-side,
      .panel,
      .loading-card {
        padding: 20px;
      }

      .hero-copy h2 {
        font-size: 32px;
      }

      .panel-head {
        flex-direction: column;
      }

      .panel-head p:last-child {
        max-width: none;
      }

      .hero-actions,
      .topbar-actions {
        width: 100%;
      }

      .hero-actions .btn-primary,
      .hero-actions .btn-secondary,
      .topbar-actions .btn-ghost {
        width: 100%;
      }
    }
  `]
})
export class WorkshopDashboardComponent implements OnInit {
  taller: Taller | null = null;
  estadisticas: WorkshopStats | null = null;
  mostrarPerfil = false;
  cargando = true;
  errorCarga = '';
  savingNotifications = false;
  notificationSuccessMessage = '';
  notificationErrorMessage = '';
  notificationDraft = {
    notificaciones_nuevas_asignaciones: false,
    notificaciones_push: false,
    notificaciones_recordatorios: false,
    notificaciones_pagos: false,
    reportes_semanales: false
  };

  constructor(
    private authService: AuthService,
    private workshopService: WorkshopProfileService,
    private router: Router,
    private cdr: ChangeDetectorRef 
  ) {}

  ngOnInit() {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }

    this.cargarDatos();
  }

  cargarDatos() {
    console.log('Iniciando carga de datos del dashboard...');
    this.cargando = true;
    this.errorCarga = '';
    this.estadisticas = null;
    this.cdr.detectChanges();

    this.workshopService.getMyWorkshop().pipe(timeout(12000)).subscribe({
      next: (taller) => {
        console.log('Taller cargado:', taller);
        this.taller = taller;
        this.resetNotificationDraft();
        this.cdr.detectChanges();
        
        this.workshopService.getWorkshopStats().pipe(timeout(12000)).subscribe({
          next: (stats) => {
            console.log('Estadísticas cargadas:', stats);
            this.estadisticas = stats;
            this.cargando = false;
            this.cdr.detectChanges();
          },
          error: (error) => {
            console.error('Error al cargar estadísticas:', error);
            this.estadisticas = null;
            this.cargando = false;
            this.cdr.detectChanges();
          }
        });
      },
      error: (error) => {
        console.error('Error al cargar taller:', error);
        if (error.status === 404) {
          console.log('Taller no encontrado, redirigiendo a crear-taller');
          this.cargando = false;
          this.cdr.detectChanges();
          this.router.navigate(['/crear-taller'], { replaceUrl: true });
          return;
        }

        this.errorCarga = 'No se pudo cargar la información del taller.';
        this.cargando = false;
        this.cdr.detectChanges();
      }
    });
  }

  get specialtyTags(): string[] {
    if (!this.taller?.especialidades) {
      return [];
    }

    return this.taller.especialidades
      .map((item) => item.nombre.trim())
      .filter(Boolean)
      .slice(0, 8);
  }

  get profileScore(): number {
    if (!this.taller) {
      return 0;
    }

    const checks = [
      !!this.taller.nombre_comercial,
      !!this.taller.direccion,
      !!this.taller.telefono,
      !!this.taller.horario_atencion,
      this.specialtyTags.length > 0,
      !!this.taller.descripcion,
      !!this.taller.email_contacto,
      !!this.taller.latitud && !!this.taller.longitud
    ];

    const completed = checks.filter(Boolean).length;
    return Math.round((completed / checks.length) * 100);
  }

  get workshopHealthLabel(): string {
    if (!this.estadisticas) {
      return 'Inicial';
    }

    if (this.estadisticas.tecnicos.tecnicos_disponibles > 0) {
      return 'Disponible';
    }

    return 'Sin técnicos libres';
  }

  get workshopHealthTitle(): string {
    if (this.profileScore >= 90) {
      return 'Perfil listo para operar';
    }

    if (this.profileScore >= 60) {
      return 'Buen nivel de configuración';
    }

    return 'Perfil todavía básico';
  }

  get workshopHealthDescription(): string {
    if (!this.estadisticas) {
      return 'El perfil ya está activo, pero todavía estamos esperando o calculando parte de las métricas operativas.';
    }

    return 'Combina la completitud del perfil con una lectura rápida de capacidad y disponibilidad del taller.';
  }

  get responseTimeLabel(): string {
    if (!this.estadisticas?.tiempo_respuesta_promedio && !this.taller?.tiempo_respuesta_promedio) {
      return 'Aún sin datos';
    }

    return `${this.estadisticas?.tiempo_respuesta_promedio ?? this.taller?.tiempo_respuesta_promedio} min`;
  }

  get technicianAvailabilityPercent(): number {
    if (!this.estadisticas?.tecnicos.total_tecnicos) {
      return 0;
    }

    return Math.round(
      (this.estadisticas.tecnicos.tecnicos_disponibles / this.estadisticas.tecnicos.total_tecnicos) * 100
    );
  }

  get averageCommissionPerService(): number {
    if (!this.estadisticas?.servicios.total_completados) {
      return 0;
    }

    return this.estadisticas.servicios.comisiones_totales_pagadas / this.estadisticas.servicios.total_completados;
  }

  get netAverageIncome(): number {
    if (!this.estadisticas) {
      return 0;
    }

    return this.estadisticas.servicios.ingreso_promedio_por_servicio - this.averageCommissionPerService;
  }

  get operationalStageLabel(): string {
    const completed = this.estadisticas?.servicios.total_completados ?? 0;

    if (completed >= 25) {
      return 'Consolidado';
    }

    if (completed >= 8) {
      return 'En crecimiento';
    }

    return 'Inicial';
  }

  get operationalStageDescription(): string {
    const completed = this.estadisticas?.servicios.total_completados ?? 0;

    if (completed >= 25) {
      return 'El taller ya tiene suficiente volumen como para medir rendimiento con mayor confianza.';
    }

    if (completed >= 8) {
      return 'Ya existe una base operativa útil para afinar tiempos, equipo y rentabilidad.';
    }

    return 'Todavía estás construyendo historial; conviene priorizar capacidad y velocidad de respuesta.';
  }

  get mainInsightTitle(): string {
    if (!this.estadisticas) {
      return 'Aún no hay suficientes métricas calculadas';
    }

    if (this.technicianAvailabilityPercent < 40) {
      return 'La disponibilidad técnica es el principal cuello de botella';
    }

    if ((this.estadisticas.servicios.total_completados ?? 0) < 5) {
      return 'La prioridad actual es construir historial operativo';
    }

    return 'El taller ya tiene una base útil para optimizar operación y rentabilidad';
  }

  get mainInsightDescription(): string {
    if (!this.estadisticas) {
      return 'A medida que se resuelvan servicios y se carguen más técnicos, el panel mostrará una lectura operativa más rica.';
    }

    if (this.technicianAvailabilityPercent < 40) {
      return 'Conviene revisar la carga de trabajo del equipo o aumentar técnicos disponibles para responder mejor a nuevas asignaciones.';
    }

    if (this.estadisticas.servicios.total_completados < 5) {
      return 'Todavía hay poco historial; enfócate en cerrar servicios y capturar datos consistentes para fortalecer el análisis.';
    }

    return 'Las métricas actuales ya permiten tomar decisiones más finas sobre capacidad, comisiones y tiempos de atención.';
  }

  get completionInsight(): string {
    const completed = this.estadisticas?.servicios.total_completados ?? 0;
    return completed > 0
      ? `El sistema registra ${completed} servicio(s) completado(s) para este taller.`
      : 'Todavía no hay servicios completados registrados para este taller.';
  }

  get availabilityInsight(): string {
    return this.estadisticas?.tecnicos.total_tecnicos
      ? `La disponibilidad del equipo está en ${this.technicianAvailabilityPercent}%, con ${this.estadisticas.tecnicos.tecnicos_disponibles} técnico(s) libre(s).`
      : 'Aún no hay técnicos registrados; eso limita la capacidad operativa visible del taller.';
  }

  get financeInsight(): string {
    return this.estadisticas && this.estadisticas.servicios.total_completados > 0
      ? `El ingreso neto medio estimado por servicio es de $${Math.round(this.netAverageIncome)}.`
      : 'Las métricas financieras se volverán más útiles cuando existan servicios resueltos con cobros registrados.';
  }

  get notificationsDirty(): boolean {
    if (!this.taller) {
      return false;
    }

    return this.notificationDraft.notificaciones_nuevas_asignaciones !== this.taller.notificaciones_nuevas_asignaciones
      || this.notificationDraft.notificaciones_push !== this.taller.notificaciones_push
      || this.notificationDraft.notificaciones_recordatorios !== this.taller.notificaciones_recordatorios
      || this.notificationDraft.notificaciones_pagos !== this.taller.notificaciones_pagos
      || this.notificationDraft.reportes_semanales !== this.taller.reportes_semanales;
  }

  editarPerfil() {
    this.router.navigate(['/taller/perfil']);
  }

  irATecnicos() {
    this.router.navigate(['/taller/tecnicos']);
  }

  irASolicitudes() {
    this.router.navigate(['/taller/solicitudes']);
  }

  resetNotificationDraft() {
    if (!this.taller) {
      return;
    }

    this.notificationDraft = {
      notificaciones_nuevas_asignaciones: this.taller.notificaciones_nuevas_asignaciones,
      notificaciones_push: this.taller.notificaciones_push,
      notificaciones_recordatorios: this.taller.notificaciones_recordatorios,
      notificaciones_pagos: this.taller.notificaciones_pagos,
      reportes_semanales: this.taller.reportes_semanales
    };
    this.notificationSuccessMessage = '';
    this.notificationErrorMessage = '';
  }

  saveNotificationSettings() {
    if (!this.taller || !this.notificationsDirty) {
      return;
    }

    this.savingNotifications = true;
    this.notificationSuccessMessage = '';
    this.notificationErrorMessage = '';

    this.workshopService.updateMyWorkshop(this.notificationDraft).subscribe({
      next: (taller) => {
        this.taller = taller;
        this.resetNotificationDraft();
        this.notificationSuccessMessage = 'Preferencias guardadas correctamente.';
        this.savingNotifications = false;
      },
      error: (error) => {
        this.notificationErrorMessage = error?.error?.detail || 'No se pudieron guardar las preferencias.';
        this.savingNotifications = false;
      }
    });
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
