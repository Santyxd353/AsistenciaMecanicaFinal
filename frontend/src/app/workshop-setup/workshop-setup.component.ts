import { AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize, timeout } from 'rxjs';

import {
  CreateTallerPayload,
  Taller,
  UpdateTallerPayload,
  WorkshopProfileService
} from '../core/workshop-profile.service';

type WorkshopDay =
  | 'Lunes'
  | 'Martes'
  | 'Miercoles'
  | 'Jueves'
  | 'Viernes'
  | 'Sabado'
  | 'Domingo';

interface ParsedWorkshopSchedule {
  generalDays: WorkshopDay[];
  generalStart: string;
  generalEnd: string;
  specialEnabled: boolean;
  specialDay: WorkshopDay;
  specialStart: string;
  specialEnd: string;
}

@Component({
  selector: 'app-workshop-setup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="shell">
      <section class="hero-card">
        <div class="hero-copy">
          <p class="eyebrow">Perfil de taller</p>
          <h1>{{ editMode ? 'Refina la presencia de tu taller' : 'Completa el perfil de tu taller' }}</h1>
          <p class="hero-text">
            {{ editMode
              ? 'Manten tu perfil comercial y operativo actualizado para que el panel muestre mejor tu capacidad, cobertura y contacto.'
              : 'Antes de entrar al panel, necesitamos los datos base del taller para habilitar tecnicos, solicitudes y estadisticas.' }}
          </p>
          <div class="hero-chips">
            <span class="chip">{{ editMode ? 'Modo edicion' : 'Primer registro' }}</span>
            <span class="chip chip-strong">{{ completionLabel }}</span>
          </div>
        </div>

        <aside class="hero-aside">
          <div class="status-card">
            <span class="status-label">Estado del perfil</span>
            <strong>{{ profileStatusTitle }}</strong>
            <p>{{ profileStatusDescription }}</p>
            <div class="progress-track" aria-hidden="true">
              <span class="progress-fill" [style.width.%]="completionPercent"></span>
            </div>
          </div>
        </aside>
      </section>

      <section class="workspace" *ngIf="!loading; else loadingTpl">
        <form [formGroup]="form" (ngSubmit)="save()" class="panel form-panel">
          <div class="section-head">
            <div>
              <p class="section-kicker">Paso principal</p>
              <h2>Informacion base</h2>
            </div>
            <p>Estos datos se usan para identificar y asignar correctamente el taller dentro de la plataforma.</p>
          </div>

          <div class="field-grid">
            <label [class.invalid]="showError('nombre_comercial')">
              <span>Nombre comercial</span>
              <input type="text" formControlName="nombre_comercial" placeholder="Taller El Rayo" />
              <small *ngIf="showError('nombre_comercial')">Ingresa el nombre comercial del taller.</small>
            </label>

            <label [class.invalid]="showError('telefono')">
              <span>Telefono</span>
              <input type="text" formControlName="telefono" placeholder="70000000" />
              <small *ngIf="showError('telefono')">Ingresa un telefono de contacto.</small>
            </label>

            <label class="full" [class.invalid]="showError('direccion')">
              <span>Direccion</span>
              <input type="text" formControlName="direccion" placeholder="Av. Principal #123" />
              <small *ngIf="showError('direccion')">La direccion ayuda a contextualizar el taller.</small>
            </label>

            <div class="full schedule-card" [class.invalid]="showError('horario_atencion')">
              <div class="schedule-card__head">
                <div>
                  <span>Horario de atencion</span>
                  <small>Marca los dias de atencion general y define un horario base.</small>
                </div>
              </div>

              <div class="schedule-block">
                <strong>Dias generales</strong>
                <div class="day-chip-grid">
                  <button
                    type="button"
                    class="day-chip"
                    *ngFor="let day of workshopDays"
                    [class.active]="selectedGeneralDays.includes(day)"
                    (click)="toggleGeneralDay(day)"
                  >
                    {{ day }}
                  </button>
                </div>
              </div>

              <div class="schedule-time-grid">
                <label>
                  <span>Apertura general</span>
                  <input type="time" [value]="generalStartTime" (input)="updateGeneralStart($any($event.target).value)" />
                </label>

                <label>
                  <span>Cierre general</span>
                  <input type="time" [value]="generalEndTime" (input)="updateGeneralEnd($any($event.target).value)" />
                </label>
              </div>

              <label class="special-toggle">
                <input type="checkbox" [checked]="specialScheduleEnabled" (change)="toggleSpecialSchedule($any($event.target).checked)" />
                <div>
                  <span>Agregar horario especial</span>
                  <small>Ejemplo: Domingo de 07:00 a 13:00.</small>
                </div>
              </label>

              <div class="schedule-time-grid" *ngIf="specialScheduleEnabled">
                <label>
                  <span>Dia especial</span>
                  <select [value]="specialDay" (change)="updateSpecialDay($any($event.target).value)">
                    <option *ngFor="let day of workshopDays" [value]="day">{{ day }}</option>
                  </select>
                </label>

                <label>
                  <span>Apertura especial</span>
                  <input type="time" [value]="specialStartTime" (input)="updateSpecialStart($any($event.target).value)" />
                </label>

                <label>
                  <span>Cierre especial</span>
                  <input type="time" [value]="specialEndTime" (input)="updateSpecialEnd($any($event.target).value)" />
                </label>
              </div>

              <small class="schedule-summary" *ngIf="scheduleSummary">{{ scheduleSummary }}</small>
              <small *ngIf="showError('horario_atencion')">Selecciona dias y horario general. Si activas horario especial, completa ese bloque tambien.</small>
            </div>

            <label [class.invalid]="showError('email_contacto')">
              <span>Email de contacto</span>
              <input type="email" formControlName="email_contacto" placeholder="contacto@taller.com" />
              <small *ngIf="showError('email_contacto')">Si lo llenas, debe tener un formato valido.</small>
            </label>
          </div>

          <div class="divider"></div>

          <div class="section-head">
            <div>
              <p class="section-kicker">Cobertura</p>
              <h2>Especialidad y presentacion</h2>
            </div>
            <p>Explica con claridad que tipo de emergencias o servicios cubre el taller.</p>
          </div>

          <div class="field-grid">
            <label class="full" [class.invalid]="showError('especialidades')">
              <span>Especialidades</span>
              <input type="text" formControlName="especialidades" placeholder="Mecanica general, baterias, grua" />
              <small *ngIf="showError('especialidades')">Agrega al menos una especialidad del taller.</small>
            </label>

            <label class="full">
              <span>Descripcion</span>
              <textarea formControlName="descripcion" rows="4" placeholder="Describe los servicios principales del taller."></textarea>
              <small>Un resumen breve mejora la lectura del perfil y el contexto operativo.</small>
            </label>

            <label>
              <span>Sitio web</span>
              <input type="text" formControlName="sitio_web" placeholder="https://taller.com" />
            </label>
          </div>

          <div class="divider"></div>

          <div class="section-head">
            <div>
              <p class="section-kicker">Ubicacion</p>
              <h2>Referencia geografica</h2>
            </div>
            <p>Ubica el taller en el mapa. Mueve el mapa hasta que el pin central quede sobre el punto exacto.</p>
          </div>

          <div class="map-card">
            <div class="map-toolbar">
              <div>
                <strong>Punto seleccionado</strong>
                <small>{{ locationSummary }}</small>
              </div>
              <button type="button" class="btn-secondary map-action" (click)="useCurrentLocation()">
                Usar ubicacion actual
              </button>
            </div>

            <div class="map-frame">
              <div #mapHost class="leaflet-map"></div>
              <div class="map-pin" aria-hidden="true">
                <span class="pin-head">+</span>
                <span class="pin-tail"></span>
              </div>
            </div>

            <small>{{ locationStatus }}</small>
          </div>

          <div class="divider" *ngIf="editMode"></div>

          <div class="section-head" *ngIf="editMode">
            <div>
              <p class="section-kicker">Operacion</p>
              <h2>Preferencias de notificacion</h2>
            </div>
            <p>Configura como quieres recibir avisos desde el sistema.</p>
          </div>

          <div class="toggles" *ngIf="editMode">
            <label class="toggle">
              <input type="checkbox" formControlName="notificaciones_nuevas_asignaciones" />
              <div>
                <span>Nuevas asignaciones</span>
                <small>Recibe alertas cuando lleguen servicios nuevos.</small>
              </div>
            </label>
            <label class="toggle">
              <input type="checkbox" formControlName="notificaciones_push" />
              <div>
                <span>Notificaciones push</span>
                <small>Canal rapido para eventos relevantes del panel.</small>
              </div>
            </label>
            <label class="toggle">
              <input type="checkbox" formControlName="notificaciones_recordatorios" />
              <div>
                <span>Recordatorios</span>
                <small>Avisos de tareas operativas pendientes.</small>
              </div>
            </label>
            <label class="toggle">
              <input type="checkbox" formControlName="notificaciones_pagos" />
              <div>
                <span>Pagos</span>
                <small>Seguimiento de cobros y comisiones.</small>
              </div>
            </label>
            <label class="toggle">
              <input type="checkbox" formControlName="reportes_semanales" />
              <div>
                <span>Reportes semanales</span>
                <small>Resumen periodico del rendimiento del taller.</small>
              </div>
            </label>
          </div>

          <div class="actions">
            <button type="button" class="btn-secondary" (click)="cancel()">
              {{ editMode ? 'Volver al panel' : 'Cancelar' }}
            </button>
            <button type="submit" class="btn-primary" [disabled]="form.invalid || saving">
              {{ saving ? 'Guardando...' : editMode ? 'Guardar cambios' : 'Crear taller' }}
            </button>
          </div>

          <p class="message success" *ngIf="successMessage">{{ successMessage }}</p>
          <p class="message error" *ngIf="errorMessage">{{ errorMessage }}</p>
        </form>

        <aside class="panel side-panel">
          <div class="preview-card">
            <p class="section-kicker">Vista previa</p>
            <h3>{{ form.value.nombre_comercial || 'Tu taller aparecera aqui' }}</h3>
            <p class="preview-text">
              {{ form.value.descripcion || 'Agrega una descripcion breve para que el perfil transmita confianza y claridad operativa.' }}
            </p>

            <div class="mini-list">
              <div>
                <span>Contacto</span>
                <strong>{{ form.value.telefono || 'Pendiente' }}</strong>
              </div>
              <div>
                <span>Horario</span>
                <strong>{{ scheduleSummary || 'Pendiente' }}</strong>
              </div>
              <div>
                <span>Direccion</span>
                <strong>{{ form.value.direccion || 'Pendiente' }}</strong>
              </div>
            </div>

            <div class="tag-list" *ngIf="specialtyTags.length; else noTags">
              <span class="tag" *ngFor="let tag of specialtyTags">{{ tag }}</span>
            </div>

            <ng-template #noTags>
              <p class="helper-note">Tus especialidades apareceran aqui separadas como etiquetas.</p>
            </ng-template>
          </div>

          <div class="tip-card">
            <p class="section-kicker">Checklist</p>
            <ul>
              <li [class.done]="!!form.value.nombre_comercial">Nombre comercial definido</li>
              <li [class.done]="!!form.value.direccion">Direccion registrada</li>
              <li [class.done]="!!scheduleSummary">Horario de atencion cargado</li>
              <li [class.done]="specialtyTags.length > 0">Especialidades identificadas</li>
              <li [class.done]="!!form.value.descripcion">Descripcion comercial anadida</li>
            </ul>
          </div>
        </aside>
      </section>

      <ng-template #loadingTpl>
        <section class="panel loading-panel">
          <p>{{ loadingMessage }}</p>
          <div class="loading-actions" *ngIf="loadingSlow">
            <button type="button" class="btn-secondary" (click)="retryLoad()">
              Reintentar
            </button>
            <button type="button" class="btn-primary" (click)="goToLogout()">
              Salir de esta sesion
            </button>
          </div>
        </section>
      </ng-template>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(218, 119, 30, 0.18), transparent 34%),
        linear-gradient(180deg, #f9efe2 0%, #f5f7fb 48%, #ffffff 100%);
      color: #1a1410;
    }

    h1,
    h2,
    h3 {
      font-family: inherit;
      font-weight: 800;
      letter-spacing: -0.02em;
    }

    .shell {
      max-width: 1240px;
      margin: 0 auto;
      padding: 36px 20px 48px;
    }

    .hero-card,
    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(290px, 0.75fr);
      gap: 18px;
    }

    .hero-card {
      margin-bottom: 18px;
      align-items: stretch;
    }

    .eyebrow {
      margin: 0 0 8px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 12px;
      color: #9a5b21;
      font-weight: 700;
    }

    .hero-copy,
    .hero-aside {
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid #eadcca;
      border-radius: 28px;
      box-shadow: 0 16px 42px rgba(64, 37, 18, 0.08);
    }

    .hero-copy {
      padding: 30px 30px 32px;
    }

    .hero-aside {
      padding: 22px;
      background:
        linear-gradient(180deg, rgba(255, 247, 235, 0.94) 0%, rgba(255, 255, 255, 0.96) 100%);
    }

    h1 {
      margin: 0 0 12px;
      font-size: 42px;
      line-height: 1.02;
    }

    .hero-text {
      margin: 0;
      color: #65584b;
      line-height: 1.6;
      font-size: 16px;
    }

    .hero-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
    }

    .chip {
      padding: 8px 12px;
      border-radius: 999px;
      background: #f7ede0;
      color: #6b4d35;
      font-size: 12px;
      font-weight: 700;
    }

    .chip-strong {
      background: #1f1712;
      color: #ffffff;
    }

    .status-card {
      display: flex;
      flex-direction: column;
      gap: 10px;
      height: 100%;
      justify-content: space-between;
    }

    .status-label {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: #98704f;
    }

    .status-card strong {
      font-size: 24px;
      line-height: 1.1;
    }

    .status-card p {
      margin: 0;
      color: #68584b;
      line-height: 1.6;
    }

    .progress-track {
      height: 12px;
      border-radius: 999px;
      background: #ead7bf;
      overflow: hidden;
    }

    .progress-fill {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #c65a16 0%, #e1922f 100%);
    }

    .panel {
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid #eadcca;
      border-radius: 28px;
      padding: 28px;
      box-shadow: 0 16px 42px rgba(64, 37, 18, 0.08);
    }

    .form-panel,
    .side-panel {
      align-self: start;
    }

    .section-head {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }

    .section-head h2 {
      margin: 4px 0 0;
      font-size: 24px;
    }

    .section-head p {
      max-width: 360px;
      margin: 0;
      color: #6b5b4d;
      line-height: 1.6;
      font-size: 14px;
    }

    .section-kicker {
      margin: 0;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: #a3632b;
    }

    .field-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    label,
    .schedule-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 13px;
      font-weight: 700;
      color: #44362a;
    }

    .full {
      grid-column: 1 / -1;
    }

    label.invalid span,
    .schedule-card.invalid > .schedule-card__head span {
      color: #9f241c;
    }

    input,
    textarea,
    select {
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #d9c9b3;
      border-radius: 16px;
      padding: 14px 15px;
      font: inherit;
      background: #fffdfa;
      color: #1a1410;
    }

    input:focus,
    textarea:focus,
    select:focus {
      outline: none;
      border-color: #cb6b1c;
      box-shadow: 0 0 0 3px rgba(203, 107, 28, 0.12);
    }

    textarea {
      resize: vertical;
      min-height: 110px;
    }

    label.invalid input,
    label.invalid textarea,
    label.invalid select,
    .schedule-card.invalid input,
    .schedule-card.invalid select {
      border-color: #d36a5d;
      box-shadow: 0 0 0 3px rgba(211, 106, 93, 0.11);
    }

    small {
      color: #7d6958;
      line-height: 1.4;
    }

    label.invalid small,
    .schedule-card.invalid small {
      color: #b13c31;
    }

    .schedule-card {
      padding: 16px;
      border: 1px solid #eadcca;
      border-radius: 20px;
      background: #fffaf5;
    }

    .schedule-card__head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }

    .schedule-block {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .day-chip-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .day-chip {
      border: 1px solid #e4d3c1;
      background: #ffffff;
      color: #624935;
      border-radius: 999px;
      padding: 10px 14px;
      font-weight: 700;
      cursor: pointer;
    }

    .day-chip.active {
      background: #1f1712;
      border-color: #1f1712;
      color: #ffffff;
    }

    .schedule-time-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .special-toggle {
      flex-direction: row;
      align-items: flex-start;
      gap: 12px;
      border: 1px solid #ecdcc8;
      border-radius: 16px;
      background: #fffefb;
      padding: 14px 16px;
      font-weight: 600;
    }

    .special-toggle input {
      width: auto;
      margin: 2px 0 0;
      box-shadow: none;
    }

    .special-toggle div {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .schedule-summary {
      font-weight: 600;
      color: #5e4d3e;
    }

    .map-card {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 16px;
      border: 1px solid #eadcca;
      border-radius: 20px;
      background: #fffaf5;
    }

    .map-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    .map-toolbar div {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .map-action {
      white-space: nowrap;
    }

    .map-frame {
      position: relative;
      display: block;
      border-radius: 18px;
      overflow: hidden;
      border: 1px solid #eadcca;
      min-height: 320px;
      background: #f2ede7;
    }

    .leaflet-map {
      display: block;
      width: 100%;
      height: 320px;
      min-height: 320px;
    }

    .map-pin {
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, calc(-100% + 14px));
      display: flex;
      flex-direction: column;
      align-items: center;
      pointer-events: none;
      z-index: 500;
    }

    .pin-head {
      width: 42px;
      height: 42px;
      border-radius: 999px;
      background: #c65a16;
      color: #ffffff;
      display: grid;
      place-items: center;
      font-size: 22px;
      font-weight: 900;
      box-shadow: 0 10px 24px rgba(28, 20, 14, 0.28);
    }

    .pin-tail {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: #1f1712;
      margin-top: 6px;
    }

    .divider {
      height: 1px;
      background: linear-gradient(90deg, #efe2d3 0%, rgba(239, 226, 211, 0.1) 100%);
      margin: 24px 0;
    }

    .toggles {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }

    .toggle {
      flex-direction: row;
      align-items: flex-start;
      gap: 12px;
      border: 1px solid #ecdcc8;
      border-radius: 16px;
      background: #fffaf5;
      padding: 14px 16px;
      font-weight: 600;
    }

    .toggle input {
      width: auto;
      margin: 0;
      margin-top: 3px;
      box-shadow: none;
    }

    .toggle div {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .toggle span {
      font-size: 14px;
      color: #2d2219;
    }

    .toggle small {
      font-size: 12px;
    }

    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 28px;
    }

    .btn-primary,
    .btn-secondary {
      border: none;
      border-radius: 999px;
      padding: 13px 20px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 0.15s ease, opacity 0.15s ease;
    }

    .btn-primary {
      background: #171411;
      color: #ffffff;
    }

    .btn-primary:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    .btn-secondary {
      background: #f4ebdf;
      color: #4d3d2f;
    }

    .btn-primary:hover:not(:disabled),
    .btn-secondary:hover,
    .day-chip:hover {
      transform: translateY(-1px);
    }

    .message {
      margin: 18px 0 0;
      font-size: 14px;
    }

    .message.success {
      color: #1e7b41;
    }

    .message.error {
      color: #b3261e;
    }

    .side-panel {
      display: flex;
      flex-direction: column;
      gap: 18px;
      padding: 0;
      border: none;
      background: transparent;
      box-shadow: none;
    }

    .preview-card,
    .tip-card {
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid #eadcca;
      border-radius: 24px;
      padding: 22px;
      box-shadow: 0 12px 34px rgba(64, 37, 18, 0.06);
    }

    .preview-card h3 {
      margin: 6px 0 8px;
      font-size: 24px;
      line-height: 1.15;
    }

    .preview-text {
      margin: 0 0 18px;
      color: #66574a;
      line-height: 1.6;
    }

    .mini-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 18px;
    }

    .mini-list div {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 12px 14px;
      border-radius: 16px;
      background: #fff8ef;
      border: 1px solid #efe2d3;
    }

    .mini-list span {
      color: #8b7058;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .mini-list strong {
      font-size: 14px;
      line-height: 1.4;
      color: #281e16;
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

    .helper-note {
      margin: 0;
      color: #786557;
      line-height: 1.6;
      font-size: 13px;
    }

    .tip-card ul {
      list-style: none;
      padding: 0;
      margin: 14px 0 0;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .tip-card li {
      padding: 12px 14px;
      border-radius: 14px;
      background: #fffaf4;
      border: 1px solid #efdfcd;
      color: #715c4a;
      font-weight: 600;
    }

    .tip-card li.done {
      background: #eef8f0;
      border-color: #cfe6d4;
      color: #29643a;
    }

    .loading-panel {
      text-align: center;
      color: #6b5c4f;
    }

    .loading-actions {
      display: flex;
      justify-content: center;
      gap: 12px;
      margin-top: 16px;
      flex-wrap: wrap;
    }

    @media (max-width: 1060px) {
      .hero-card,
      .workspace {
        grid-template-columns: 1fr;
      }

      .section-head {
        flex-direction: column;
      }

      .section-head p {
        max-width: none;
      }
    }

    @media (max-width: 840px) {
      h1 {
        font-size: 31px;
      }

      .field-grid,
      .schedule-time-grid {
        grid-template-columns: 1fr;
      }

      .map-toolbar {
        flex-direction: column;
        align-items: stretch;
      }

      .actions {
        flex-direction: column-reverse;
      }

      .hero-copy,
      .hero-aside,
      .panel,
      .preview-card,
      .tip-card {
        padding: 20px;
        border-radius: 22px;
      }
    }
  `]
})
export class WorkshopSetupComponent implements OnInit, AfterViewInit, OnDestroy {
  form: FormGroup;
  loading = true;
  loadingSlow = false;
  saving = false;
  editMode = false;
  initialLoadResolved = false;
  currentWorkshop: Taller | null = null;
  successMessage = '';
  errorMessage = '';
  loadingMessage = 'Cargando perfil del taller...';
  mapReady = false;
  locationStatus = 'Mueve el mapa hasta dejar el pin central sobre la ubicacion exacta del taller.';
  readonly workshopDays: WorkshopDay[] = [
    'Lunes',
    'Martes',
    'Miercoles',
    'Jueves',
    'Viernes',
    'Sabado',
    'Domingo'
  ];
  selectedGeneralDays: WorkshopDay[] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado'];
  generalStartTime = '08:00';
  generalEndTime = '18:00';
  specialScheduleEnabled = false;
  specialDay: WorkshopDay = 'Domingo';
  specialStartTime = '07:00';
  specialEndTime = '13:00';
  @ViewChild('mapHost')
  set mapHostRef(value: ElementRef<HTMLDivElement> | undefined) {
    this.mapHost = value;
    if (value) {
      setTimeout(() => {
        void this.initializeMap();
      }, 0);
    }
  }
  private mapHost?: ElementRef<HTMLDivElement>;
  private leafletModule: typeof import('leaflet') | null = null;
  private mapInstance: import('leaflet').Map | null = null;
  private mapResizeObserver: ResizeObserver | null = null;
  private slowLoadingTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly createRoutePath = 'crear-taller';

  constructor(
    private fb: FormBuilder,
    private workshopService: WorkshopProfileService,
    private route: ActivatedRoute,
    private router: Router
  ) {
    this.form = this.fb.group({
      nombre_comercial: ['', Validators.required],
      direccion: ['', Validators.required],
      telefono: ['', Validators.required],
      email_contacto: ['', Validators.email],
      horario_atencion: ['', Validators.required],
      especialidades: ['', Validators.required],
      descripcion: [''],
      sitio_web: [''],
      latitud: [null],
      longitud: [null],
      notificaciones_nuevas_asignaciones: [true],
      notificaciones_push: [true],
      notificaciones_recordatorios: [true],
      notificaciones_pagos: [true],
      reportes_semanales: [false]
    });
  }

  ngOnInit(): void {
    if (this.route.routeConfig?.path === this.createRoutePath) {
      this.prepareCreateMode();
      return;
    }

    this.loadWorkshop();
  }

  ngAfterViewInit(): void {
    void this.initializeMap();
  }

  ngOnDestroy(): void {
    this.clearSlowLoadingTimer();
    this.mapResizeObserver?.disconnect();
    this.mapResizeObserver = null;
    this.mapInstance?.remove();
    this.mapInstance = null;
  }

  get completionPercent(): number {
    const checks = [
      !!this.form.value.nombre_comercial,
      !!this.form.value.direccion,
      !!this.form.value.telefono,
      !!this.scheduleSummary,
      this.specialtyTags.length > 0,
      !!this.form.value.descripcion
    ];
    const completed = checks.filter(Boolean).length;
    return Math.round((completed / checks.length) * 100);
  }

  get completionLabel(): string {
    return `${this.completionPercent}% completo`;
  }

  get profileStatusTitle(): string {
    if (this.completionPercent === 100) {
      return 'Perfil listo para operar';
    }

    if (this.completionPercent >= 60) {
      return 'Perfil casi completo';
    }

    return 'Perfil en preparacion';
  }

  get profileStatusDescription(): string {
    if (this.editMode) {
      return 'Puedes seguir afinando tu presentacion comercial y tus preferencias operativas desde esta misma pantalla.';
    }

    return 'Completa la informacion esencial para habilitar correctamente el flujo de taller dentro del sistema.';
  }

  get specialtyTags(): string[] {
    const raw = (this.form.value.especialidades || '') as string;
    return raw
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 6);
  }

  get scheduleSummary(): string {
    return String(this.form.get('horario_atencion')?.value ?? '').trim();
  }

  get locationSummary(): string {
    const lat = this.normalizeNumber(this.form.get('latitud')?.value);
    const lng = this.normalizeNumber(this.form.get('longitud')?.value);
    if (lat == null || lng == null) {
      return 'Ubicacion pendiente';
    }
    return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
  }

  toggleGeneralDay(day: WorkshopDay): void {
    if (this.selectedGeneralDays.includes(day)) {
      this.selectedGeneralDays = this.selectedGeneralDays.filter((item) => item !== day);
    } else {
      this.selectedGeneralDays = [...this.selectedGeneralDays, day].sort(
        (left, right) => this.workshopDays.indexOf(left) - this.workshopDays.indexOf(right)
      );
    }
    this.syncScheduleControl();
  }

  updateGeneralStart(value: string): void {
    this.generalStartTime = value;
    this.syncScheduleControl();
  }

  updateGeneralEnd(value: string): void {
    this.generalEndTime = value;
    this.syncScheduleControl();
  }

  toggleSpecialSchedule(enabled: boolean): void {
    this.specialScheduleEnabled = enabled;
    this.syncScheduleControl();
  }

  updateSpecialDay(value: string): void {
    if (this.workshopDays.includes(value as WorkshopDay)) {
      this.specialDay = value as WorkshopDay;
      this.syncScheduleControl();
    }
  }

  updateSpecialStart(value: string): void {
    this.specialStartTime = value;
    this.syncScheduleControl();
  }

  updateSpecialEnd(value: string): void {
    this.specialEndTime = value;
    this.syncScheduleControl();
  }

  save(): void {
    this.syncScheduleControl(true);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const wasEditing = this.editMode;
    this.saving = true;
    this.successMessage = '';
    this.errorMessage = '';

    const request = this.editMode
      ? this.workshopService.updateMyWorkshop(this.buildUpdatePayload())
      : this.workshopService.createWorkshop(this.buildCreatePayload());

    request.pipe(
      timeout(10000),
      finalize(() => {
        this.saving = false;
      })
    ).subscribe({
      next: (taller) => {
        this.currentWorkshop = taller;
        this.editMode = true;
        this.applyWorkshopSchedule(taller.horario_atencion);
        this.successMessage = wasEditing
          ? 'Perfil del taller guardado correctamente.'
          : 'Taller creado correctamente.';
        void this.redirectToWorkshopDashboard();
      },
      error: (error) => {
        this.errorMessage = error?.error?.detail || 'No se pudo guardar la informacion del taller.';
      }
    });
  }

  cancel(): void {
    void this.router.navigate([this.editMode ? '/taller' : '/login']);
  }

  showError(controlName: string): boolean {
    const control = this.form.get(controlName);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  retryLoad(): void {
    this.loadWorkshop();
  }

  goToLogout(): void {
    void this.router.navigate(['/logout']);
  }

  async useCurrentLocation(): Promise<void> {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      this.locationStatus = 'El navegador no permite obtener tu ubicacion actual.';
      return;
    }

    this.locationStatus = 'Buscando ubicacion actual...';
    navigator.geolocation.getCurrentPosition(
      (position) => {
        this.setLocation(position.coords.latitude, position.coords.longitude, 16);
        this.locationStatus = 'Ubicacion actual cargada. Ajusta el mapa si necesitas mover el pin.';
      },
      () => {
        this.locationStatus = 'No se pudo obtener tu ubicacion actual. Puedes mover el mapa manualmente.';
      },
      { enableHighAccuracy: true, timeout: 12000 }
    );
  }

  private loadWorkshop(): void {
    this.clearSlowLoadingTimer();
    this.loading = true;
    this.loadingSlow = false;
    this.initialLoadResolved = false;
    this.editMode = false;
    this.currentWorkshop = null;
    this.loadingMessage = 'Cargando perfil del taller...';
    this.errorMessage = '';
    this.slowLoadingTimer = setTimeout(() => {
      this.loadingSlow = true;
      this.loadingMessage = 'La carga esta tardando mas de lo esperado.';
    }, 4000);

    this.workshopService.getMyWorkshop().pipe(
      timeout(10000),
      finalize(() => {
        this.clearSlowLoadingTimer();
        if (this.initialLoadResolved) {
          this.loading = false;
        }
      })
    ).subscribe({
      next: (taller) => {
        this.currentWorkshop = taller;
        this.editMode = true;
        this.form.patchValue(taller);
        this.applyWorkshopSchedule(taller.horario_atencion);
        this.updateMapFromForm();
        this.initialLoadResolved = true;
        this.loading = false;
      },
      error: (error) => {
        if (error.status === 404) {
          this.prepareCreateMode();
          return;
        }

        this.initialLoadResolved = true;
        this.loading = false;
        this.loadingSlow = true;
        this.loadingMessage = 'No se pudo cargar la informacion del taller.';
        this.errorMessage = 'No se pudo cargar la informacion del taller.';
      }
    });
  }

  private prepareCreateMode(): void {
    this.initialLoadResolved = true;
    this.loading = false;
    this.loadingSlow = false;
    this.editMode = false;
    this.currentWorkshop = null;
    this.loadingMessage = 'Listo para crear tu taller.';
    this.clearSlowLoadingTimer();
    this.form.reset({
      nombre_comercial: '',
      direccion: '',
      telefono: '',
      email_contacto: '',
      horario_atencion: '',
      especialidades: '',
      descripcion: '',
      sitio_web: '',
      latitud: null,
      longitud: null,
      notificaciones_nuevas_asignaciones: true,
      notificaciones_push: true,
      notificaciones_recordatorios: true,
      notificaciones_pagos: true,
      reportes_semanales: false
    });
    this.selectedGeneralDays = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado'];
    this.generalStartTime = '08:00';
    this.generalEndTime = '18:00';
    this.specialScheduleEnabled = false;
    this.specialDay = 'Domingo';
    this.specialStartTime = '07:00';
    this.specialEndTime = '13:00';
    this.form.patchValue({
      latitud: -16.5,
      longitud: -68.15,
    });
    this.syncScheduleControl();
    this.updateMapFromForm();
  }

  private buildCreatePayload(): CreateTallerPayload {
    const value = this.form.getRawValue();
    return {
      nombre_comercial: value.nombre_comercial,
      direccion: value.direccion,
      telefono: value.telefono,
      email_contacto: value.email_contacto || undefined,
      horario_atencion: value.horario_atencion,
      especialidades: value.especialidades,
      descripcion: value.descripcion || undefined,
      sitio_web: value.sitio_web || undefined,
      latitud: this.normalizeNumber(value.latitud),
      longitud: this.normalizeNumber(value.longitud)
    };
  }

  private buildUpdatePayload(): UpdateTallerPayload {
    const value = this.form.getRawValue();
    return {
      nombre_comercial: value.nombre_comercial,
      direccion: value.direccion,
      telefono: value.telefono,
      email_contacto: value.email_contacto || undefined,
      horario_atencion: value.horario_atencion,
      especialidades: value.especialidades,
      descripcion: value.descripcion || undefined,
      sitio_web: value.sitio_web || undefined,
      latitud: this.normalizeNumber(value.latitud),
      longitud: this.normalizeNumber(value.longitud),
      notificaciones_nuevas_asignaciones: value.notificaciones_nuevas_asignaciones,
      notificaciones_push: value.notificaciones_push,
      notificaciones_recordatorios: value.notificaciones_recordatorios,
      notificaciones_pagos: value.notificaciones_pagos,
      reportes_semanales: value.reportes_semanales
    };
  }

  private normalizeNumber(value: unknown): number | undefined {
    if (value === null || value === undefined || value === '') {
      return undefined;
    }

    return Number(value);
  }

  private async initializeMap(): Promise<void> {
    if (typeof window === 'undefined' || !this.mapHost || this.mapInstance) {
      return;
    }

    const leaflet = await import('leaflet');
    this.leafletModule = leaflet;
    const initialLat = this.normalizeNumber(this.form.get('latitud')?.value) ?? -16.5;
    const initialLng = this.normalizeNumber(this.form.get('longitud')?.value) ?? -68.15;

    const map = leaflet.map(this.mapHost.nativeElement, {
      zoomControl: true,
      attributionControl: true,
    }).setView([initialLat, initialLng], 15);

    leaflet
      .tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors',
      })
      .addTo(map);

    map.on('moveend', () => {
      const center = map.getCenter();
      this.setLocation(center.lat, center.lng);
      this.locationStatus = 'Pin actualizado desde el mapa.';
    });

    map.whenReady(() => {
      map.invalidateSize();
    });
    map.on('load', () => {
      map.invalidateSize();
    });

    this.mapInstance = map;
    this.mapReady = true;
    this.attachMapResizeObserver();
    setTimeout(() => map.invalidateSize(), 0);
    setTimeout(() => map.invalidateSize(), 200);
    setTimeout(() => map.invalidateSize(), 600);
  }

  private setLocation(lat: number, lng: number, zoom?: number): void {
    this.form.patchValue(
      {
        latitud: Number(lat.toFixed(6)),
        longitud: Number(lng.toFixed(6)),
      },
      { emitEvent: false }
    );

    if (zoom != null && this.mapInstance) {
      this.mapInstance.setView([lat, lng], zoom);
    }
  }

  private updateMapFromForm(): void {
    const lat = this.normalizeNumber(this.form.get('latitud')?.value);
    const lng = this.normalizeNumber(this.form.get('longitud')?.value);
    if (lat == null || lng == null || !this.mapInstance) {
      return;
    }
    this.mapInstance.setView([lat, lng], this.mapInstance.getZoom(), { animate: false });
    this.locationStatus = 'Ubicacion cargada desde el perfil del taller.';
    this.mapInstance.invalidateSize();
  }

  private attachMapResizeObserver(): void {
    if (typeof ResizeObserver === 'undefined' || !this.mapHost || !this.mapInstance) {
      return;
    }
    this.mapResizeObserver?.disconnect();
    this.mapResizeObserver = new ResizeObserver(() => {
      this.mapInstance?.invalidateSize();
    });
    this.mapResizeObserver.observe(this.mapHost.nativeElement);
    const parent = this.mapHost.nativeElement.parentElement;
    if (parent) {
      this.mapResizeObserver.observe(parent);
    }
  }

  private async redirectToWorkshopDashboard(): Promise<void> {
    const navigated = await this.router.navigate(['/taller'], { replaceUrl: true });
    if (!navigated && typeof window !== 'undefined') {
      window.location.assign('/taller');
    }
  }

  private syncScheduleControl(markTouched = false): void {
    const control = this.form.get('horario_atencion');
    if (!control) {
      return;
    }

    const generalValid =
      this.selectedGeneralDays.length > 0 &&
      this.isValidTime(this.generalStartTime) &&
      this.isValidTime(this.generalEndTime) &&
      this.generalStartTime < this.generalEndTime;

    const specialValid =
      !this.specialScheduleEnabled ||
      (
        this.isValidTime(this.specialStartTime) &&
        this.isValidTime(this.specialEndTime) &&
        this.specialStartTime < this.specialEndTime &&
        !!this.specialDay
      );

    if (markTouched) {
      control.markAsTouched();
    }

    if (!generalValid || !specialValid) {
      control.setValue('', { emitEvent: false });
      control.setErrors({ required: true });
      return;
    }

    control.setErrors(null);
    control.setValue(this.buildScheduleSummary(), { emitEvent: false });
    control.updateValueAndValidity({ emitEvent: false });
  }

  private buildScheduleSummary(): string {
    const generalDays = this.selectedGeneralDays.join(', ');
    const parts = [
      `Dias generales: ${generalDays}`,
      `Horario general: ${this.generalStartTime}-${this.generalEndTime}`
    ];

    if (this.specialScheduleEnabled) {
      parts.push(
        `Horario especial: ${this.specialDay} ${this.specialStartTime}-${this.specialEndTime}`
      );
    }

    return parts.join(' | ');
  }

  private applyWorkshopSchedule(raw: string | undefined): void {
    const parsed = this.parseWorkshopSchedule(raw);
    this.selectedGeneralDays = parsed.generalDays;
    this.generalStartTime = parsed.generalStart;
    this.generalEndTime = parsed.generalEnd;
    this.specialScheduleEnabled = parsed.specialEnabled;
    this.specialDay = parsed.specialDay;
    this.specialStartTime = parsed.specialStart;
    this.specialEndTime = parsed.specialEnd;
    this.syncScheduleControl();
  }

  private parseWorkshopSchedule(raw: string | undefined): ParsedWorkshopSchedule {
    const fallback: ParsedWorkshopSchedule = {
      generalDays: ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado'],
      generalStart: '08:00',
      generalEnd: '18:00',
      specialEnabled: false,
      specialDay: 'Domingo',
      specialStart: '07:00',
      specialEnd: '13:00'
    };

    const text = (raw ?? '').trim();
    if (!text) {
      return fallback;
    }

    const generalDaysMatch = text.match(/Dias generales:\s*([^|]+)/i);
    const generalTimeMatch = text.match(/Horario general:\s*(\d{2}:\d{2})-(\d{2}:\d{2})/i);
    const specialMatch = text.match(/Horario especial:\s*(Lunes|Martes|Miercoles|Jueves|Viernes|Sabado|Domingo)\s+(\d{2}:\d{2})-(\d{2}:\d{2})/i);

    const legacyRangeMatch = text.match(
      /(Lunes|Martes|Miercoles|Jueves|Viernes|Sabado|Domingo)\s+a\s+(Lunes|Martes|Miercoles|Jueves|Viernes|Sabado|Domingo).*?(\d{2}:\d{2}).*?(\d{2}:\d{2})/i
    );

    const legacySpecialMatch = text.match(
      /(Lunes|Martes|Miercoles|Jueves|Viernes|Sabado|Domingo)\s+de\s+(\d{2}:\d{2})\s+a\s+(\d{2}:\d{2})/i
    );

    const parsedGeneralDays = generalDaysMatch
      ? this.parseDayList(generalDaysMatch[1])
      : legacyRangeMatch
        ? this.expandDayRange(legacyRangeMatch[1] as WorkshopDay, legacyRangeMatch[2] as WorkshopDay)
        : this.parseDayList(text);

    const generalStart = generalTimeMatch?.[1] ?? legacyRangeMatch?.[3] ?? fallback.generalStart;
    const generalEnd = generalTimeMatch?.[2] ?? legacyRangeMatch?.[4] ?? fallback.generalEnd;

    let specialEnabled = false;
    let specialDay = fallback.specialDay;
    let specialStart = fallback.specialStart;
    let specialEnd = fallback.specialEnd;

    if (specialMatch) {
      specialEnabled = true;
      specialDay = this.normalizeDay(specialMatch[1]) ?? fallback.specialDay;
      specialStart = specialMatch[2];
      specialEnd = specialMatch[3];
    } else if (legacySpecialMatch && !legacyRangeMatch) {
      specialEnabled = true;
      specialDay = this.normalizeDay(legacySpecialMatch[1]) ?? fallback.specialDay;
      specialStart = legacySpecialMatch[2];
      specialEnd = legacySpecialMatch[3];
    }

    return {
      generalDays: parsedGeneralDays.length ? parsedGeneralDays : fallback.generalDays,
      generalStart,
      generalEnd,
      specialEnabled,
      specialDay,
      specialStart,
      specialEnd
    };
  }

  private parseDayList(value: string): WorkshopDay[] {
    const found = this.workshopDays.filter((day) => new RegExp(day, 'i').test(value));
    return found.length ? found : [];
  }

  private expandDayRange(start: WorkshopDay, end: WorkshopDay): WorkshopDay[] {
    const startIndex = this.workshopDays.indexOf(start);
    const endIndex = this.workshopDays.indexOf(end);
    if (startIndex === -1 || endIndex === -1 || startIndex > endIndex) {
      return [];
    }
    return this.workshopDays.slice(startIndex, endIndex + 1);
  }

  private normalizeDay(value: string | undefined): WorkshopDay | null {
    const match = this.workshopDays.find((day) => day.toLowerCase() === (value ?? '').toLowerCase());
    return match ?? null;
  }

  private isValidTime(value: string): boolean {
    return /^\d{2}:\d{2}$/.test(value);
  }

  private clearSlowLoadingTimer(): void {
    if (this.slowLoadingTimer) {
      clearTimeout(this.slowLoadingTimer);
      this.slowLoadingTimer = null;
    }
  }
}
