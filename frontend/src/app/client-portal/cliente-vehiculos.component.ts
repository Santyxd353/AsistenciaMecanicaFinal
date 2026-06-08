import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize, timeout } from 'rxjs/operators';
import { AuthService } from '../core/auth.service';
import { Vehicle, VehiclePhotoPreview, VehicleRepairHistory, VehicleService } from '../core/vehicle.service';
import { ClienteNavbarComponent } from './cliente-navbar.component';

@Component({
  selector: 'app-cliente-vehiculos',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, ClienteNavbarComponent],
  template: `
    <div class="portal-shell">
      <app-cliente-navbar></app-cliente-navbar>

      <section class="page-heading">
        <h1>Mis vehículos</h1>
        <p class="lede">Registra los vehículos que usarás en tus solicitudes. La IA puede llenar los datos por foto.</p>
      </section>

      <section class="panel" *ngIf="vehicles.length">
        <p class="section-kicker">Registrados</p>
        <div class="vehicle-list">
          <article class="vehicle-hero" *ngFor="let v of vehicles">
            <div class="vehicle-thumb">&#128663;</div>
            <div class="vehicle-grid">
              <div><span>Placa</span><strong>{{ v.placa }}</strong></div>
              <div><span>Marca</span><strong>{{ v.marca }}</strong></div>
              <div><span>Modelo</span><strong>{{ v.modelo }}</strong></div>
              <div><span>Color</span><strong>{{ v.color || 'No definido' }}</strong></div>
            </div>
            <div class="vehicle-actions">
              <button class="btn-secondary" type="button" (click)="toggleHistory(v)">
                {{ historyOpenId === v.id ? 'Ocultar historial' : 'Ver historial' }}
              </button>
            </div>
            <div class="vehicle-history" *ngIf="historyOpenId === v.id">
              <p class="message" *ngIf="historyLoadingId === v.id">Cargando historial...</p>
              <p class="message error" *ngIf="historyError">{{ historyError }}</p>
              <p class="history-empty" *ngIf="historyLoadingId !== v.id && !historyError && !(histories[v.id]?.length)">
                Este vehiculo todavia no tiene reparaciones registradas.
              </p>
              <article class="history-item" *ngFor="let h of histories[v.id] || []">
                <div>
                  <strong>{{ h.titulo || 'Atencion mecanica' }}</strong>
                  <span>{{ h.fecha_servicio | date:'dd/MM/yyyy HH:mm' }}</span>
                </div>
                <p>{{ h.diagnostico || h.acciones_realizadas || 'Sin detalle tecnico.' }}</p>
                <small>
                  {{ h.taller_nombre || 'Taller no registrado' }}
                  <ng-container *ngIf="h.tecnico_nombre"> · {{ h.tecnico_nombre }}</ng-container>
                  <ng-container *ngIf="h.costo"> · Bs {{ h.costo | number:'1.2-2' }}</ng-container>
                  <ng-container *ngIf="h.estado_pago"> · {{ h.estado_pago }}</ng-container>
                </small>
              </article>
            </div>
          </article>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="section-kicker">Nuevo vehículo</p>
            <h2>Registrar vehículo</h2>
            <p>Sube fotos para que la IA detecte placa, marca, modelo, color y año.</p>
          </div>
        </div>

        <div class="ai-upload-box">
          <input type="file" accept="image/*" multiple (change)="handlePhotos($event)" />
          <div class="ai-actions">
            <span>{{ photoFiles.length }} foto(s) cargada(s)</span>
            <button class="btn-secondary" type="button" (click)="analyze()" [disabled]="!photoFiles.length || analyzing">
              {{ analyzing ? 'Analizando...' : 'Analizar con IA' }}
            </button>
          </div>
          <div class="preview-card" *ngIf="preview">
            <strong>Previsualización IA</strong>
            <ul class="ai-fields">
              <li><span>Placa</span>
                <strong *ngIf="preview.placa">{{ preview.placa }}</strong>
                <em *ngIf="!preview.placa">placa no identificada</em>
              </li>
              <li><span>Marca</span>
                <strong *ngIf="preview.marca">{{ preview.marca }}</strong>
                <em *ngIf="!preview.marca">marca no identificada</em>
              </li>
              <li><span>Modelo</span>
                <strong *ngIf="preview.modelo">{{ preview.modelo }}</strong>
                <em *ngIf="!preview.modelo">modelo no identificado</em>
              </li>
              <li><span>Color</span>
                <strong *ngIf="preview.color">{{ preview.color }}</strong>
                <em *ngIf="!preview.color">color no identificado</em>
              </li>
              <li><span>Año</span>
                <strong *ngIf="preview.anio">{{ preview.anio }}</strong>
                <em *ngIf="!preview.anio">año no identificado</em>
              </li>
            </ul>
            <small>Fuente: {{ preview.source }}. Revisa antes de guardar.</small>
          </div>
        </div>

        <form [formGroup]="form" (ngSubmit)="add()" class="form-layout">
          <label class="field"><span>Placa</span><input type="text" formControlName="placa" placeholder="1234ABC" /></label>
          <label class="field"><span>Marca</span><input type="text" formControlName="marca" placeholder="Toyota" /></label>
          <label class="field"><span>Modelo</span><input type="text" formControlName="modelo" placeholder="Corolla" /></label>
          <label class="field"><span>Color</span><input type="text" formControlName="color" placeholder="Blanco" /></label>
          <div class="panel-actions">
            <button class="btn-primary" type="submit" [disabled]="form.invalid || saving">
              {{ saving ? 'Registrando...' : 'Registrar vehículo' }}
            </button>
          </div>
        </form>

        <p class="message success" *ngIf="msg">{{ msg }}</p>
        <p class="message error" *ngIf="err">{{ err }}</p>
      </section>
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh;
      background: radial-gradient(circle at top left, rgba(214,149,82,0.16), transparent 28%),
        linear-gradient(180deg,#f8f2ea 0%, #f6f7fb 46%, #fff 100%);
      color:#18120e; font-family:"Segoe UI",sans-serif;}
    .portal-shell { max-width: 1100px; margin: 0 auto; padding: 28px 20px 44px; }
    .page-heading { padding: 6px 4px 22px; }
    h1 { margin: 0; font-size: clamp(2rem,3.5vw,3rem); }
    h2 { margin: 0; font-size: 1.6rem; }
    .lede { margin: 10px 0 0; color: #685a4b; }
    .section-kicker {
      margin: 0 0 6px; text-transform: uppercase; letter-spacing: 0.14em;
      font-size: 11px; font-weight: 800; color: #9a6133;
    }
    .panel {
      background: rgba(255,255,255,0.95); border: 1px solid #eadcca;
      border-radius: 22px; padding: 22px; margin-bottom: 18px;
      box-shadow: 0 18px 42px rgba(64,37,18,0.08);
    }
    .panel-head { margin-bottom: 14px; }
    .vehicle-list { display: grid; gap: 12px; }
    .vehicle-hero {
      display: grid; grid-template-columns: auto 1fr auto; gap: 16px; align-items: center;
      padding: 14px; background: #fdf6ec; border: 1px solid #eadcca; border-radius: 16px;
    }
    .vehicle-thumb {
      width: 90px; height: 64px; background: #d8c4a8; border-radius: 12px;
      display: flex; align-items: center; justify-content: center; font-size: 32px;
    }
    .vehicle-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 22px; flex: 1; }
    .vehicle-grid > div span {
      display: block; font-size: 10px; font-weight: 800; text-transform: uppercase;
      letter-spacing: 0.14em; color: #8a6647;
    }
    .vehicle-grid > div strong { font-size: 1rem; }
    .vehicle-actions { display: flex; justify-content: flex-end; }
    .vehicle-history {
      grid-column: 1 / -1; display: grid; gap: 10px; padding-top: 12px;
      border-top: 1px dashed #eadcca;
    }
    .history-empty { margin: 0; color: #8a6647; }
    .history-item {
      background: #fff; border: 1px solid #eadcca; border-radius: 14px;
      padding: 12px; box-shadow: 0 10px 22px rgba(64,37,18,0.06);
    }
    .history-item > div { display: flex; justify-content: space-between; gap: 10px; }
    .history-item > div span { color: #8a6647; font-size: 12px; }
    .history-item p { margin: 8px 0; color: #4f3b2a; }
    .history-item small { color: #8a6647; }
    .ai-upload-box {
      padding: 16px; background: #fff8ef; border: 1px dashed #c19a6a;
      border-radius: 14px; margin-bottom: 14px;
    }
    .ai-actions { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 10px 0; }
    .preview-card { background: #fff; border-radius: 12px; padding: 12px; margin-top: 10px; }
    .ai-fields { list-style: none; padding: 0; margin: 8px 0; }
    .ai-fields li { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dashed #eadcca; }
    .ai-fields li span { font-size: 11px; color: #8a6647; text-transform: uppercase; letter-spacing: 0.12em; }
    .ai-fields li em { color: #b87333; font-style: italic; }
    .form-layout { display: grid; grid-template-columns: repeat(2,1fr); gap: 12px; }
    .field { display: flex; flex-direction: column; gap: 6px; }
    .field span { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.14em; color: #8a6647; }
    .field input { padding: 10px 12px; border-radius: 10px; border: 1px solid #eadcca; }
    .panel-actions { grid-column: 1 / -1; }
    .btn-primary {
      padding: 12px 22px; border-radius: 12px;
      background: linear-gradient(180deg,#b5651d 0%,#8a4a16 100%);
      color: #fff8ef; border: none; font-weight: 800; cursor: pointer;
    }
    .btn-secondary {
      background: #fff8ef; border: 1px solid #c19a6a; color: #5a3a22;
      padding: 8px 14px; border-radius: 10px; cursor: pointer; font-weight: 700;
    }
    .btn-primary:disabled, .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
    .message { margin-top: 10px; font-size: 13px; }
    .message.success { color: #2e7d32; }
    .message.error { color: #c62828; }
  `]
})
export class ClienteVehiculosComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly vehicleService = inject(VehicleService);
  private readonly router = inject(Router);

  form: FormGroup;
  vehicles: Vehicle[] = [];
  histories: Record<number, VehicleRepairHistory[]> = {};
  historyOpenId: number | null = null;
  historyLoadingId: number | null = null;
  historyError = '';
  photoFiles: File[] = [];
  preview: VehiclePhotoPreview | null = null;
  analyzing = false;
  saving = false;
  msg = '';
  err = '';

  constructor() {
    this.form = this.fb.group({
      placa: ['', Validators.required],
      marca: ['', Validators.required],
      modelo: ['', Validators.required],
      color: [''],
    });
  }

  ngOnInit(): void {
    if (!this.auth.isLoggedIn()) { this.router.navigate(['/login']); return; }
    this.reload();
  }

  reload(): void {
    this.vehicleService.getVehicles().pipe(timeout(10000)).subscribe({
      next: (v) => { this.vehicles = v; },
      error: () => { this.err = 'No se pudieron cargar tus vehículos.'; },
    });
  }

  toggleHistory(vehicle: Vehicle): void {
    if (this.historyOpenId === vehicle.id) {
      this.historyOpenId = null;
      this.historyError = '';
      return;
    }
    this.historyOpenId = vehicle.id;
    this.historyError = '';
    if (this.histories[vehicle.id]) {
      return;
    }
    this.historyLoadingId = vehicle.id;
    this.vehicleService.getVehicleHistory(vehicle.id).pipe(timeout(10000)).subscribe({
      next: (items) => {
        this.histories[vehicle.id] = Array.isArray(items) ? items : [];
        this.historyLoadingId = null;
      },
      error: (error) => {
        this.historyError = error?.error?.detail || 'No se pudo cargar el historial.';
        this.historyLoadingId = null;
      },
    });
  }

  handlePhotos(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.photoFiles = Array.from(input.files ?? []).slice(0, 4);
    this.preview = null;
    this.err = '';
  }

  analyze(): void {
    if (!this.photoFiles.length) return;
    this.analyzing = true;
    this.err = '';
    this.vehicleService.previewVehicleFromPhotos(this.photoFiles).pipe(
      timeout(45000),
      finalize(() => { this.analyzing = false; }),
    ).subscribe({
      next: (p) => {
        this.preview = p;
        this.form.patchValue({
          placa: p.placa || this.form.value.placa,
          marca: p.marca || this.form.value.marca,
          modelo: p.modelo || this.form.value.modelo,
          color: p.color || this.form.value.color,
        });
        this.msg = 'IA completó el preview. Revisa antes de guardar.';
      },
      error: (error) => { this.err = error?.error?.detail || 'La IA no pudo analizar las fotos.'; },
    });
  }

  add(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving = true;
    this.err = '';
    this.msg = '';
    this.vehicleService.createVehicle(this.form.value).pipe(timeout(10000)).subscribe({
      next: () => {
        this.saving = false;
        this.msg = 'Vehículo registrado.';
        this.form.reset();
        this.preview = null;
        this.photoFiles = [];
        this.reload();
      },
      error: (error) => {
        this.saving = false;
        this.err = error?.error?.detail || 'No se pudo registrar.';
      },
    });
  }
}
