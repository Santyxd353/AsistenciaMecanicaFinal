import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { timeout } from 'rxjs/operators';
import { AuthService } from '../core/auth.service';
import { Vehicle, VehicleService } from '../core/vehicle.service';
import { ClienteNavbarComponent } from './cliente-navbar.component';

@Component({
  selector: 'app-cliente-perfil',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, ClienteNavbarComponent],
  template: `
    <div class="portal-shell">
      <app-cliente-navbar></app-cliente-navbar>

      <section class="page-heading">
        <h1>Mi perfil</h1>
        <p class="lede">Tus datos personales, foto, contacto y vehículos registrados.</p>
      </section>

      <div class="profile-grid">
        <section class="panel panel-photo">
          <p class="section-kicker">Foto de perfil</p>
          <div class="photo-wrapper">
            <img *ngIf="profileForm.value.foto_url" [src]="profileForm.value.foto_url" alt="foto perfil" />
            <div *ngIf="!profileForm.value.foto_url" class="photo-placeholder">&#128100;</div>
          </div>
          <label class="field field-wide">
            <span>URL de la foto</span>
            <input type="text" [formControl]="$any(profileForm.controls['foto_url'])" placeholder="https://..." />
          </label>
          <small>Pega la URL pública de tu foto.</small>
        </section>

        <section class="panel">
          <p class="section-kicker">Datos personales</p>
          <form [formGroup]="profileForm" (ngSubmit)="save()" class="form-layout">
            <label class="field field-wide">
              <span>Nombre completo</span>
              <input type="text" formControlName="full_name" placeholder="Juan Pérez" />
            </label>
            <label class="field">
              <span>Usuario</span>
              <input type="text" formControlName="username" />
            </label>
            <label class="field">
              <span>Correo</span>
              <input type="email" formControlName="email" />
            </label>
            <label class="field">
              <span>Teléfono</span>
              <input type="text" formControlName="telefono" placeholder="+591 70000000" />
            </label>
            <label class="field">
              <span>Contacto de emergencia</span>
              <input type="text" formControlName="contacto_emergencia" placeholder="+591 70000000" />
            </label>

            <div class="panel-actions">
              <button class="btn-primary" type="submit" [disabled]="profileForm.invalid || saving">
                {{ saving ? 'Guardando...' : 'Guardar perfil' }}
              </button>
            </div>
          </form>

          <p class="message success" *ngIf="msg">{{ msg }}</p>
          <p class="message error" *ngIf="err">{{ err }}</p>
        </section>
      </div>

      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="section-kicker">Vehículos</p>
            <h2>Autos registrados</h2>
            <p>{{ vehicles.length }} vehículo(s) asociado(s) a tu cuenta.</p>
          </div>
          <button class="btn-link" type="button" (click)="goVehiculos()">Gestionar</button>
        </div>

        <p class="empty" *ngIf="!vehicles.length">Aún no registraste vehículos. Ve a la pestaña "Vehículos".</p>

        <div class="vehicle-list" *ngIf="vehicles.length">
          <article class="vehicle-hero" *ngFor="let v of vehicles">
            <div class="vehicle-thumb">&#128663;</div>
            <div class="vehicle-grid">
              <div><span>Placa</span><strong>{{ v.placa }}</strong></div>
              <div><span>Marca</span><strong>{{ v.marca }}</strong></div>
              <div><span>Modelo</span><strong>{{ v.modelo }}</strong></div>
              <div><span>Color</span><strong>{{ v.color || 'No definido' }}</strong></div>
            </div>
          </article>
        </div>
      </section>
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
    .portal-shell { max-width: 1100px; margin: 0 auto; padding: 28px 20px 44px; }
    .page-heading { padding: 6px 4px 22px; }
    h1 { margin: 0; font-size: clamp(2rem, 3.5vw, 3rem); }
    h2 { margin: 0; font-size: 1.4rem; }
    .lede { margin: 10px 0 0; color: #685a4b; }
    .empty { padding: 10px 0; color: #685a4b; }
    .section-kicker {
      margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.14em;
      font-size: 11px; font-weight: 800; color: #9a6133;
    }
    .panel {
      background: rgba(255,255,255,0.95); border: 1px solid #eadcca;
      border-radius: 22px; padding: 22px; margin-bottom: 14px;
      box-shadow: 0 18px 42px rgba(64,37,18,0.08);
    }
    .panel-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
    .profile-grid { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 14px; margin-bottom: 14px; }
    .panel-photo { text-align: center; }
    .photo-wrapper {
      width: 140px; height: 140px; margin: 8px auto 14px;
      border-radius: 50%; overflow: hidden;
      background: #f4dbb9; display: flex; align-items: center; justify-content: center;
      border: 3px solid #d8c4a8;
    }
    .photo-wrapper img { width: 100%; height: 100%; object-fit: cover; }
    .photo-placeholder { font-size: 64px; opacity: 0.5; }
    .panel-photo small { color: #685a4b; font-size: 12px; }
    .form-layout { display: grid; grid-template-columns: repeat(2,1fr); gap: 12px; }
    .field { display: flex; flex-direction: column; gap: 6px; }
    .field-wide { grid-column: 1 / -1; }
    .field span { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.14em; color: #8a6647; }
    .field input { padding: 10px 12px; border-radius: 10px; border: 1px solid #eadcca; }
    .panel-actions { grid-column: 1 / -1; }
    .btn-primary {
      padding: 12px 22px; border-radius: 12px;
      background: linear-gradient(180deg,#b5651d 0%,#8a4a16 100%);
      color: #fff8ef; border: none; font-weight: 800; cursor: pointer;
    }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-link {
      background: transparent; border: 1px solid #c19a6a;
      color: #5a3a22; padding: 8px 14px; border-radius: 10px; cursor: pointer; font-weight: 700;
    }
    .vehicle-list { display: grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap: 12px; }
    .vehicle-hero {
      display: flex; gap: 14px; align-items: center;
      padding: 14px; background: #fdf6ec; border: 1px solid #eadcca; border-radius: 16px;
    }
    .vehicle-thumb {
      width: 70px; height: 56px; background: #d8c4a8; border-radius: 12px;
      display: flex; align-items: center; justify-content: center; font-size: 28px;
    }
    .vehicle-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px; flex: 1; }
    .vehicle-grid > div span { display: block; font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.14em; color: #8a6647; }
    .vehicle-grid > div strong { font-size: 0.9rem; }
    .message { margin-top: 10px; font-size: 13px; }
    .message.success { color: #2e7d32; }
    .message.error { color: #c62828; }
    @media (max-width: 880px) {
      .profile-grid { grid-template-columns: 1fr; }
    }
  `]
})
export class ClientePerfilComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly vehicleService = inject(VehicleService);

  profileForm: FormGroup;
  vehicles: Vehicle[] = [];
  saving = false;
  msg = '';
  err = '';

  constructor() {
    this.profileForm = this.fb.group({
      full_name: ['', Validators.required],
      username: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      telefono: [''],
      foto_url: [''],
      contacto_emergencia: [''],
    });
  }

  ngOnInit(): void {
    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }
    this.auth.getProfile().pipe(timeout(10000)).subscribe({
      next: (user) => this.profileForm.patchValue(user),
      error: () => { this.err = 'No se pudo cargar tu perfil.'; },
    });
    this.vehicleService.getVehicles().pipe(timeout(10000)).subscribe({
      next: (v) => { this.vehicles = v; },
      error: () => { /* sin vehículos */ },
    });
  }

  save(): void {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.err = '';
    this.msg = '';
    this.auth.updateProfile(this.profileForm.value).pipe(timeout(10000)).subscribe({
      next: () => {
        this.saving = false;
        this.msg = 'Perfil actualizado correctamente.';
      },
      error: (error) => {
        this.saving = false;
        this.err = error?.error?.detail || 'No se pudo guardar el perfil.';
      },
    });
  }

  goVehiculos(): void {
    this.router.navigate(['/cliente/vehiculos']);
  }
}
