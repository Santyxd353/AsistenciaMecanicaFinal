import { Component, OnInit, ChangeDetectorRef  } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize, timeout } from 'rxjs';

import {
  CreateTallerPayload,
  EspecialidadTaller,
  Taller,
  UpdateTallerPayload,
  WorkshopProfileService
} from '../core/workshop-profile.service';
import { WorkshopSpecialtyService } from '../core/workshop-specialty.service';

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
              ? 'Mantén tu perfil comercial y operativo actualizado para que el panel muestre mejor tu capacidad, cobertura y contacto.'
              : 'Antes de entrar al panel, necesitamos los datos base del taller para habilitar técnicos, solicitudes y estadísticas.' }}
          </p>
          <div class="hero-chips">
            <span class="chip">{{ editMode ? 'Modo edición' : 'Primer registro' }}</span>
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
              <h2>Información base</h2>
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
              <span>Teléfono</span>
              <input type="text" formControlName="telefono" placeholder="70000000" />
              <small *ngIf="showError('telefono')">Ingresa un teléfono de contacto.</small>
            </label>

            <label class="full" [class.invalid]="showError('direccion')">
              <span>Dirección</span>
              <input type="text" formControlName="direccion" placeholder="Av. Principal #123" />
              <small *ngIf="showError('direccion')">La dirección ayuda a contextualizar el taller.</small>
            </label>

            <label [class.invalid]="showError('horario_atencion')">
              <span>Horario de atención</span>
              <input type="text" formControlName="horario_atencion" placeholder="Lunes a Domingo 07:00 - 22:00" />
              <small *ngIf="showError('horario_atencion')">Indica cuándo puede responder el taller.</small>
            </label>

            <label [class.invalid]="showError('email_contacto')">
              <span>Email de contacto</span>
              <input type="email" formControlName="email_contacto" placeholder="contacto@taller.com" />
              <small *ngIf="showError('email_contacto')">Si lo llenas, debe tener un formato válido.</small>
            </label>
          </div>

          <div class="divider"></div>

          <div class="section-head">
            <div>
              <p class="section-kicker">Cobertura</p>
              <h2>Especialidad y presentación</h2>
            </div>
            <p>Explica con claridad qué tipo de emergencias o servicios cubre el taller.</p>
          </div>

          <div class="field-grid">
            <div class="full specialty-field" [class.invalid]="showError('especialidades')">
              <span>Especialidades</span>
              <div class="specialty-input-row">
                <select
                  [value]="selectedSpecialtyId"
                  (change)="handleSpecialtySelection($any($event.target).value)"
                >
                  <option value="">Selecciona una especialidad</option>
                  <option *ngFor="let specialty of availableSpecialties" [value]="specialty.id">
                    {{ specialty.nombre }}
                  </option>
                  <option value="__new__">+ Crear nueva especialidad</option>
                </select>
                <button type="button" class="btn-secondary specialty-add-btn" (click)="addSelectedSpecialty()">
                  Agregar
                </button>
              </div>
              <div class="specialty-input-row" *ngIf="showNewSpecialtyForm">
                <input
                  type="text"
                  [value]="newSpecialtyName"
                  (input)="newSpecialtyName = $any($event.target).value"
                  (keydown.enter)="handleSpecialtyEnter($event)"
                  placeholder="Ej. Mecánica general"
                />
                <button type="button" class="btn-secondary specialty-add-btn" (click)="createSpecialtyAndAdd()">
                  Crear y agregar
                </button>
              </div>
              <small *ngIf="specialtyErrorMessage">{{ specialtyErrorMessage }}</small>
              <div class="tag-list specialty-chip-list" *ngIf="specialtyTags.length; else noSpecialtiesSelected">
                <button
                  type="button"
                  class="tag tag-button"
                  *ngFor="let tag of specialtyTags"
                  (click)="removeSpecialty(tag.id)"
                >
                  {{ tag.nombre }} <span aria-hidden="true">×</span>
                </button>
              </div>
              <ng-template #noSpecialtiesSelected>
                <p class="helper-note">Selecciona una o varias especialidades del catálogo. Si no existe una, puedes crearla antes de agregarla.</p>
              </ng-template>
              <small *ngIf="showError('especialidades')">Agrega al menos una especialidad del taller.</small>
            </div>

            <label class="full">
              <span>Descripción</span>
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
              <p class="section-kicker">Ubicación</p>
              <h2>Referencia geográfica</h2>
            </div>
            <p>Estas coordenadas son opcionales, pero dejan preparado el taller para futuras reglas de asignación.</p>
          </div>

          <div class="field-grid">
            <label>
              <span>Latitud</span>
              <input type="number" formControlName="latitud" step="any" placeholder="-16.5" />
            </label>

            <label>
              <span>Longitud</span>
              <input type="number" formControlName="longitud" step="any" placeholder="-68.1" />
            </label>
          </div>

          <div class="divider" *ngIf="editMode"></div>

          <div class="section-head" *ngIf="editMode">
            <div>
              <p class="section-kicker">Operación</p>
              <h2>Preferencias de notificación</h2>
            </div>
            <p>Configura cómo quieres recibir avisos desde el sistema.</p>
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
                <small>Canal rápido para eventos relevantes del panel.</small>
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
                <small>Resumen periódico del rendimiento del taller.</small>
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
            <h3>{{ form.value.nombre_comercial || 'Tu taller aparecerá aquí' }}</h3>
            <p class="preview-text">
              {{ form.value.descripcion || 'Agrega una descripción breve para que el perfil transmita confianza y claridad operativa.' }}
            </p>

            <div class="mini-list">
              <div>
                <span>Contacto</span>
                <strong>{{ form.value.telefono || 'Pendiente' }}</strong>
              </div>
              <div>
                <span>Horario</span>
                <strong>{{ form.value.horario_atencion || 'Pendiente' }}</strong>
              </div>
              <div>
                <span>Dirección</span>
                <strong>{{ form.value.direccion || 'Pendiente' }}</strong>
              </div>
            </div>

            <div class="tag-list" *ngIf="specialtyTags.length; else noTags">
              <span class="tag" *ngFor="let tag of specialtyTags">{{ tag.nombre }}</span>
            </div>

            <ng-template #noTags>
              <p class="helper-note">Tus especialidades aparecerán aquí separadas como etiquetas.</p>
            </ng-template>
          </div>

          <div class="tip-card">
            <p class="section-kicker">Checklist</p>
            <ul>
              <li [class.done]="!!form.value.nombre_comercial">Nombre comercial definido</li>
              <li [class.done]="!!form.value.direccion">Dirección registrada</li>
              <li [class.done]="!!form.value.horario_atencion">Horario de atención cargado</li>
              <li [class.done]="specialtyTags.length > 0">Especialidades identificadas</li>
              <li [class.done]="!!form.value.descripcion">Descripción comercial añadida</li>
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
              Salir de esta sesión
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

    label {
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

    .specialty-field {
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 13px;
      font-weight: 700;
      color: #44362a;
    }

    label.invalid span {
      color: #9f241c;
    }

    .specialty-field.invalid > span {
      color: #9f241c;
    }

    input,
    select,
    textarea {
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
    select:focus,
    textarea:focus {
      outline: none;
      border-color: #cb6b1c;
      box-shadow: 0 0 0 3px rgba(203, 107, 28, 0.12);
    }

    textarea {
      resize: vertical;
      min-height: 110px;
    }

    label.invalid input,
    label.invalid select,
    label.invalid textarea {
      border-color: #d36a5d;
      box-shadow: 0 0 0 3px rgba(211, 106, 93, 0.11);
    }

    .specialty-field.invalid input,
    .specialty-field.invalid select {
      border-color: #d36a5d;
      box-shadow: 0 0 0 3px rgba(211, 106, 93, 0.11);
    }

    small {
      color: #7d6958;
      line-height: 1.4;
    }

    label.invalid small {
      color: #b13c31;
    }

    .specialty-field.invalid small {
      color: #b13c31;
    }

    .specialty-input-row {
      display: flex;
      gap: 10px;
      align-items: center;
    }

    .specialty-add-btn {
      flex-shrink: 0;
      padding-inline: 18px;
    }

    .specialty-chip-list {
      margin-top: 4px;
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
    .btn-secondary:hover {
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

    .tag-button {
      border: none;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
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

      .field-grid {
        grid-template-columns: 1fr;
      }

      .actions {
        flex-direction: column-reverse;
      }

      .specialty-input-row {
        flex-direction: column;
        align-items: stretch;
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
export class WorkshopSetupComponent implements OnInit {
  form: FormGroup;
  loading = true;
  loadingSlow = false;
  saving = false;
  editMode = false;
  initialLoadResolved = false;
  currentWorkshop: Taller | null = null;
  successMessage = '';
  errorMessage = '';
  specialtyErrorMessage = '';
  loadingMessage = 'Cargando perfil del taller...';
  newSpecialtyName = '';
  selectedSpecialtyId = '';
  showNewSpecialtyForm = false;
  availableSpecialties: EspecialidadTaller[] = [];
  selectedSpecialties: EspecialidadTaller[] = [];
  private slowLoadingTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly createRoutePath = 'crear-taller';
  private readonly editRoutePath = 'taller/perfil'; 

  constructor(
    private fb: FormBuilder,
    private workshopService: WorkshopProfileService,
    private workshopSpecialtyService: WorkshopSpecialtyService,
    private route: ActivatedRoute,
    private router: Router,
    private cdr: ChangeDetectorRef 
  ) {
    this.form = this.fb.group({
      nombre_comercial: ['', Validators.required],
      direccion: ['', Validators.required],
      telefono: ['', Validators.required],
      email_contacto: ['', Validators.email],
      horario_atencion: ['', Validators.required],
      especialidades: [[], Validators.required],
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
    this.loadAvailableSpecialties();

    const currentPath = this.route.snapshot.url.map(segment => segment.path).join('/');
    
    if (currentPath === this.createRoutePath || this.route.routeConfig?.path === this.createRoutePath) {
      this.prepareCreateMode();
      return;
    }
    
    this.loadWorkshop();
  }

  get completionPercent(): number {
    const checks = [
      !!this.form.value.nombre_comercial,
      !!this.form.value.direccion,
      !!this.form.value.telefono,
      !!this.form.value.horario_atencion,
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

    return 'Perfil en preparación';
  }

  get profileStatusDescription(): string {
    if (this.editMode) {
      return 'Puedes seguir afinando tu presentación comercial y tus preferencias operativas desde esta misma pantalla.';
    }

    return 'Completa la información esencial para habilitar correctamente el flujo de taller dentro del sistema.';
  }

  get specialtyTags(): EspecialidadTaller[] {
    return this.selectedSpecialties.slice(0, 6);
  }

  handleSpecialtySelection(value: string): void {
    this.specialtyErrorMessage = '';

    if (value === '__new__') {
      this.showNewSpecialtyForm = true;
      this.selectedSpecialtyId = '';
      return;
    }

    this.showNewSpecialtyForm = false;
    this.newSpecialtyName = '';
    this.selectedSpecialtyId = value;
  }

  addSelectedSpecialty(): void {
    this.specialtyErrorMessage = '';
    const specialtyId = Number(this.selectedSpecialtyId);
    if (!specialtyId) {
      this.markSpecialtiesAsTouched();
      return;
    }

    const selectedSpecialty = this.availableSpecialties.find((specialty) => specialty.id === specialtyId);
    if (!selectedSpecialty) {
      this.specialtyErrorMessage = 'La especialidad seleccionada no está disponible.';
      return;
    }

    const alreadyExists = this.selectedSpecialties.some(
      (specialty) => specialty.id === selectedSpecialty.id
    );
    if (alreadyExists) {
      this.selectedSpecialtyId = '';
      return;
    }

    this.selectedSpecialties = [...this.selectedSpecialties, selectedSpecialty];
    this.selectedSpecialtyId = '';
    this.syncSpecialtiesControl();
  }

  createSpecialtyAndAdd(): void {
    this.specialtyErrorMessage = '';
    const normalizedName = this.normalizeSpecialtyName(this.newSpecialtyName);
    if (!normalizedName) {
      this.specialtyErrorMessage = 'Debes ingresar el nombre de la nueva especialidad.';
      return;
    }

    const alreadyExists = this.availableSpecialties.some(
      (specialty) => specialty.nombre.toLocaleLowerCase() === normalizedName.toLocaleLowerCase()
    );
    if (alreadyExists) {
      this.specialtyErrorMessage = 'La especialidad ya existe. Selecciónala de la lista.';
      return;
    }

    this.workshopSpecialtyService.createSpecialty(normalizedName).subscribe({
      next: (specialty) => {
        this.availableSpecialties = [...this.availableSpecialties, specialty]
          .sort((a, b) => a.nombre.localeCompare(b.nombre));
        this.selectedSpecialties = [...this.selectedSpecialties, specialty];
        this.showNewSpecialtyForm = false;
        this.selectedSpecialtyId = '';
        this.newSpecialtyName = '';
        this.syncSpecialtiesControl();
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.specialtyErrorMessage = error?.error?.detail || 'No se pudo crear la especialidad.';
      }
    });
  }

  removeSpecialty(id: number): void {
    this.selectedSpecialties = this.selectedSpecialties.filter((specialty) => specialty.id !== id);
    this.selectedSpecialtyId = '';
    this.newSpecialtyName = '';
    this.syncSpecialtiesControl();
    this.markSpecialtiesAsTouched();
  }

  handleSpecialtyEnter(event: Event): void {
    event.preventDefault();
    this.createSpecialtyAndAdd();
  }

  save(): void {
    this.syncSpecialtiesControl();

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const wasEditing = this.editMode;
    this.saving = true;
    this.successMessage = '';
    this.errorMessage = '';
    this.specialtyErrorMessage = '';

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
        this.extractSpecialtiesFromTaller(taller);
        this.editMode = true;
        this.successMessage = wasEditing
          ? 'Perfil del taller guardado correctamente.'
          : 'Taller creado correctamente.';
        this.router.navigate(['/taller']);
      },
      error: (error) => {
        this.errorMessage = error?.error?.detail || 'No se pudo guardar la información del taller.';
      }
    });
  }

  cancel(): void {
    this.router.navigate([this.editMode ? '/taller' : '/login']);
  }

  showError(controlName: string): boolean {
    const control = this.form.get(controlName);
    return !!control && control.invalid && (control.dirty || control.touched);
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
    this.specialtyErrorMessage = '';
    
    this.slowLoadingTimer = setTimeout(() => {
      this.loadingSlow = true;
      this.loadingMessage = 'La carga está tardando más de lo esperado.';
      this.cdr.detectChanges(); // Forzar detección de cambios
    }, 4000);

    this.workshopService.getMyWorkshop().subscribe({
      next: (taller) => {
        this.clearSlowLoadingTimer();
        this.currentWorkshop = taller;
        this.editMode = true;
        
        // Actualizar formulario
        this.form.patchValue({
          nombre_comercial: taller.nombre_comercial,
          direccion: taller.direccion,
          telefono: taller.telefono,
          email_contacto: taller.email_contacto || '',
          horario_atencion: taller.horario_atencion,
          especialidades: this.extractSpecialtiesFromTaller(taller),
          descripcion: taller.descripcion || '',
          sitio_web: taller.sitio_web || '',
          latitud: taller.latitud,
          longitud: taller.longitud,
          notificaciones_nuevas_asignaciones: taller.notificaciones_nuevas_asignaciones,
          notificaciones_push: taller.notificaciones_push,
          notificaciones_recordatorios: taller.notificaciones_recordatorios,
          notificaciones_pagos: taller.notificaciones_pagos,
          reportes_semanales: taller.reportes_semanales
        });
        
        this.initialLoadResolved = true;
        this.loading = false;

        this.cdr.detectChanges();
        
      },
      error: (error) => {
        this.clearSlowLoadingTimer();
        if (error.status === 404) {
          this.prepareCreateMode();
          this.cdr.detectChanges();
          return;
        }

        this.initialLoadResolved = true;
        this.loading = false;
        this.loadingSlow = true;
        this.loadingMessage = 'No se pudo cargar la información del taller.';
        this.errorMessage = 'No se pudo cargar la información del taller.';
        this.cdr.detectChanges();
      }
    });
  }

  retryLoad(): void {
    this.loadWorkshop();
  }

  goToLogout(): void {
    this.router.navigate(['/logout']);
  }

  private prepareCreateMode(): void {
    this.initialLoadResolved = true;
    this.loading = false;
    this.loadingSlow = false;
    this.editMode = false;
    this.currentWorkshop = null;
    this.specialtyErrorMessage = '';
    this.newSpecialtyName = '';
    this.selectedSpecialtyId = '';
    this.showNewSpecialtyForm = false;
    this.selectedSpecialties = [];
    this.loadingMessage = 'Listo para crear tu taller.';
    this.clearSlowLoadingTimer();
    this.form.reset({
      nombre_comercial: '',
      direccion: '',
      telefono: '',
      email_contacto: '',
      horario_atencion: '',
      especialidades: [],
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
  }

  private buildCreatePayload(): CreateTallerPayload {
    const value = this.form.getRawValue();
    return {
      nombre_comercial: value.nombre_comercial,
      direccion: value.direccion,
      telefono: value.telefono,
      email_contacto: value.email_contacto || undefined,
      horario_atencion: value.horario_atencion,
      especialidad_ids: this.selectedSpecialties.map((specialty) => specialty.id),
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
      especialidad_ids: this.selectedSpecialties.map((specialty) => specialty.id),
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

  private normalizeSpecialtyName(value: string): string {
    return value.trim().replace(/\s+/g, ' ');
  }

  private extractSpecialtiesFromTaller(taller: Taller): number[] {
    this.selectedSpecialties = taller.especialidades
      .map((item) => ({
        id: item.id,
        nombre: this.normalizeSpecialtyName(item.nombre)
      }))
      .filter((item) => !!item.nombre);

    return this.selectedSpecialties.map((item) => item.id);
  }

  private loadAvailableSpecialties(): void {
    this.workshopSpecialtyService.getSpecialties().subscribe({
      next: (specialties) => {
        this.availableSpecialties = specialties;
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.specialtyErrorMessage = error?.error?.detail || 'No se pudieron cargar las especialidades.';
        this.cdr.detectChanges();
      }
    });
  }

  private syncSpecialtiesControl(): void {
    this.form.get('especialidades')?.setValue(this.selectedSpecialties.map((specialty) => specialty.id));
    this.form.get('especialidades')?.updateValueAndValidity();
  }

  private markSpecialtiesAsTouched(): void {
    this.form.get('especialidades')?.markAsTouched();
    this.form.get('especialidades')?.updateValueAndValidity();
  }

  private clearSlowLoadingTimer(): void {
    if (this.slowLoadingTimer) {
      clearTimeout(this.slowLoadingTimer);
      this.slowLoadingTimer = null;
    }
  }
}
