import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize, timeout } from 'rxjs';

import { AuthService } from '../core/auth.service';
import { Solicitud, SolicitudService } from '../core/incident.service';
import { Vehicle, VehicleService } from '../core/vehicle.service';

@Component({
  selector: 'app-client-portal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="portal-shell">
      <div class="ambient ambient-a" aria-hidden="true"></div>
      <div class="ambient ambient-b" aria-hidden="true"></div>

      <header class="topbar">
        <div class="brand-block">
          <p class="eyebrow">Panel Cliente</p>
          <h1>Centro personal de asistencia mecanica.</h1>
          <p class="lede">
            Administra tus datos, registra vehiculos y sigue cada solicitud desde un mismo lugar con una interfaz mucho mas clara.
          </p>
        </div>

        <div class="topbar-actions">
          <div class="identity-chip">
            <span class="identity-kicker">Cuenta activa</span>
            <strong>{{ displayName }}</strong>
          </div>
          <button class="btn-ghost" (click)="logout()">Cerrar sesion</button>
        </div>
      </header>

      <section class="hero-grid">
        <article class="hero-card hero-card-main">
          <div class="hero-copy">
            <p class="eyebrow eyebrow-light">Cliente conectado</p>
            <h2>{{ displayName }}</h2>
            <p>
              Tu cuenta ya puede operar entre web y mobile. Desde aqui puedes dejar listo tu perfil, cargar los vehiculos y reportar una emergencia con seguimiento en tiempo real.
            </p>
            <div class="hero-tags">
              <span class="hero-tag">Perfil {{ profileCompletion }}% completo</span>
              <span class="hero-tag">{{ vehicles.length }} vehiculo(s) listos</span>
              <span class="hero-tag">{{ activeReportsCount }} caso(s) activo(s)</span>
            </div>
          </div>

          <div class="hero-side">
            <div class="metric-stack">
              <div class="metric-card metric-card-strong">
                <span>Solicitudes</span>
                <strong>{{ reports.length }}</strong>
                <p>Total acumulado dentro del sistema.</p>
              </div>
              <div class="metric-card">
                <span>Activas</span>
                <strong>{{ activeReportsCount }}</strong>
                <p>Pendientes, asignadas o en progreso.</p>
              </div>
              <div class="metric-card">
                <span>Pagadas</span>
                <strong>{{ paidReportsCount }}</strong>
                <p>Servicios ya marcados como pagados.</p>
              </div>
            </div>
          </div>
        </article>

        <article class="hero-card hero-card-note">
          <p class="eyebrow">Ruta de uso</p>
          <h3>Flujo recomendado</h3>
          <ol class="guide-list">
            <li>Actualiza tu perfil.</li>
            <li>Registra al menos un vehiculo.</li>
            <li>Crea la solicitud con ubicacion.</li>
            <li>Monitorea taller, tecnico, ETA y pago.</li>
          </ol>
        </article>
      </section>

      <main class="dashboard-grid">
        <section class="panel panel-profile">
          <div class="panel-head">
            <div>
              <p class="section-kicker">Cuenta</p>
              <h2>Mi perfil</h2>
              <p>Datos basicos del cliente para que web y mobile trabajen con la misma identidad.</p>
            </div>
            <div class="status-chip status-neutral">{{ profileCompletion }}% completo</div>
          </div>

          <form [formGroup]="profileForm" (ngSubmit)="saveProfile()" class="form-layout">
            <label class="field field-wide">
              <span>Nombre completo</span>
              <input type="text" formControlName="full_name" placeholder="Juan Perez" />
            </label>
            <label class="field">
              <span>Usuario</span>
              <input type="text" formControlName="username" placeholder="juanperez" />
            </label>
            <label class="field">
              <span>Correo</span>
              <input type="email" formControlName="email" placeholder="juan@mail.com" />
            </label>

            <div class="panel-actions">
              <button class="btn-primary" type="submit" [disabled]="profileForm.invalid || savingProfile">
                {{ savingProfile ? 'Guardando...' : 'Guardar perfil' }}
              </button>
            </div>
          </form>

          <p class="message success" *ngIf="profileMessage">{{ profileMessage }}</p>
          <p class="message error" *ngIf="profileError">{{ profileError }}</p>
        </section>

        <section class="panel panel-request">
          <div class="panel-head">
            <div>
              <p class="section-kicker">Emergencias</p>
              <h2>Reportar incidente</h2>
              <p>Genera una nueva solicitud con el vehiculo y la ubicacion exacta del problema.</p>
            </div>
            <div class="status-chip status-alert">{{ reports.length }} solicitud(es)</div>
          </div>

          <form [formGroup]="requestForm" (ngSubmit)="createRequest()" class="form-layout">
            <label class="field field-wide">
              <span>Vehiculo</span>
              <select formControlName="vehiculo_id">
                <option [ngValue]="null">Selecciona un vehiculo</option>
                <option *ngFor="let vehicle of vehicles" [ngValue]="vehicle.id">
                  {{ vehicle.placa }} - {{ vehicle.marca }} {{ vehicle.modelo }}
                </option>
              </select>
            </label>

            <label class="field field-wide">
              <span>Descripcion del incidente</span>
              <textarea formControlName="descripcion" rows="5" placeholder="Describe la falla, los sintomas y cualquier contexto importante."></textarea>
            </label>

            <label class="field">
              <span>Latitud</span>
              <input type="number" step="any" formControlName="latitud" placeholder="-16.500" />
            </label>
            <label class="field">
              <span>Longitud</span>
              <input type="number" step="any" formControlName="longitud" placeholder="-68.150" />
            </label>

            <div class="panel-actions">
              <button class="btn-primary" type="submit" [disabled]="requestForm.invalid || savingRequest || !vehicles.length">
                {{ savingRequest ? 'Enviando...' : 'Crear solicitud' }}
              </button>
            </div>
          </form>

          <p class="message success" *ngIf="requestMessage">{{ requestMessage }}</p>
          <p class="message error" *ngIf="requestError">{{ requestError }}</p>
        </section>

        <section class="panel panel-vehicles">
          <div class="panel-head">
            <div>
              <p class="section-kicker">Flota personal</p>
              <h2>Mis vehiculos</h2>
              <p>Registra y edita los vehiculos que quieres usar al momento de reportar una emergencia.</p>
            </div>
            <div class="status-chip status-soft">{{ vehicles.length }} registrado(s)</div>
          </div>

          <form [formGroup]="vehicleForm" (ngSubmit)="saveVehicle()" class="form-layout">
            <label class="field">
              <span>Placa</span>
              <input type="text" formControlName="placa" placeholder="1234ABC" />
            </label>
            <label class="field">
              <span>Marca</span>
              <input type="text" formControlName="marca" placeholder="Toyota" />
            </label>
            <label class="field">
              <span>Modelo</span>
              <input type="text" formControlName="modelo" placeholder="Corolla" />
            </label>
            <label class="field">
              <span>Color</span>
              <input type="text" formControlName="color" placeholder="Blanco" />
            </label>

            <div class="panel-actions">
              <button class="btn-primary" type="submit" [disabled]="vehicleForm.invalid || savingVehicle">
                {{ savingVehicle ? 'Guardando...' : (editingVehicleId ? 'Actualizar vehiculo' : 'Registrar vehiculo') }}
              </button>
              <button class="btn-secondary" type="button" *ngIf="editingVehicleId" (click)="cancelVehicleEdit()">
                Cancelar edicion
              </button>
            </div>
          </form>

          <p class="message success" *ngIf="vehicleMessage">{{ vehicleMessage }}</p>
          <p class="message error" *ngIf="vehicleError">{{ vehicleError }}</p>

          <div class="vehicle-grid" *ngIf="vehicles.length; else emptyVehicleState">
            <article class="vehicle-card" *ngFor="let vehicle of vehicles">
              <div class="vehicle-plate">{{ vehicle.placa }}</div>
              <strong>{{ vehicle.marca }} {{ vehicle.modelo }}</strong>
              <p>{{ vehicle.color || 'Color no definido' }}</p>
              <button class="btn-mini" type="button" (click)="startVehicleEdit(vehicle)">Editar</button>
            </article>
          </div>

          <ng-template #emptyVehicleState>
            <div class="empty-state">
              <strong>Aun no registraste vehiculos.</strong>
              <p>Empieza cargando el auto principal para usarlo en las solicitudes.</p>
            </div>
          </ng-template>
        </section>

        <section class="panel panel-reports">
          <div class="panel-head">
            <div>
              <p class="section-kicker">Seguimiento</p>
              <h2>Mis solicitudes</h2>
              <p>Consulta estado, taller asignado, tecnico, tiempo estimado de llegada y estado de pago.</p>
            </div>
            <button class="btn-secondary" type="button" (click)="loadReports()">Actualizar</button>
          </div>

          <div class="report-list" *ngIf="reports.length; else emptyReportState">
            <article class="report-card" *ngFor="let report of reports">
              <div class="report-top">
                <div class="report-heading">
                  <span class="report-id">Caso #{{ report.id }}</span>
                  <h3>{{ report.vehiculo_placa || 'Vehiculo sin referencia' }}</h3>
                  <p>{{ report.descripcion }}</p>
                </div>
                <span class="status-chip" [ngClass]="report.estado">{{ labelForStatus(report.estado) }}</span>
              </div>

              <div class="report-metrics">
                <div class="report-metric">
                  <span>Taller</span>
                  <strong>{{ report.taller_nombre || 'Pendiente de asignacion' }}</strong>
                </div>
                <div class="report-metric">
                  <span>Tecnico</span>
                  <strong>{{ technicianLabel(report) }}</strong>
                </div>
                <div class="report-metric">
                  <span>ETA</span>
                  <strong>{{ etaLabel(report) }}</strong>
                </div>
                <div class="report-metric">
                  <span>Pago</span>
                  <strong>{{ paymentLabel(report) }}</strong>
                </div>
                <div class="report-metric">
                  <span>Monto</span>
                  <strong>{{ amountLabel(report) }}</strong>
                </div>
                <div class="report-metric">
                  <span>Analisis</span>
                  <strong>{{ report.clasificacion_ia || 'General' }}</strong>
                </div>
              </div>

              <div class="panel-actions">
                <button
                  class="btn-secondary"
                  type="button"
                  *ngIf="canCancel(report)"
                  (click)="cancelReport(report)"
                >
                  Cancelar solicitud
                </button>
                <button
                  class="btn-primary"
                  type="button"
                  *ngIf="canPay(report)"
                  (click)="payReport(report)"
                >
                  Pagar servicio
                </button>
              </div>
            </article>
          </div>

          <ng-template #emptyReportState>
            <div class="empty-state empty-state-large">
              <strong>Todavia no hay solicitudes registradas.</strong>
              <p>Cuando reportes una emergencia, aqui aparecera el detalle completo del seguimiento.</p>
            </div>
          </ng-template>
        </section>
      </main>
    </div>
  `,
  styles: [`
    :host {
      --bg: #f6efe6;
      --panel: rgba(255, 251, 246, 0.86);
      --panel-strong: #1f1b18;
      --line: rgba(113, 85, 58, 0.16);
      --text: #1d1714;
      --muted: #685a4b;
      --accent: #bf5d24;
      --accent-soft: #f7dfc6;
      --highlight: #cfded3;
      display: block;
      min-height: 100vh;
      background:
        radial-gradient(circle at 0% 0%, rgba(207, 152, 91, 0.22), transparent 30%),
        radial-gradient(circle at 100% 20%, rgba(137, 170, 154, 0.18), transparent 24%),
        linear-gradient(180deg, #fbf6ef 0%, #f6efe6 45%, #f8f5f0 100%);
      color: var(--text);
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
    }

    .portal-shell {
      max-width: 1320px;
      margin: 0 auto;
      padding: 34px 24px 48px;
      position: relative;
    }

    .ambient {
      position: fixed;
      width: 340px;
      height: 340px;
      border-radius: 50%;
      filter: blur(70px);
      pointer-events: none;
      opacity: 0.45;
    }

    .ambient-a {
      top: 40px;
      right: -90px;
      background: rgba(220, 170, 112, 0.38);
    }

    .ambient-b {
      bottom: 40px;
      left: -120px;
      background: rgba(143, 180, 160, 0.22);
    }

    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 20px;
      margin-bottom: 22px;
    }

    .brand-block {
      max-width: 760px;
    }

    .eyebrow,
    .section-kicker,
    .identity-kicker {
      margin: 0 0 8px;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 11px;
      font-weight: 800;
      color: #9a6133;
    }

    .eyebrow-light {
      color: #f5c999;
    }

    h1,
    h2,
    h3 {
      font-family: Georgia, "Times New Roman", serif;
      letter-spacing: -0.03em;
    }

    h1 {
      margin: 0;
      font-size: clamp(2.7rem, 4.8vw, 4.5rem);
      line-height: 0.95;
      max-width: 860px;
    }

    .lede {
      margin: 14px 0 0;
      max-width: 700px;
      color: var(--muted);
      line-height: 1.7;
      font-size: 1rem;
    }

    .topbar-actions {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .identity-chip {
      min-width: 170px;
      padding: 14px 18px;
      border-radius: 22px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid var(--line);
      box-shadow: 0 14px 32px rgba(71, 48, 26, 0.08);
      backdrop-filter: blur(12px);
    }

    .identity-chip strong {
      display: block;
      font-size: 1rem;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
      gap: 18px;
      margin-bottom: 22px;
    }

    .hero-card {
      border-radius: 34px;
      border: 1px solid var(--line);
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(69, 44, 22, 0.08);
      backdrop-filter: blur(14px);
    }

    .hero-card-main {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.7fr);
      background:
        radial-gradient(circle at 0% 0%, rgba(255, 167, 82, 0.18), transparent 32%),
        linear-gradient(135deg, #1f1916 0%, #4a2f1d 58%, #b65a28 100%);
      color: #fff8ef;
    }

    .hero-copy,
    .hero-side {
      padding: 28px;
    }

    .hero-copy h2 {
      margin: 0 0 12px;
      font-size: clamp(2rem, 3vw, 3rem);
      line-height: 0.95;
    }

    .hero-copy p {
      margin: 0;
      max-width: 560px;
      line-height: 1.75;
      color: rgba(255, 244, 231, 0.88);
    }

    .hero-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 20px;
    }

    .hero-tag {
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid rgba(255, 255, 255, 0.16);
      background: rgba(255, 255, 255, 0.10);
      font-size: 13px;
      font-weight: 700;
    }

    .hero-side {
      background: linear-gradient(180deg, rgba(255, 250, 244, 0.16) 0%, rgba(255, 255, 255, 0.08) 100%);
      border-left: 1px solid rgba(255, 255, 255, 0.1);
    }

    .metric-stack {
      display: grid;
      gap: 12px;
      height: 100%;
    }

    .metric-card {
      padding: 18px;
      border-radius: 22px;
      background: rgba(255, 255, 255, 0.14);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }

    .metric-card-strong {
      background: rgba(255, 249, 241, 0.22);
    }

    .metric-card span {
      display: block;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-weight: 800;
      color: rgba(255, 227, 202, 0.76);
    }

    .metric-card strong {
      display: block;
      margin: 10px 0 6px;
      font-size: 2rem;
      line-height: 1;
    }

    .metric-card p {
      margin: 0;
      color: rgba(255, 242, 228, 0.78);
      line-height: 1.55;
      font-size: 13px;
    }

    .hero-card-note {
      padding: 24px;
      background: var(--panel);
    }

    .hero-card-note h3 {
      margin: 0 0 12px;
      font-size: 1.8rem;
    }

    .guide-list {
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
      line-height: 1.8;
    }

    .dashboard-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 18px;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 30px;
      padding: 26px;
      box-shadow: 0 18px 36px rgba(70, 47, 26, 0.07);
      backdrop-filter: blur(14px);
    }

    .panel-vehicles,
    .panel-reports {
      grid-column: 1 / -1;
    }

    .panel-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 18px;
    }

    .panel-head h2 {
      margin: 0 0 8px;
      font-size: 2rem;
      line-height: 0.98;
    }

    .panel-head p {
      margin: 0;
      color: var(--muted);
      max-width: 540px;
      line-height: 1.7;
    }

    .status-chip {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 10px 14px;
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }

    .status-neutral {
      background: #ede6dd;
      color: #6e5238;
    }

    .status-alert {
      background: #f8dfc9;
      color: #a45321;
    }

    .status-soft {
      background: #e7efe9;
      color: #35624f;
    }

    .form-layout {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 7px;
    }

    .field-wide,
    .panel-actions,
    .message {
      grid-column: 1 / -1;
    }

    .field span {
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #5e4a39;
    }

    input,
    select,
    textarea {
      width: 100%;
      box-sizing: border-box;
      border: 1px solid rgba(131, 97, 62, 0.18);
      border-radius: 18px;
      padding: 15px 16px;
      background: rgba(255, 255, 255, 0.76);
      color: var(--text);
      font: inherit;
      transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
    }

    input:focus,
    select:focus,
    textarea:focus {
      outline: none;
      border-color: rgba(191, 93, 36, 0.66);
      box-shadow: 0 0 0 4px rgba(191, 93, 36, 0.10);
      transform: translateY(-1px);
    }

    textarea {
      resize: vertical;
      min-height: 130px;
    }

    .panel-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 8px;
    }

    .btn-primary,
    .btn-secondary,
    .btn-ghost,
    .btn-mini {
      border: none;
      cursor: pointer;
      font: inherit;
      font-weight: 800;
      transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
    }

    .btn-primary:hover,
    .btn-secondary:hover,
    .btn-ghost:hover,
    .btn-mini:hover {
      transform: translateY(-1px);
    }

    .btn-primary {
      padding: 13px 20px;
      border-radius: 999px;
      background: linear-gradient(135deg, #241c17 0%, #4e321f 55%, #bf5d24 100%);
      color: #fff9f0;
      box-shadow: 0 14px 24px rgba(136, 78, 37, 0.22);
    }

    .btn-primary:disabled {
      opacity: 0.55;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }

    .btn-secondary,
    .btn-ghost {
      padding: 13px 18px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.72);
      color: #2d231b;
      border: 1px solid var(--line);
    }

    .btn-mini {
      padding: 10px 14px;
      border-radius: 14px;
      background: #efe4d6;
      color: #5f452c;
      align-self: flex-start;
    }

    .message {
      margin: 2px 0 0;
      font-size: 13px;
      line-height: 1.5;
    }

    .message.success {
      color: #16714a;
    }

    .message.error {
      color: #b22d24;
    }

    .vehicle-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-top: 18px;
    }

    .vehicle-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 18px;
      border-radius: 24px;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.88) 0%, rgba(247, 239, 229, 0.82) 100%);
      border: 1px solid rgba(127, 92, 58, 0.12);
    }

    .vehicle-plate {
      display: inline-flex;
      align-self: flex-start;
      padding: 8px 11px;
      border-radius: 999px;
      background: #20262a;
      color: #f4f1eb;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.1em;
    }

    .vehicle-card strong {
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.35rem;
      line-height: 1.05;
    }

    .vehicle-card p {
      margin: 0;
      color: var(--muted);
    }

    .report-list {
      display: grid;
      gap: 14px;
      margin-top: 4px;
    }

    .report-card {
      padding: 22px;
      border-radius: 26px;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(250, 244, 236, 0.92) 100%);
      border: 1px solid rgba(127, 92, 58, 0.12);
    }

    .report-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 16px;
    }

    .report-id {
      display: inline-block;
      margin-bottom: 8px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: #9a6133;
    }

    .report-heading h3 {
      margin: 0 0 8px;
      font-size: 1.65rem;
      line-height: 0.98;
    }

    .report-heading p {
      margin: 0;
      max-width: 880px;
      color: var(--muted);
      line-height: 1.7;
    }

    .report-metrics {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }

    .report-metric {
      padding: 14px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(127, 92, 58, 0.10);
    }

    .report-metric span {
      display: block;
      margin-bottom: 6px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #8a6544;
    }

    .report-metric strong {
      font-size: 14px;
      line-height: 1.4;
      color: var(--text);
    }

    .pendiente {
      background: #fdf0ce;
      color: #8b5a00;
    }

    .asignada {
      background: #dbe8ff;
      color: #1f4fa6;
    }

    .en_progreso {
      background: #ece2ff;
      color: #5a2bb4;
    }

    .resuelta {
      background: #dff5e5;
      color: #15653f;
    }

    .cancelada {
      background: #fde3df;
      color: #a52d26;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 14px;
      padding: 24px;
      border-radius: 24px;
      border: 1px dashed rgba(121, 92, 61, 0.28);
      background: rgba(255, 252, 247, 0.74);
      color: var(--muted);
    }

    .empty-state strong {
      font-size: 1.05rem;
      color: var(--text);
    }

    .empty-state p {
      margin: 0;
      line-height: 1.6;
    }

    .empty-state-large {
      align-items: center;
      text-align: center;
      padding: 42px 24px;
    }

    @media (max-width: 1120px) {
      .hero-grid,
      .dashboard-grid,
      .hero-card-main {
        grid-template-columns: 1fr;
      }

      .report-metrics {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
    }

    @media (max-width: 820px) {
      .portal-shell {
        padding: 22px 14px 34px;
      }

      .topbar {
        flex-direction: column;
      }

      .topbar-actions {
        width: 100%;
        justify-content: flex-start;
      }

      .panel,
      .hero-copy,
      .hero-side,
      .hero-card-note {
        padding: 20px;
      }

      .form-layout,
      .report-metrics {
        grid-template-columns: 1fr;
      }

      .report-top,
      .panel-head {
        flex-direction: column;
      }

      .btn-primary,
      .btn-secondary,
      .btn-ghost {
        width: 100%;
        justify-content: center;
      }

      .panel-actions {
        flex-direction: column;
      }
    }
  `]
})
export class ClientPortalComponent implements OnInit {
  profileForm: FormGroup;
  vehicleForm: FormGroup;
  requestForm: FormGroup;
  vehicles: Vehicle[] = [];
  reports: Solicitud[] = [];
  editingVehicleId: number | null = null;

  savingProfile = false;
  savingVehicle = false;
  savingRequest = false;
  profileMessage = '';
  profileError = '';
  vehicleMessage = '';
  vehicleError = '';
  requestMessage = '';
  requestError = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private vehicleService: VehicleService,
    private solicitudService: SolicitudService,
    private router: Router
  ) {
    this.profileForm = this.fb.group({
      full_name: ['', Validators.required],
      username: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]]
    });

    this.vehicleForm = this.fb.group({
      placa: ['', Validators.required],
      marca: ['', Validators.required],
      modelo: ['', Validators.required],
      color: ['']
    });

    this.requestForm = this.fb.group({
      vehiculo_id: [null, Validators.required],
      descripcion: ['', [Validators.required, Validators.minLength(12)]],
      latitud: [-16.500, Validators.required],
      longitud: [-68.150, Validators.required]
    });
  }

  get displayName(): string {
    return this.authService.getCurrentUser()?.full_name || 'Cliente';
  }

  get profileCompletion(): number {
    const value = this.profileForm.getRawValue();
    const checks = [value.full_name, value.username, value.email];
    return Math.round((checks.filter(Boolean).length / checks.length) * 100);
  }

  get activeReportsCount(): number {
    return this.reports.filter((report) => report.estado !== 'cancelada' && report.estado !== 'resuelta').length;
  }

  get paidReportsCount(): number {
    return this.reports.filter((report) => report.estado_pago === 'pagado').length;
  }

  ngOnInit() {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }

    if (this.authService.isWorkshopLike()) {
      this.router.navigate([this.authService.getDefaultRouteForRole()]);
      return;
    }

    this.loadProfile();
    this.loadVehicles();
    this.loadReports();
  }

  loadProfile() {
    this.authService.getProfile().pipe(timeout(10000)).subscribe({
      next: (user) => this.profileForm.patchValue(user),
      error: () => this.profileError = 'No se pudo cargar tu perfil.'
    });
  }

  loadVehicles() {
    this.vehicleService.getVehicles().pipe(timeout(10000)).subscribe({
      next: (vehicles) => this.vehicles = vehicles,
      error: () => this.vehicleError = 'No se pudieron cargar tus vehiculos.'
    });
  }

  loadReports() {
    this.solicitudService.getMyReports().pipe(timeout(10000)).subscribe({
      next: (reports) => this.reports = reports.sort((a, b) => b.id - a.id),
      error: () => this.requestError = 'No se pudo cargar el seguimiento de solicitudes.'
    });
  }

  saveProfile() {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }

    this.profileError = '';
    this.profileMessage = '';
    this.savingProfile = true;

    this.authService.updateProfile(this.profileForm.getRawValue()).pipe(
      timeout(10000),
      finalize(() => this.savingProfile = false)
    ).subscribe({
      next: (user) => {
        this.profileForm.patchValue(user);
        this.profileMessage = 'Perfil actualizado correctamente.';
      },
      error: (error) => this.profileError = error?.error?.detail || 'No se pudo actualizar el perfil.'
    });
  }

  saveVehicle() {
    if (this.vehicleForm.invalid) {
      this.vehicleForm.markAllAsTouched();
      return;
    }

    this.vehicleError = '';
    this.vehicleMessage = '';
    this.savingVehicle = true;

    const request$ = this.editingVehicleId
      ? this.vehicleService.updateVehicle(this.editingVehicleId, this.vehicleForm.getRawValue())
      : this.vehicleService.createVehicle(this.vehicleForm.getRawValue());

    request$.pipe(
      timeout(10000),
      finalize(() => this.savingVehicle = false)
    ).subscribe({
      next: (vehicle) => {
        if (this.editingVehicleId) {
          this.vehicles = this.vehicles.map((item) => item.id === vehicle.id ? vehicle : item);
          this.vehicleMessage = 'Vehiculo actualizado correctamente.';
        } else {
          this.vehicles = [vehicle, ...this.vehicles];
          this.vehicleMessage = 'Vehiculo registrado correctamente.';
        }

        this.cancelVehicleEdit();
      },
      error: (error) => this.vehicleError = error?.error?.detail || 'No se pudo guardar el vehiculo.'
    });
  }

  startVehicleEdit(vehicle: Vehicle) {
    this.editingVehicleId = vehicle.id;
    this.vehicleForm.reset({
      placa: vehicle.placa,
      marca: vehicle.marca,
      modelo: vehicle.modelo,
      color: vehicle.color || ''
    });
  }

  cancelVehicleEdit() {
    this.editingVehicleId = null;
    this.vehicleForm.reset({ placa: '', marca: '', modelo: '', color: '' });
  }

  createRequest() {
    if (this.requestForm.invalid) {
      this.requestForm.markAllAsTouched();
      return;
    }

    this.requestError = '';
    this.requestMessage = '';
    this.savingRequest = true;

    this.solicitudService.createSolicitud({
      ...this.requestForm.getRawValue(),
      estado: 'pendiente'
    }).pipe(
      timeout(10000),
      finalize(() => this.savingRequest = false)
    ).subscribe({
      next: (report) => {
        this.reports = [report, ...this.reports];
        this.requestForm.patchValue({ descripcion: '', vehiculo_id: this.requestForm.value.vehiculo_id });
        this.requestMessage = `Solicitud #${report.id} creada correctamente.`;
      },
      error: (error) => this.requestError = error?.error?.detail || 'No se pudo crear la solicitud.'
    });
  }

  canCancel(report: Solicitud): boolean {
    return report.estado !== 'cancelada' && report.estado !== 'resuelta';
  }

  canPay(report: Solicitud): boolean {
    return report.estado !== 'cancelada' && report.estado_pago !== 'pagado' && !!report.precio_cobrado;
  }

  cancelReport(report: Solicitud) {
    this.solicitudService.cancelSolicitud(report.id).pipe(timeout(10000)).subscribe({
      next: (updated) => {
        this.reports = this.reports.map((item) => item.id === updated.id ? updated : item);
      },
      error: (error) => this.requestError = error?.error?.detail || 'No se pudo cancelar la solicitud.'
    });
  }

  payReport(report: Solicitud) {
    this.solicitudService.paySolicitud(report.id, report.precio_cobrado).pipe(timeout(10000)).subscribe({
      next: (updated) => {
        this.reports = this.reports.map((item) => item.id === updated.id ? updated : item);
      },
      error: (error) => this.requestError = error?.error?.detail || 'No se pudo registrar el pago.'
    });
  }

  etaLabel(report: Solicitud): string {
    if (report.estado === 'cancelada') {
      return 'Cancelada';
    }
    if (!report.tiempo_estimado_minutos && report.tiempo_estimado_minutos !== 0) {
      return 'Pendiente';
    }
    return report.tiempo_estimado_minutos === 0 ? 'Finalizada' : `${report.tiempo_estimado_minutos} min`;
  }

  amountLabel(report: Solicitud): string {
    return report.precio_cobrado ? `Bs ${report.precio_cobrado.toFixed(2)}` : 'Sin monto';
  }

  paymentLabel(report: Solicitud): string {
    return report.estado_pago === 'pagado' ? 'Pagado' : 'Pendiente';
  }

  technicianLabel(report: Solicitud): string {
    if (report.tecnico_nombre) {
      return report.tecnico_especialidad
        ? `${report.tecnico_nombre} - ${report.tecnico_especialidad}`
        : report.tecnico_nombre;
    }
    return 'Pendiente';
  }

  labelForStatus(status: string): string {
    const map: Record<string, string> = {
      pendiente: 'Pendiente',
      asignada: 'Asignada',
      en_progreso: 'En progreso',
      resuelta: 'Resuelta',
      cancelada: 'Cancelada'
    };
    return map[status] ?? status;
  }

  logout() {
    this.authService.logout();
  }
}
