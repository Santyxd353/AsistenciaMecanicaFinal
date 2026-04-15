import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize, timeout } from 'rxjs';

import { AuthService } from '../core/auth.service';
import { Vehicle, VehicleService } from '../core/vehicle.service';

@Component({
  selector: 'app-client-portal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="client-shell">
      <header class="topbar">
        <div>
          <p class="eyebrow">Portal del Cliente</p>
          <h1>{{ displayName }}</h1>
        </div>
        <button class="btn-ghost" (click)="logout()">Cerrar sesión</button>
      </header>

      <main class="grid">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>Mi perfil</h2>
              <p>Actualiza tus datos para usar la web y la app móvil con la misma cuenta.</p>
            </div>
          </div>

          <form [formGroup]="profileForm" (ngSubmit)="saveProfile()" class="stack">
            <label>
              <span>Nombre completo</span>
              <input type="text" formControlName="full_name" placeholder="Juan Perez" />
            </label>
            <label>
              <span>Usuario</span>
              <input type="text" formControlName="username" placeholder="juanperez" />
            </label>
            <label>
              <span>Correo</span>
              <input type="email" formControlName="email" placeholder="juan@mail.com" />
            </label>

            <div class="actions">
              <button class="btn-primary" type="submit" [disabled]="profileForm.invalid || savingProfile">
                {{ savingProfile ? 'Guardando...' : 'Guardar perfil' }}
              </button>
            </div>
          </form>

          <p class="message success" *ngIf="profileMessage">{{ profileMessage }}</p>
          <p class="message error" *ngIf="profileError">{{ profileError }}</p>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>Mis vehículos</h2>
              <p>Todo vehículo que registres aquí quedará disponible para los reportes del cliente.</p>
            </div>
            <span class="badge">{{ vehicles.length }} registrado(s)</span>
          </div>

          <form [formGroup]="vehicleForm" (ngSubmit)="addVehicle()" class="stack vehicle-form">
            <div class="row">
              <label>
                <span>Placa</span>
                <input type="text" formControlName="placa" placeholder="1234ABC" />
              </label>
              <label>
                <span>Marca</span>
                <input type="text" formControlName="marca" placeholder="Toyota" />
              </label>
            </div>
            <div class="row">
              <label>
                <span>Modelo</span>
                <input type="text" formControlName="modelo" placeholder="Corolla" />
              </label>
              <label>
                <span>Color</span>
                <input type="text" formControlName="color" placeholder="Blanco" />
              </label>
            </div>
            <div class="actions">
              <button class="btn-primary" type="submit" [disabled]="vehicleForm.invalid || savingVehicle">
                {{ savingVehicle ? 'Registrando...' : 'Registrar vehículo' }}
              </button>
            </div>
          </form>

          <p class="message success" *ngIf="vehicleMessage">{{ vehicleMessage }}</p>
          <p class="message error" *ngIf="vehicleError">{{ vehicleError }}</p>

          <div class="vehicle-list" *ngIf="vehicles.length; else emptyState">
            <article class="vehicle-card" *ngFor="let vehicle of vehicles">
              <div>
                <strong>{{ vehicle.placa }}</strong>
                <p>{{ vehicle.marca }} {{ vehicle.modelo }}</p>
              </div>
              <span>{{ vehicle.color || 'Sin color' }}</span>
            </article>
          </div>

          <ng-template #emptyState>
            <div class="empty-state">
              <p>No tienes vehículos registrados todavía.</p>
            </div>
          </ng-template>
        </section>
      </main>
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; background: linear-gradient(180deg, #f8f1e8 0%, #f6f7fb 45%, #ffffff 100%); color: #16110d; }
    .client-shell { max-width: 1180px; margin: 0 auto; padding: 28px 20px 40px; }
    .topbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 24px; }
    .eyebrow { margin: 0 0 6px; font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: #8b6e54; }
    h1 { margin: 0; font-size: 34px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    .panel { background: rgba(255,255,255,.88); border: 1px solid #eadfce; border-radius: 24px; padding: 24px; box-shadow: 0 10px 30px rgba(64,37,18,.06); }
    .panel-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
    .panel-head h2 { margin: 0 0 6px; font-size: 22px; }
    .panel-head p { margin: 0; color: #68584a; line-height: 1.45; }
    .badge { background: #fff1e3; color: #a04e10; border-radius: 999px; padding: 7px 12px; font-size: 12px; font-weight: 700; }
    .stack { display: flex; flex-direction: column; gap: 14px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; font-weight: 600; }
    input { border: 1px solid #dbcdb8; border-radius: 14px; padding: 13px 14px; font-size: 14px; background: #fffdfa; }
    input:focus { outline: none; border-color: #ca6419; box-shadow: 0 0 0 3px rgba(202,100,25,.12); }
    .actions { display: flex; justify-content: flex-start; }
    .btn-primary, .btn-ghost { border-radius: 999px; padding: 12px 18px; font-weight: 700; border: none; cursor: pointer; }
    .btn-primary { background: #171411; color: #fff; }
    .btn-primary:disabled { opacity: .55; cursor: not-allowed; }
    .btn-ghost { background: #fff; color: #171411; border: 1px solid #ddcfbc; }
    .message { margin: 14px 0 0; font-size: 13px; }
    .message.success { color: #1b7a42; }
    .message.error { color: #b3261e; }
    .vehicle-list { display: flex; flex-direction: column; gap: 10px; margin-top: 18px; }
    .vehicle-card { display: flex; justify-content: space-between; align-items: center; gap: 12px; border: 1px solid #f0e5d7; background: #fffaf5; border-radius: 16px; padding: 16px; }
    .vehicle-card strong { display: block; margin-bottom: 4px; font-size: 16px; }
    .vehicle-card p { margin: 0; color: #6b5a4b; }
    .empty-state { margin-top: 18px; border: 1px dashed #d8c8b4; border-radius: 18px; padding: 20px; color: #7b6d60; background: #fffdf9; }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      .row { grid-template-columns: 1fr; }
      .topbar { flex-direction: column; align-items: flex-start; }
    }
  `]
})
export class ClientPortalComponent implements OnInit {
  profileForm: FormGroup;
  vehicleForm: FormGroup;
  vehicles: Vehicle[] = [];
  savingProfile = false;
  savingVehicle = false;
  profileMessage = '';
  profileError = '';
  vehicleMessage = '';
  vehicleError = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private vehicleService: VehicleService,
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
  }

  get displayName(): string {
    return this.authService.getCurrentUser()?.full_name || 'Cliente';
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
  }

  loadProfile() {
    this.authService.getProfile().pipe(
      timeout(10000)
    ).subscribe({
      next: (user) => {
        this.profileForm.patchValue(user);
      },
      error: () => {
        this.profileError = 'No se pudo cargar tu perfil.';
      }
    });
  }

  loadVehicles() {
    this.vehicleService.getVehicles().pipe(
      timeout(10000)
    ).subscribe({
      next: (vehicles) => {
        this.vehicles = vehicles;
      },
      error: () => {
        this.vehicleError = 'No se pudieron cargar tus vehículos.';
      }
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
        this.vehicleForm.reset({ placa: '', marca: '', modelo: '', color: '' });
        this.vehicleMessage = 'Vehículo registrado correctamente.';
      },
      error: (error) => {
        this.vehicleError = error?.error?.detail || 'No se pudo registrar el vehículo.';
      }
    });
  }

  logout() {
    this.authService.logout();
  }
}
