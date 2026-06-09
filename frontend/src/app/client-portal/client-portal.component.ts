import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { Subscription, finalize, timeout } from 'rxjs';
import * as L from 'leaflet';

import { AuthService } from '../core/auth.service';
import { Cotizacion, CotizacionService } from '../core/cotizacion.service';
import { Solicitud, SolicitudService } from '../core/incident.service';
import { OfflineQueueService } from '../core/offline-queue.service';
import { RealtimeEvent, RealtimeService } from '../core/realtime.service';
import { Vehicle, VehiclePhotoPreview, VehicleService } from '../core/vehicle.service';
import { ClienteNavbarComponent } from './cliente-navbar.component';

@Component({
  selector: 'app-client-portal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, ClienteNavbarComponent],
  template: `
    <div class="portal-shell">
      <app-cliente-navbar></app-cliente-navbar>

      <section class="page-heading">
        <h1>Control de perfil, vehículos y solicitudes.</h1>
        <p class="lede">
          Mantén tu cuenta lista, registra vehículos con ayuda de IA y reporta emergencias marcando el punto exacto en el mapa.
        </p>
      </section>

      <section class="resumen-rapido">
        <p class="section-kicker">Resumen rapido</p>
        <div class="resumen-cards">
          <article class="resumen-card">
            <div class="resumen-icon resumen-icon-left">&#128663;</div>
            <div class="resumen-text">
              <strong>{{ vehicles.length }}</strong>
              <span>Vehículos</span>
            </div>
            <div class="resumen-icon resumen-icon-right">&#128663;</div>
          </article>
          <article class="resumen-card">
            <div class="resumen-icon resumen-icon-left">&#128221;</div>
            <div class="resumen-text">
              <strong>{{ reports.length }}</strong>
              <span>Solicitudes</span>
            </div>
            <div class="resumen-icon resumen-icon-right">&#128221;</div>
          </article>
          <article class="resumen-card">
            <div class="resumen-icon resumen-icon-left">&#128184;</div>
            <div class="resumen-text">
              <strong>{{ payableReports.length }}</strong>
              <span>Cobro listo</span>
            </div>
            <div class="resumen-icon resumen-icon-right">&#128184;</div>
          </article>
        </div>
      </section>

      <main class="dashboard-grid single-col">
        <section class="panel panel-dark report-panel">
          <div class="panel-head">
            <div>
              <p class="section-kicker section-kicker-light">Reportar accidente o falla</p>
            </div>
          </div>

          <form [formGroup]="reportForm" (ngSubmit)="saveReport()" class="report-form">
            <label class="field field-wide">
              <span>Vehiculo registrado</span>
              <select formControlName="vehiculo_id">
                <option [ngValue]="null">Selecciona un vehículo</option>
                <option *ngFor="let vehicle of vehicles" [ngValue]="vehicle.id">
                  {{ vehicle.placa }} - {{ vehicle.marca }} {{ vehicle.modelo }}
                </option>
              </select>
            </label>

            <div class="report-row">
              <label class="field field-wide">
                <span>Descripcion del incidente</span>
                <textarea
                  formControlName="descripcion"
                  rows="4"
                  placeholder="Ejemplo: choque leve, bateria descargada, llanta pinchada..."
                ></textarea>
              </label>
            </div>

            <div class="audio-record-box" style="margin-bottom: 16px; padding: 12px; background: #fff8ef; border: 1px dashed #d7b99f; border-radius: 12px;">
              <p style="margin-top: 0; color: #6d5c4d; font-weight: bold; margin-bottom: 8px;">Mensaje de voz (Opcional)</p>
              
              <div *ngIf="!audioBlob && !isRecording" style="display: flex; gap: 10px;">
                <button type="button" class="btn-primary" (click)="startRecording()" style="padding: 6px 12px; font-size: 0.9rem;">🎤 Grabar Audio</button>
              </div>
              
              <div *ngIf="isRecording" style="display: flex; gap: 10px; align-items: center;">
                <span style="color: #d32f2f; font-weight: bold; animation: pulse 1.5s infinite;">🔴 Grabando...</span>
                <button type="button" class="btn-secondary" (click)="stopRecording()" style="padding: 6px 12px; font-size: 0.9rem;">⏹️ Detener</button>
              </div>

              <div *ngIf="audioBlob && !isRecording" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                <audio [src]="audioUrl" controls style="max-width: 100%; height: 40px;"></audio>
                <button type="button" class="btn-secondary" (click)="clearRecording()" style="padding: 6px 12px; font-size: 0.9rem;">🗑️ Borrar</button>
              </div>
            </div>
            <div class="report-side-actions">
              <button class="btn-side btn-side-light" type="button" (click)="useCurrentLocation()">Usar ubicación actual</button>
              <button class="btn-side btn-side-map" type="button" (click)="openMapPicker()">
                {{ mapPickerOpen ? 'Mapa abierto' : 'Abrir mapa' }}
              </button>
              <button class="btn-side btn-side-outline" type="button" (click)="goRegistrarVehiculo()">Registrar vehículo</button>
            </div>

            <p class="location-summary">{{ locationSummary }}</p>

            <section class="inline-map-panel" *ngIf="mapPickerOpen">
              <div class="inline-map-copy">
                <div>
                  <p class="section-kicker section-kicker-light">Ubicación del incidente</p>
                  <h3>Fija el punto exacto</h3>
                  <p>Mueve el mapa hasta dejar el pin central donde necesitas la asistencia.</p>
                </div>
                <button class="btn-map-close" type="button" (click)="closeMapPicker()">Cerrar mapa</button>
              </div>

              <div class="map-frame">
                <div id="client-report-map"></div>
                <div class="center-pin" aria-hidden="true">
                  <span class="pin-head">📍</span>
                  <span class="pin-shadow"></span>
                </div>
              </div>

              <div class="inline-map-footer">
                <div class="modal-grid">
                  <div class="modal-item">
                    <span>Latitud</span>
                    <strong>{{ selectedLat?.toFixed(6) || 'Pendiente' }}</strong>
                  </div>
                  <div class="modal-item">
                    <span>Longitud</span>
                    <strong>{{ selectedLng?.toFixed(6) || 'Pendiente' }}</strong>
                  </div>
                </div>

                <div class="panel-actions">
                  <button class="btn-secondary btn-secondary-on-dark" type="button" (click)="useCurrentLocation()">Usar actual</button>
                  <button class="btn-primary" type="button" (click)="confirmMapLocation()">Confirmar pin</button>
                </div>
              </div>
            </section>

            <button
              class="btn-crear-solicitud"
              type="submit"
              [disabled]="reportForm.invalid || savingReport || !vehicles.length"
            >
              {{ savingReport ? 'Creando...' : 'Crear solicitud' }}
            </button>
          </form>

          <p class="message success" *ngIf="reportMessage">{{ reportMessage }}</p>
          <p class="message error" *ngIf="reportError">{{ reportError }}</p>
        </section>

        <section class="panel panel-cotizaciones" *ngIf="pendingReports.length">
          <div class="panel-head">
            <div>
              <p class="section-kicker">Cotizaciones</p>
              <h2>Elige el taller para tu servicio</h2>
              <p>Compara costo, tiempo de reparacion y llegada. Selecciona la oferta que prefieras.</p>
            </div>
            <button class="btn-secondary" type="button" (click)="reloadCotizaciones()">Actualizar</button>
          </div>

          <div class="report-list">
            <article class="report-card" *ngFor="let report of pendingReports">
              <div class="report-top">
                <div>
                  <span class="report-id">Solicitud #{{ report.id }}</span>
                  <h3>{{ report.descripcion }}</h3>
                </div>
                <span class="status-chip" [ngClass]="report.estado">{{ labelForStatus(report.estado) }}</span>
              </div>

              <p class="message" *ngIf="cotizacionesLoading[report.id]">Cargando cotizaciones...</p>
              <p class="message" *ngIf="!cotizacionesLoading[report.id] && !cotizacionesPorReporte[report.id]?.length">
                Aún no hay cotizaciones. Los talleres cercanos están revisando tu solicitud.
              </p>

              <div class="cotizacion-list" *ngIf="cotizacionesPorReporte[report.id]?.length">
                <div class="cotizacion-card" *ngFor="let cot of cotizacionesPorReporte[report.id]">
                  <div class="report-top">
                    <strong>{{ cot.taller_nombre || 'Taller' }}</strong>
                    <span class="status-chip" *ngIf="cot.taller_calificacion != null">
                      ★ {{ cot.taller_calificacion | number:'1.1-1' }}
                    </span>
                  </div>
                  <div class="report-metrics">
                    <div class="report-metric">
                      <span>Costo</span>
                      <strong>Bs {{ cot.costo_estimado }}</strong>
                    </div>
                    <div class="report-metric">
                      <span>Reparacion</span>
                      <strong>{{ cot.tiempo_reparacion_horas }} h</strong>
                    </div>
                    <div class="report-metric">
                      <span>Llegada</span>
                      <strong>{{ cot.eta_llegada_minutos }} min</strong>
                    </div>
                    <div class="report-metric">
                      <span>Garantia</span>
                      <strong>{{ cot.garantia_dias }} dias</strong>
                    </div>
                  </div>
                  <p *ngIf="cot.descripcion">{{ cot.descripcion }}</p>
                  <p class="cotizacion-extra">{{ cot.incluye_repuestos ? 'Incluye repuestos' : 'Repuestos aparte' }}</p>
                  <div class="panel-actions">
                    <button
                      class="btn-primary"
                      type="button"
                      [disabled]="selectingCotizacionId === cot.id"
                      (click)="seleccionarCotizacion(cot, report.id)"
                    >
                      {{ selectingCotizacionId === cot.id ? 'Seleccionando...' : 'Seleccionar este taller' }}
                    </button>
                  </div>
                </div>
              </div>
            </article>
          </div>

          <p class="message success" *ngIf="cotizacionMessage">{{ cotizacionMessage }}</p>
          <p class="message error" *ngIf="cotizacionError">{{ cotizacionError }}</p>
        </section>

        <section class="panel panel-payments" *ngIf="payableReports.length">
          <div class="panel-head">
            <div>
              <p class="section-kicker">Cobros</p>
              <h2>Pago QR del servicio</h2>
              <p>
                Estos servicios ya pueden pagarse por QR cuando el taller define el monto final del trabajo.
              </p>
            </div>
            <button class="btn-secondary" type="button" (click)="loadReports()">Actualizar</button>
          </div>

          <div class="report-list">
            <article class="report-card" *ngFor="let report of payableReports">
              <div class="report-top">
                <div>
                  <span class="report-id">Servicio #{{ report.id }}</span>
                  <h3>{{ report.descripcion }}</h3>
                </div>
                <span class="status-chip" [ngClass]="report.estado">{{ labelForStatus(report.estado) }}</span>
              </div>

              <div class="report-metrics">
                <div class="report-metric">
                  <span>Taller</span>
                  <strong>{{ report.taller_nombre || 'Pendiente de asignacion' }}</strong>
                </div>
                <div class="report-metric">
                  <span>Técnico</span>
                  <strong>{{ technicianLabel(report) }}</strong>
                </div>
                <div class="report-metric">
                  <span>ETA</span>
                  <strong>{{ etaLabel(report) }}</strong>
                </div>
                <div class="report-metric">
                  <span>Monto</span>
                  <strong>{{ amountLabel(report) }}</strong>
                </div>
                <div class="report-metric">
                  <span>Comisión</span>
                  <strong>{{ commissionLabel(report) }}</strong>
                </div>
              </div>

              <div class="payment-box">
                <strong>{{ report.estado_pago === 'pagado' ? 'Pago confirmado' : 'Pago QR disponible' }}</strong>
                <p>
                  {{
                    report.estado_pago === 'pagado'
                      ? 'El servicio ya fue marcado como pagado.'
                      : 'El cobro se habilitara cuando el taller marque el servicio en ejecucion o finalizado.'
                  }}
                </p>
              </div>

              <div class="panel-actions">
                <button
                  class="btn-primary"
                  type="button"
                  [disabled]="!canOpenGateway(report)"
                  (click)="openPaymentPlaceholder(report)"
                >
                  Abrir pasarela
                </button>
              </div>
            </article>
          </div>

          <p class="message error" *ngIf="reportError">{{ reportError }}</p>
        </section>
      </main>

      <div class="modal-backdrop" *ngIf="selectedReportForPayment" (click)="closePaymentPlaceholder()">
        <section class="payment-modal" (click)="$event.stopPropagation()">
          <p class="eyebrow">Pasarela QR</p>
          <h3>Servicio #{{ selectedReportForPayment.id }}</h3>
          <p>
            Escanea el QR con tu banco o billetera movil y confirma el pago del servicio.
          </p>

          <div class="modal-grid">
            <div class="modal-item">
              <span>Monto</span>
              <strong>{{ amountLabel(selectedReportForPayment) }}</strong>
            </div>
            <div class="modal-item">
              <span>Estado</span>
              <strong>{{ labelForStatus(selectedReportForPayment.estado) }}</strong>
            </div>
            <div class="modal-item">
              <span>Taller</span>
              <strong>{{ selectedReportForPayment.taller_nombre || 'Pendiente' }}</strong>
            </div>
            <div class="modal-item">
              <span>Técnico</span>
              <strong>{{ technicianLabel(selectedReportForPayment) }}</strong>
            </div>
          </div>

          <div class="payment-box">
            <strong>Pago seguro por QR</strong>
            <p>Usa el monto indicado y conserva el comprobante de la transaccion.</p>
          </div>

          <div class="qr-pay-panel">
            <img src="/assets/payment-qr.jpeg" alt="QR de pago del servicio" />
            <div>
              <strong>{{ amountLabel(selectedReportForPayment) }}</strong>
              <span>Referencia: Servicio #{{ selectedReportForPayment.id }}</span>
            </div>
          </div>

          <p class="message success" *ngIf="paymentMessage">{{ paymentMessage }}</p>
          <p class="message error" *ngIf="paymentError">{{ paymentError }}</p>

          <div class="panel-actions">
            <button
              class="btn-primary"
              type="button"
              [disabled]="paymentProcessing || selectedReportForPayment.estado_pago === 'pagado'"
              (click)="confirmPayment()"
            >
              {{ paymentProcessing ? 'Confirmando...' : 'Confirmar pago' }}
            </button>
            <button class="btn-secondary" type="button" (click)="closePaymentPlaceholder()">Cerrar</button>
          </div>
        </section>
      </div>

    </div>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(214, 149, 82, 0.16), transparent 28%),
        linear-gradient(180deg, #f8f2ea 0%, #f6f7fb 46%, #ffffff 100%);
      color: #18120e;
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }

    .portal-shell {
      max-width: 1260px;
      margin: 0 auto;
      padding: 28px 20px 44px;
    }

    .hero-card,
    .panel,
    .payment-modal {
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid #eadcca;
      box-shadow: 0 18px 42px rgba(64, 37, 18, 0.08);
    }

    /* Topbar oscura horizontal (rediseño Stitch) */
    .navbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      background: #1a1410;
      color: #f4e6d3;
      border-radius: 14px;
      padding: 12px 20px;
      margin-bottom: 18px;
    }
    .navbar-brand {
      font-weight: 800;
      letter-spacing: 0.18em;
      font-size: 13px;
    }
    .navbar-links {
      display: flex;
      gap: 22px;
      flex: 1;
      justify-content: center;
    }
    .nav-link {
      color: #d8c4a8;
      text-decoration: none;
      font-size: 13px;
      cursor: pointer;
      letter-spacing: 0.02em;
    }
    .nav-link.active,
    .nav-link:hover {
      color: #fff8ef;
    }
    .navbar-user {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .user-chip {
      text-align: right;
      font-size: 12px;
      color: #c19a6a;
    }
    .user-chip strong {
      display: block;
      color: #fff8ef;
      font-size: 13px;
    }
    .btn-logout {
      background: transparent;
      border: 1px solid #5a3a22;
      color: #f4c58e;
      padding: 8px 14px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 0.04em;
    }
    .btn-logout:hover { background: #2a1d14; }

    .page-heading {
      padding: 10px 4px 22px;
    }

    /* Resumen rapido en 3 cards horizontales */
    .resumen-rapido { margin-bottom: 22px; }
    .resumen-cards {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      background: linear-gradient(135deg, #1f1a16 0%, #5b3a23 60%, #b5651d 100%);
      padding: 18px;
      border-radius: 22px;
    }
    .resumen-card {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      background: rgba(255, 248, 239, 0.94);
      border-radius: 18px;
      padding: 14px 18px;
    }
    .resumen-text { display: flex; flex-direction: column; gap: 2px; flex: 1; padding: 0 6px; }
    .resumen-icon { flex-shrink: 0; line-height: 1; }
    .resumen-icon-left {
      font-size: 22px;
      background: #f4dbb9;
      border-radius: 12px;
      padding: 8px;
    }
    .resumen-icon-right { font-size: 32px; opacity: 0.55; }

    /* Mis vehiculos: hero card con thumbnail + grid 2x2 */
    .vehicle-hero {
      display: flex;
      gap: 18px;
      align-items: center;
      padding: 16px;
      background: #fdf6ec;
      border: 1px solid #eadcca;
      border-radius: 18px;
      margin-bottom: 14px;
    }
    .vehicle-thumb {
      width: 96px; height: 70px;
      background: #d8c4a8;
      border-radius: 14px;
      display: flex; align-items: center; justify-content: center;
      font-size: 36px;
      flex-shrink: 0;
    }
    .vehicle-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 22px;
      flex: 1;
    }
    .vehicle-grid > div span {
      display: block;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: #8a6647;
    }
    .vehicle-grid > div strong { font-size: 1rem; }
    .form-section-title {
      margin: 8px 0 6px;
      font-weight: 800;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: #8a6647;
    }

    /* Reportar accidente sobre fondo oscuro marron */
    .panel-dark {
      background: linear-gradient(135deg, #4a3120 0%, #7a4d2c 100%);
      color: #fff8ef;
      border: none;
    }
    .report-panel {
      width: min(1220px, calc(100% - 24px));
      margin-inline: auto;
      border-radius: 28px;
      padding: clamp(22px, 3vw, 34px);
      box-shadow: 0 24px 60px rgba(74, 49, 32, 0.22);
    }
    .report-panel .panel-head,
    .report-form {
      width: min(1080px, 100%);
      margin-inline: auto;
    }
    .panel-dark .section-kicker-light { color: #f4c58e; font-size: 13px; }
    .panel-dark .field span { color: #f0d8b8; }
    .panel-dark select,
    .panel-dark textarea,
    .panel-dark input[type=text] {
      background: #fff8ef;
      color: #1f1a16;
      border-radius: 10px;
      border: 1px solid #c19a6a;
      padding: 10px 12px;
    }
    .report-form { display: flex; flex-direction: column; gap: 14px; }
    .report-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 12px;
      align-items: stretch;
    }
    .report-side-actions {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .btn-side {
      min-height: 44px;
      border-radius: 14px;
      padding: 11px 16px;
      cursor: pointer;
      font-weight: 900;
      font-size: 14px;
      transition: transform .2s ease, box-shadow .2s ease, background .2s ease, border-color .2s ease;
    }
    .btn-side:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 28px rgba(31, 26, 22, .22);
    }
    .btn-side-light {
      background: #fff8ef;
      color: #4a3120;
      border: 1px solid #f4c58e;
    }
    .btn-side-light:hover { background: #ffe9c7; }
    .btn-side-map {
      background: linear-gradient(180deg, #f4c58e 0%, #d58a3a 100%);
      color: #2f1e12;
      border: 1px solid #f7d29e;
    }
    .btn-side-map:hover { background: linear-gradient(180deg, #ffd799 0%, #e99b40 100%); }
    .btn-side-outline {
      background: rgba(255, 248, 239, .08);
      color: #fff8ef;
      border: 1px solid rgba(244, 197, 142, .55);
    }
    .btn-side-outline:hover { background: rgba(255, 248, 239, .16); }
    .location-summary {
      font-size: 12px;
      color: #f4c58e;
      margin: 2px 0 0;
    }
    .inline-map-panel {
      overflow: hidden;
      border-radius: 24px;
      padding: 20px;
      background: rgba(47, 30, 18, .58);
      border: 1px solid rgba(244, 197, 142, .35);
      box-shadow: inset 0 1px 0 rgba(255, 248, 239, .08), 0 24px 48px rgba(31, 26, 22, .22);
      animation: mapReveal .42s cubic-bezier(.2,.8,.2,1) both;
      transform-origin: top center;
    }
    .inline-map-copy {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 14px;
    }
    .inline-map-copy h3 {
      margin: 0 0 4px;
      color: #fff8ef;
      font-size: 1.35rem;
    }
    .inline-map-copy p {
      margin: 0;
      color: #f0d8b8;
      line-height: 1.55;
    }
    .btn-map-close {
      flex: 0 0 auto;
      border: 1px solid rgba(244, 197, 142, .45);
      border-radius: 999px;
      background: rgba(255, 248, 239, .1);
      color: #fff8ef;
      padding: 10px 14px;
      font-weight: 900;
      cursor: pointer;
      transition: transform .2s ease, background .2s ease;
    }
    .btn-map-close:hover {
      transform: translateY(-2px);
      background: rgba(255, 248, 239, .18);
    }
    .inline-map-footer {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
    }
    .inline-map-footer .modal-grid {
      margin: 0;
      align-items: stretch;
    }
    .btn-secondary-on-dark {
      background: #fff8ef !important;
      color: #4a3120 !important;
      border-color: #f4c58e !important;
    }
    @keyframes mapReveal {
      from {
        opacity: 0;
        max-height: 0;
        transform: translateY(-12px) scale(.98);
      }
      to {
        opacity: 1;
        max-height: 760px;
        transform: translateY(0) scale(1);
      }
    }
    .btn-crear-solicitud {
      width: 100%;
      padding: 14px;
      background: linear-gradient(180deg, #b5651d 0%, #8a4a16 100%);
      color: #fff8ef;
      border: none;
      border-radius: 12px;
      font-weight: 800;
      font-size: 1rem;
      cursor: pointer;
      letter-spacing: 0.02em;
    }
    .btn-crear-solicitud:disabled { opacity: 0.5; cursor: not-allowed; }
    .resumen-card strong {
      font-size: 1.8rem;
      line-height: 1;
      color: #1f1a16;
    }
    .resumen-card span {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #8a6647;
    }

    .eyebrow,
    .section-kicker {
      margin: 0 0 8px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 11px;
      font-weight: 800;
      color: #9a6133;
    }

    .eyebrow-light {
      color: #f4c58e;
    }

    h1,
    h2,
    h3 {
      font-family: "Segoe UI Semibold", "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
      letter-spacing: -0.01em;
    }

    h1 {
      margin: 0;
      font-size: clamp(2.4rem, 4.5vw, 4.2rem);
      line-height: 0.96;
      max-width: 760px;
    }

    .lede {
      margin: 14px 0 0;
      max-width: 720px;
      color: #685a4b;
      line-height: 1.7;
    }

    .topbar-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
    }

    .identity-chip {
      min-width: 180px;
      padding: 14px 16px;
      border-radius: 20px;
      background: #fff8ef;
      border: 1px solid #eadcca;
    }

    .identity-chip span {
      display: block;
      font-size: 12px;
      color: #8a6647;
      margin-bottom: 4px;
    }

    .identity-chip strong {
      font-size: 1rem;
    }

    .hero-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
      gap: 18px;
      margin-bottom: 20px;
    }

    .hero-card {
      border-radius: 30px;
      overflow: hidden;
    }

    .hero-main {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(240px, 0.8fr);
      gap: 18px;
      padding: 26px;
      background: linear-gradient(135deg, #1f1a16 0%, #4f311f 58%, #c26122 100%);
      color: #fff8ef;
    }

    .hero-main h2 {
      margin: 0 0 10px;
      font-size: clamp(2rem, 3vw, 2.8rem);
      line-height: 0.98;
    }

    .hero-main p {
      margin: 0;
      color: rgba(255, 242, 227, 0.88);
      line-height: 1.7;
    }

    .hero-note {
      padding: 24px;
    }

    .hero-note h3 {
      margin: 0 0 10px;
      font-size: 1.8rem;
    }

    .hero-note p,
    .hero-note li {
      color: #6c5b4d;
      line-height: 1.65;
    }

    .hero-note ul {
      margin: 14px 0 0;
      padding-left: 20px;
    }

    .metric-grid {
      display: grid;
      gap: 12px;
    }

    .metric-card {
      padding: 16px;
      border-radius: 22px;
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .metric-card span {
      display: block;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-weight: 800;
      color: rgba(255, 225, 196, 0.78);
    }

    .metric-card strong {
      display: block;
      margin-top: 8px;
      font-size: 2rem;
      line-height: 1;
    }

    .dashboard-grid.single-col { grid-template-columns: 1fr !important; }
    .dashboard-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }

    .panel {
      border-radius: 30px;
      padding: 24px;
    }

    .panel-payments {
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
      color: #685a4b;
      line-height: 1.7;
      max-width: 560px;
    }

    .badge {
      padding: 10px 14px;
      border-radius: 999px;
      background: #fff1e3;
      color: #9d501a;
      font-size: 12px;
      font-weight: 800;
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
      color: #1d1714;
      font: inherit;
    }

    textarea {
      resize: vertical;
      min-height: 120px;
    }

    input:focus,
    select:focus,
    textarea:focus {
      outline: none;
      border-color: rgba(191, 93, 36, 0.66);
      box-shadow: 0 0 0 4px rgba(191, 93, 36, 0.10);
    }

    .location-box {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      padding: 16px 18px;
      border-radius: 22px;
      border: 1px solid #efdfcd;
      background: #fff8ef;
    }

    .location-title {
      display: block;
      margin-bottom: 6px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #8a6544;
    }

    .location-box p {
      margin: 0;
      color: #6d5c4d;
      line-height: 1.6;
    }

    .location-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .panel-actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 8px;
    }

    .btn-primary,
    .btn-secondary,
    .btn-ghost {
      border: none;
      cursor: pointer;
      font: inherit;
      font-weight: 800;
      transition: transform 0.16s ease, opacity 0.16s ease;
    }

    .btn-primary:hover,
    .btn-secondary:hover,
    .btn-ghost:hover {
      transform: translateY(-1px);
    }

    .btn-primary {
      padding: 13px 20px;
      border-radius: 999px;
      background: linear-gradient(135deg, #241c17 0%, #4e321f 55%, #bf5d24 100%);
      color: #fff9f0;
    }

    .btn-primary:disabled {
      opacity: 0.55;
      cursor: not-allowed;
      transform: none;
    }

    .btn-secondary,
    .btn-ghost {
      padding: 13px 18px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.72);
      color: #2d231b;
      border: 1px solid #eadcca;
    }

    .message {
      margin: 0;
      font-size: 13px;
      line-height: 1.5;
    }

    .message.success {
      color: #16714a;
    }

    .message.error {
      color: #b22d24;
    }

    .vehicle-list {
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
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.88) 0%, rgba(247, 239, 229, 0.82) 100%);
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
      font-size: 1.3rem;
      line-height: 1.1;
    }

    .vehicle-card p {
      margin: 0;
      color: #685a4b;
    }

    .report-list {
      display: grid;
      gap: 14px;
    }

    .report-card {
      padding: 22px;
      border-radius: 26px;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(250, 244, 236, 0.92) 100%);
      border: 1px solid rgba(127, 92, 58, 0.12);
    }

    .cotizacion-list { display: grid; gap: 12px; margin-top: 14px; }
    .cotizacion-card {
      padding: 16px 18px; border-radius: 18px;
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid rgba(127, 92, 58, 0.18);
    }

    .report-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 14px;
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

    .report-top h3 {
      margin: 0;
      font-size: 1.4rem;
      line-height: 1.15;
    }

    .report-metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
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
      line-height: 1.45;
    }

    .payment-box {
      padding: 14px;
      border-radius: 18px;
      background: #fff7ef;
      border: 1px solid #efdfcd;
      margin-bottom: 14px;
    }

    .payment-box strong {
      display: block;
      margin-bottom: 6px;
    }

    .payment-box p {
      margin: 0;
      color: #6d5c4d;
      line-height: 1.6;
    }

    .qr-pay-panel {
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 18px;
      align-items: center;
      margin: 18px 0;
      padding: 16px;
      border: 1px solid #ead8c6;
      border-radius: 22px;
      background: #fffaf5;
    }

    .qr-pay-panel img {
      width: 100%;
      border-radius: 18px;
      background: #fff;
      box-shadow: 0 18px 35px rgba(43, 28, 20, .12);
    }

    .qr-pay-panel strong {
      display: block;
      font-size: 26px;
      color: #24130d;
    }

    .qr-pay-panel span {
      color: #7b6a5f;
      font-weight: 700;
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
      color: #685a4b;
    }

    .empty-state strong {
      font-size: 1.05rem;
      color: #1d1714;
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

    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(20, 16, 13, 0.55);
      display: grid;
      place-items: center;
      padding: 20px;
      z-index: 40;
    }

    .payment-modal {
      width: min(560px, 100%);
      border-radius: 28px;
      padding: 24px;
    }

    .payment-modal h3 {
      margin: 0 0 10px;
      font-size: 2rem;
    }

    .payment-modal p {
      color: #6c5b4d;
      line-height: 1.65;
    }

    .modal-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin: 16px 0;
    }

    .modal-item {
      min-height: 78px;
      padding: 14px 16px;
      border-radius: 18px;
      background: #fff8ef;
      border: 1px solid #efdfcd;
      display: grid;
      align-content: center;
      gap: 6px;
      overflow: hidden;
    }

    .modal-item span {
      display: block;
      margin-bottom: 6px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #8a6544;
    }

    .modal-item strong {
      display: block;
      min-width: 0;
      line-height: 1.35;
      color: #2f241d;
      font-size: 1rem;
      overflow-wrap: anywhere;
      white-space: normal;
    }

    .map-modal {
      width: min(920px, 100%);
    }

    .map-frame {
      position: relative;
      height: 420px;
      border-radius: 24px;
      overflow: hidden;
      border: 1px solid #efdfcd;
      margin: 16px 0;
    }

    .map-frame #client-report-map {
      width: 100%;
      height: 100%;
    }

    .center-pin {
      position: absolute;
      inset: 0;
      pointer-events: none;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      transform: translateY(-16px);
      z-index: 1200;
      filter: drop-shadow(0 14px 18px rgba(0, 0, 0, 0.35));
    }

    .pin-head {
      display: block;
      width: 44px;
      height: 44px;
      border-radius: 50% 50% 50% 0;
      background: #c04f12;
      border: 4px solid #fff;
      transform: rotate(-45deg);
      box-shadow: 0 12px 22px rgba(0, 0, 0, 0.28);
      position: relative;
      font-size: 0;
    }

    .pin-head::after {
      content: '';
      position: absolute;
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: #fff;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
    }

    .pin-shadow {
      width: 18px;
      height: 8px;
      border-radius: 999px;
      background: rgba(0, 0, 0, 0.18);
      filter: blur(1px);
      margin-top: 6px;
    }

    .ai-upload-box {
      gap: 12px;
      background: #fff8ef;
      border: 1px dashed #d7b99f;
    }

    .ai-upload-box input[type='file'] {
      padding: 12px;
      border-radius: 16px;
      border: 1px solid #efdfcd;
      background: #fff;
    }

    .ai-upload-box p,
    .preview-card p {
      margin: 6px 0 0;
      color: #6d5c4d;
      line-height: 1.45;
    }

    .ai-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .preview-card {
      padding: 14px;
      border-radius: 18px;
      background: #fff;
      border: 1px solid #efdfcd;
    }

    @media (max-width: 1080px) {
      .hero-grid,
      .dashboard-grid,
      .hero-main {
        grid-template-columns: 1fr;
      }

      .report-metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .inline-map-footer {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 820px) {
      .portal-shell {
        padding: 20px 14px 32px;
      }

      .topbar {
        flex-direction: column;
      }

      .topbar-actions {
        width: 100%;
        justify-content: flex-start;
      }

      .panel,
      .hero-main,
      .hero-note,
      .payment-modal {
        padding: 20px;
      }

      .form-layout,
      .report-metrics,
      .modal-grid,
      .report-side-actions {
        grid-template-columns: 1fr;
      }

      .report-panel {
        width: 100%;
        border-radius: 22px;
      }

      .inline-map-copy {
        flex-direction: column;
      }

      .map-frame {
        height: 320px;
      }

      .location-box {
        flex-direction: column;
        align-items: stretch;
      }

      .panel-head,
      .report-top {
        flex-direction: column;
      }

      .btn-primary,
      .btn-secondary,
      .btn-ghost {
        width: 100%;
      }
    }
  `]
})
export class ClientPortalComponent implements OnInit, OnDestroy {
  profileForm: FormGroup;
  vehicleForm: FormGroup;
  reportForm: FormGroup;
  vehicles: Vehicle[] = [];
  reports: Solicitud[] = [];
  cotizacionesPorReporte: Record<number, Cotizacion[]> = {};
  cotizacionesLoading: Record<number, boolean> = {};
  cotizacionMessage = '';
  cotizacionError = '';
  selectingCotizacionId: number | null = null;
  selectedReportForPayment: Solicitud | null = null;
  vehiclePhotoFiles: File[] = [];
  vehiclePreview: VehiclePhotoPreview | null = null;
  selectedLat: number | null = null;
  selectedLng: number | null = null;
  mapPickerOpen = false;
  audioBlob: Blob | null = null;
  audioUrl = '';
  isRecording = false;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: BlobPart[] = [];
  private mapInstance: L.Map | null = null;
  private reportRealtimeSubs = new Map<number, Subscription>();
  private flushedSub?: Subscription;

  savingProfile = false;
  savingVehicle = false;
  savingReport = false;
  analyzingVehicle = false;
  profileMessage = '';
  profileError = '';
  vehicleMessage = '';
  vehicleError = '';
  reportMessage = '';
  reportError = '';
  paymentProcessing = false;
  paymentMessage = '';
  paymentError = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private vehicleService: VehicleService,
    private solicitudService: SolicitudService,
    private realtimeService: RealtimeService,
    private offlineQueue: OfflineQueueService,
    private cotizacionService: CotizacionService,
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
      color: [''],
      anio: ['']
    });

    this.reportForm = this.fb.group({
      vehiculo_id: [null, Validators.required],
      descripcion: ['', [Validators.required, Validators.minLength(12)]]
    });
  }

  get displayName(): string {
    return this.authService.getCurrentUser()?.full_name || 'Cliente';
  }

  get payableReports(): Solicitud[] {
    return this.reports.filter((report) => this.canOpenGateway(report));
  }

  get pendingReports(): Solicitud[] {
    return this.reports.filter(
      (report) => report.id > 0 && ['pendiente', 'buscando_taller'].includes(report.estado),
    );
  }

  get locationSummary(): string {
    if (this.selectedLat == null || this.selectedLng == null) {
      return 'Ubicacion pendiente. Usa tu GPS o mueve el mapa hasta el punto exacto.';
    }
    return `${this.selectedLat.toFixed(6)}, ${this.selectedLng.toFixed(6)}`;
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
    this.flushedSub = this.offlineQueue.flushed$.subscribe((result) => {
      if (result.synced > 0) {
        this.reportMessage = `Sincronizadas ${result.synced} emergencia(s) pendientes.`;
        this.loadReports();
      }
    });
  }

  ngOnDestroy() {
    this.destroyMapPicker();
    this.clearRecording();
    this.reportRealtimeSubs.forEach((sub) => sub.unsubscribe());
    this.reportRealtimeSubs.clear();
    this.flushedSub?.unsubscribe();
  }

  loadProfile() {
    this.authService.getProfile().pipe(timeout(10000)).subscribe({
      next: (user) => {
        this.profileForm.patchValue(user);
      },
      error: () => {
        this.profileError = 'No se pudo cargar tu perfil.';
      }
    });
  }

  loadVehicles() {
    this.vehicleService.getVehicles().pipe(timeout(10000)).subscribe({
      next: (vehicles) => {
        this.vehicles = vehicles;
        const currentVehicle = this.reportForm.value.vehiculo_id;
        if (!currentVehicle && vehicles.length) {
          this.reportForm.patchValue({ vehiculo_id: vehicles[0].id });
        }
        this.loadReports();
      },
      error: () => {
        this.vehicleError = 'No se pudieron cargar tus vehiculos.';
        this.reports = [];
      }
    });
  }

  loadReports() {
    const ownVehicleIds = new Set(this.vehicles.map((vehicle) => vehicle.id));
    if (!ownVehicleIds.size) {
      this.reports = [];
      return;
    }

    this.reportError = '';
    this.solicitudService.getSolicitudes().pipe(timeout(10000)).subscribe({
      next: (reports) => {
        this.reports = reports
          .filter((report) => !!report.vehiculo_id && ownVehicleIds.has(report.vehiculo_id))
          .sort((left, right) => right.id - left.id);
        this.connectReportsRealtime();
        this.reloadCotizaciones();
      },
      error: () => {
        this.reportError = 'No se pudo cargar el estado de tus solicitudes.';
      }
    });
  }

  reloadCotizaciones(): void {
    const activos = new Set(this.pendingReports.map((report) => report.id));
    Object.keys(this.cotizacionesPorReporte).forEach((key) => {
      if (!activos.has(Number(key))) {
        delete this.cotizacionesPorReporte[Number(key)];
      }
    });
    this.pendingReports.forEach((report) => this.loadCotizaciones(report.id));
  }

  loadCotizaciones(reportId: number): void {
    this.cotizacionesLoading[reportId] = true;
    this.cotizacionService.listarPorSolicitud(reportId).pipe(timeout(10000)).subscribe({
      next: (cotizaciones) => {
        this.cotizacionesPorReporte[reportId] = cotizaciones.filter(
          (cot) => cot.estado === 'enviada',
        );
        this.cotizacionesLoading[reportId] = false;
      },
      error: () => {
        this.cotizacionesLoading[reportId] = false;
      },
    });
  }

  seleccionarCotizacion(cotizacion: Cotizacion, reportId: number): void {
    this.cotizacionMessage = '';
    this.cotizacionError = '';
    this.selectingCotizacionId = cotizacion.id;
    this.cotizacionService.seleccionar(cotizacion.id).pipe(timeout(10000)).subscribe({
      next: () => {
        this.selectingCotizacionId = null;
        this.cotizacionMessage = `Taller ${cotizacion.taller_nombre ?? ''} asignado a tu servicio.`.trim();
        delete this.cotizacionesPorReporte[reportId];
        this.loadReports();
      },
      error: (error) => {
        this.selectingCotizacionId = null;
        this.cotizacionError = error?.error?.detail || 'No se pudo seleccionar la cotizacion.';
        this.loadCotizaciones(reportId);
      },
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
      finalize(() => {
        this.savingProfile = false;
      })
    ).subscribe({
      next: (user) => {
        this.profileForm.patchValue(user);
        this.profileMessage = 'Perfil actualizado correctamente.';
      },
      error: (error) => {
        this.profileError = error?.error?.detail || 'No se pudo actualizar el perfil.';
      }
    });
  }

  addVehicle() {
    if (this.vehicleForm.invalid) {
      this.vehicleForm.markAllAsTouched();
      return;
    }

    this.vehicleError = '';
    this.vehicleMessage = '';
    this.savingVehicle = true;
    this.vehicleService.createVehicle(this.vehicleForm.getRawValue()).pipe(
      timeout(10000),
      finalize(() => {
        this.savingVehicle = false;
      })
    ).subscribe({
      next: (vehicle) => {
        this.vehicles = [vehicle, ...this.vehicles];
        this.vehicleForm.reset({ placa: '', marca: '', modelo: '', color: '', anio: '' });
        this.vehiclePhotoFiles = [];
        this.vehiclePreview = null;
        if (!this.reportForm.value.vehiculo_id) {
          this.reportForm.patchValue({ vehiculo_id: vehicle.id });
        }
        this.vehicleMessage = 'Vehiculo registrado correctamente.';
        this.loadReports();
      },
      error: (error) => {
        this.vehicleError = error?.error?.detail || 'No se pudo registrar el vehiculo.';
      }
    });
  }

  saveReport() {
    if (this.reportForm.invalid) {
      this.reportForm.markAllAsTouched();
      return;
    }
    if (this.selectedLat == null || this.selectedLng == null) {
      this.reportError = 'Selecciona una ubicacion valida usando el mapa o tu ubicacion actual.';
      this.reportMessage = '';
      return;
    }

    this.reportError = '';
    this.reportMessage = '';
    this.savingReport = true;
    this.solicitudService.createSolicitud({
      vehiculo_id: this.reportForm.value.vehiculo_id,
      descripcion: this.reportForm.value.descripcion,
      latitud: this.selectedLat,
      longitud: this.selectedLng
    }).pipe(
      timeout(10000),
      finalize(() => {
        this.savingReport = false;
      })
    ).subscribe({
      next: (report) => {
        this.reports = [report, ...this.reports].sort((left, right) => right.id - left.id);
        this.reportMessage = report.estado === 'pendiente_sync'
          ? 'Sin conexion: solicitud guardada y pendiente de sincronizacion.'
          : 'Solicitud creada correctamente.';
        this.connectReportsRealtime();
        this.reportForm.reset({
          vehiculo_id: this.vehicles[0]?.id ?? null,
          descripcion: ''
        });
        this.selectedLat = null;
        this.selectedLng = null;
        this.clearRecording();
      },
      error: (error) => {
        this.reportError = error?.error?.detail || 'No se pudo crear la solicitud.';
      }
    });
  }

  handleVehiclePhotos(event: Event) {
    const input = event.target as HTMLInputElement;
    this.vehiclePhotoFiles = Array.from(input.files ?? []).slice(0, 4);
    this.vehiclePreview = null;
    this.vehicleError = '';
  }

  async startRecording() {
    if (!navigator.mediaDevices?.getUserMedia) {
      this.reportError = 'Tu navegador no permite grabar audio.';
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.audioChunks = [];
    this.mediaRecorder = new MediaRecorder(stream);
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };
    this.mediaRecorder.onstop = () => {
      this.audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
      this.audioUrl = URL.createObjectURL(this.audioBlob);
      stream.getTracks().forEach((track) => track.stop());
    };
    this.isRecording = true;
    this.mediaRecorder.start();
  }

  stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
    }
    this.isRecording = false;
  }

  clearRecording() {
    if (this.audioUrl) {
      URL.revokeObjectURL(this.audioUrl);
    }
    this.audioBlob = null;
    this.audioUrl = '';
    this.audioChunks = [];
    this.isRecording = false;
    this.mediaRecorder = null;
  }

  analyzeVehiclePhotos() {
    if (!this.vehiclePhotoFiles.length) {
      this.vehicleError = 'Selecciona al menos una foto del vehículo.';
      return;
    }

    this.vehicleError = '';
    this.vehicleMessage = '';
    this.analyzingVehicle = true;

    this.vehicleService.previewVehicleFromPhotos(this.vehiclePhotoFiles).pipe(
      timeout(45000),
      finalize(() => {
        this.analyzingVehicle = false;
      })
    ).subscribe({
      next: (preview) => {
        this.vehiclePreview = preview;
        this.vehicleForm.patchValue({
          placa: preview.placa || this.vehicleForm.value.placa,
          marca: preview.marca || this.vehicleForm.value.marca,
          modelo: preview.modelo || this.vehicleForm.value.modelo,
          color: preview.color || this.vehicleForm.value.color,
          anio: preview.anio?.toString() || this.vehicleForm.value.anio
        });
        this.vehicleMessage = 'La IA completo una previsualizacion editable. Revisa los campos antes de guardar.';
      },
      error: (error) => {
        this.vehicleError = error?.error?.detail || 'La IA no pudo analizar las fotos del vehículo.';
      }
    });
  }

  useCurrentLocation() {
    this.reportError = '';
    if (!navigator.geolocation) {
      this.reportError = 'Tu navegador no permite obtener la ubicacion actual.';
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        this.selectedLat = Number(position.coords.latitude.toFixed(6));
        this.selectedLng = Number(position.coords.longitude.toFixed(6));
        if (this.mapInstance) {
          this.mapInstance.setView([this.selectedLat, this.selectedLng], 16);
        }
      },
      () => {
        this.reportError = 'No se pudo obtener la ubicacion actual.';
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  openMapPicker() {
    this.mapPickerOpen = true;
    setTimeout(() => this.initializeMapPicker(), 0);
  }

  closeMapPicker() {
    this.destroyMapPicker();
    this.mapPickerOpen = false;
  }

  confirmMapLocation() {
    this.closeMapPicker();
  }

  private initializeMapPicker() {
    const host = document.getElementById('client-report-map');
    if (!host) {
      return;
    }

    const lat = this.selectedLat ?? -16.5;
    const lng = this.selectedLng ?? -68.15;
    this.selectedLat = lat;
    this.selectedLng = lng;

    if (!this.mapInstance) {
      this.mapInstance = L.map(host, {
        zoomControl: true,
        attributionControl: true
      }).setView([lat, lng], 15);

      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(this.mapInstance);

      this.mapInstance.on('moveend', () => {
        if (!this.mapInstance) {
          return;
        }
        const center = this.mapInstance.getCenter();
        this.selectedLat = Number(center.lat.toFixed(6));
        this.selectedLng = Number(center.lng.toFixed(6));
      });
    } else {
      this.mapInstance.setView([lat, lng], this.mapInstance.getZoom() || 15);
    }

    setTimeout(() => this.mapInstance?.invalidateSize(), 50);
    setTimeout(() => this.mapInstance?.invalidateSize(), 250);
    setTimeout(() => this.mapInstance?.invalidateSize(), 600);
  }

  private destroyMapPicker() {
    if (!this.mapInstance) {
      return;
    }
    this.mapInstance.remove();
    this.mapInstance = null;
  }

  canOpenGateway(report: Solicitud): boolean {
    return ['en_proceso', 'finalizado', 'en_progreso', 'resuelta'].includes(report.estado);
  }

  amountLabel(report: Solicitud): string {
    return report.precio_cobrado == null ? 'Pendiente' : `Bs ${report.precio_cobrado.toFixed(2)}`;
  }

  commissionLabel(report: Solicitud): string {
    return report.comision_plataforma == null ? 'Pendiente' : `Bs ${report.comision_plataforma.toFixed(2)}`;
  }

  technicianLabel(report: Solicitud): string {
    if (report.tecnico_nombre) {
      return report.tecnico_especialidad
        ? `${report.tecnico_nombre} - ${report.tecnico_especialidad}`
        : report.tecnico_nombre;
    }
    return 'Pendiente';
  }

  etaLabel(report: Solicitud): string {
    return report.tiempo_estimado_minutos == null
      ? 'Pendiente'
      : `${report.tiempo_estimado_minutos} min`;
  }

  labelForStatus(status: string): string {
    const map: Record<string, string> = {
      pendiente: 'Pendiente',
      pendiente_sync: 'Pendiente sync',
      buscando_taller: 'Buscando taller',
      asignada: 'Asignada',
      tecnico_en_camino: 'Técnico en camino',
      tecnico_llego: 'Técnico llegó',
      en_proceso: 'En proceso',
      finalizado: 'Finalizado',
      cancelado: 'Cancelado',
      en_progreso: 'En progreso',
      resuelta: 'Finalizado',
      cancelada: 'Cancelado'
    };
    return map[status] ?? status;
  }

  private connectReportsRealtime(): void {
    const activeReports = this.reports.filter((report) => report.id > 0 && !['finalizado', 'cancelado', 'resuelta', 'cancelada'].includes(report.estado));
    const activeIds = new Set(activeReports.map((report) => report.id));

    this.reportRealtimeSubs.forEach((sub, id) => {
      if (!activeIds.has(id)) {
        sub.unsubscribe();
        this.reportRealtimeSubs.delete(id);
      }
    });

    activeReports.forEach((report) => {
      if (this.reportRealtimeSubs.has(report.id)) return;
      const sub = this.realtimeService.subscribe('solicitud', report.id).subscribe((event) => {
        this.applyRealtimeEvent(event);
      });
      this.reportRealtimeSubs.set(report.id, sub);
    });
  }

  private applyRealtimeEvent(event: RealtimeEvent): void {
    if (event.event === 'solicitud.actualizada') {
      const payload = event.payload as Partial<Solicitud>;
      if (payload.id) {
        this.mergeReport(payload.id, payload);
      }
      return;
    }

    if (event.event === 'cotizacion.nueva') {
      const payload = event.payload as Partial<Cotizacion>;
      if (payload.solicitud_id) {
        this.loadCotizaciones(payload.solicitud_id);
      }
      return;
    }

    if (event.event === 'cotizacion.aceptada') {
      // Una cotización fue aceptada (por este u otro dispositivo): refrescar
      // reports para reflejar el estado ASIGNADA y limpiar la lista.
      this.loadReports();
      return;
    }

    if (event.event === 'tracking.update') {
      const payload = event.payload as {
        solicitud_id?: number;
        latitud?: number;
        longitud?: number;
        eta_minutos?: number;
        distancia_restante_km?: number;
      };
      if (!payload.solicitud_id) return;
      this.mergeReport(payload.solicitud_id, {
        tecnico_latitud: payload.latitud,
        tecnico_longitud: payload.longitud,
        tiempo_estimado_minutos: payload.eta_minutos,
        distancia_tecnico_km: payload.distancia_restante_km,
      });
    }
  }

  private mergeReport(reportId: number, patch: Partial<Solicitud>): void {
    this.reports = this.reports.map((report) => report.id === reportId ? { ...report, ...patch } : report);
    if (this.selectedReportForPayment?.id === reportId) {
      this.selectedReportForPayment = { ...this.selectedReportForPayment, ...patch };
    }
  }

  openPaymentPlaceholder(report: Solicitud) {
    if (!this.canOpenGateway(report)) {
      return;
    }
    this.paymentMessage = '';
    this.paymentError = '';
    this.selectedReportForPayment = report;
  }

  closePaymentPlaceholder() {
    this.selectedReportForPayment = null;
    this.paymentProcessing = false;
    this.paymentMessage = '';
    this.paymentError = '';
  }

  confirmPayment() {
    if (!this.selectedReportForPayment || this.selectedReportForPayment.estado_pago === 'pagado') {
      return;
    }
    this.paymentProcessing = true;
    this.paymentMessage = '';
    this.paymentError = '';
    this.solicitudService.pagarSolicitud(
      this.selectedReportForPayment.id,
      this.selectedReportForPayment.precio_cobrado
    ).subscribe({
      next: (updated) => {
        this.reports = this.reports.map((report) => report.id === updated.id ? updated : report);
        this.selectedReportForPayment = updated;
        this.paymentProcessing = false;
        this.paymentMessage = 'Pago confirmado correctamente.';
      },
      error: (error) => {
        this.paymentProcessing = false;
        this.paymentError = error?.error?.detail || 'No se pudo confirmar el pago.';
      }
    });
  }

  logout() {
    this.authService.logout();
  }

  goRegistrarVehiculo() {
    this.router.navigate(['/cliente/vehiculos']);
  }
}
