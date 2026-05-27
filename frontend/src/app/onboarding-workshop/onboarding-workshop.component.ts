import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { AuthService } from '../core/auth.service';
import { OnboardingService } from '../core/onboarding.service';
import { WorkshopSpecialtyService } from '../core/workshop-specialty.service';
import { EspecialidadTaller } from '../core/workshop-profile.service';

@Component({
  selector: 'app-onboarding-workshop',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="onboarding">
      <header>
        <p class="kicker">Creacion de taller</p>
        <h1>Configura tu taller</h1>
        <p>Completa los datos administrativos y operativos para activar el panel.</p>
      </header>

      <form class="panel" (ngSubmit)="submit()" #form="ngForm">
        <section>
          <h2>Administrador principal</h2>
          <div class="grid">
            <label>Nombre completo <input name="fullName" [(ngModel)]="admin.full_name" required></label>
            <label>Usuario <input name="username" [(ngModel)]="admin.username" required></label>
            <label>Email <input name="email" [(ngModel)]="admin.email" required type="email"></label>
            <label>Contrasena <input name="password" [(ngModel)]="admin.password" required minlength="6" type="password"></label>
          </div>
        </section>

        <section>
          <h2>Datos del taller</h2>
          <div class="grid">
            <label>Nombre comercial <input name="nombre" [(ngModel)]="taller.nombre_comercial" required></label>
            <label>Telefono <input name="telefono" [(ngModel)]="taller.telefono" required></label>
            <label>Email contacto <input name="emailContacto" [(ngModel)]="taller.email_contacto" type="email"></label>
            <label>Horario <input name="horario" [(ngModel)]="taller.horario_atencion" required placeholder="Lunes a Sabado 08:00-18:00"></label>
            <label class="wide">Direccion <input name="direccion" [(ngModel)]="taller.direccion" required></label>
            <label class="wide">Descripcion <textarea name="descripcion" [(ngModel)]="taller.descripcion" rows="3"></textarea></label>
            <label>Latitud <input name="latitud" [(ngModel)]="taller.latitud" type="number" step="any"></label>
            <label>Longitud <input name="longitud" [(ngModel)]="taller.longitud" type="number" step="any"></label>
          </div>
        </section>

        <section>
          <h2>Especialidades</h2>
          <div class="specialties">
            <label *ngFor="let item of specialties">
              <input type="checkbox" [checked]="isSelected(item.id)" (change)="toggleSpecialty(item.id)">
              {{ item.nombre }}
            </label>
          </div>
        </section>

        <div class="error" *ngIf="error">{{ error }}</div>
        <button [disabled]="loading || form.invalid || !selectedSpecialtyIds.length">{{ loading ? 'Creando...' : 'Crear taller y entrar' }}</button>
      </form>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;color:#2f241d;font-family:Inter,Segoe UI,Arial,sans-serif}
    .onboarding{max-width:1100px;margin:0 auto;padding:32px} header{margin-bottom:18px}.kicker{color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{margin:0;font-size:44px} header p{color:#7a6554}.panel{background:#fff;border:1px solid #ead7c4;border-radius:18px;padding:26px;display:grid;gap:26px;box-shadow:0 20px 55px rgba(86,52,28,.10)}
    h2{margin:0 0 14px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.wide{grid-column:1/-1}
    label{display:grid;gap:7px;font-weight:800} input,textarea{border:1px solid #ead7c4;border-radius:12px;padding:13px;font:inherit}
    .specialties{display:flex;gap:10px;flex-wrap:wrap}.specialties label{display:flex;align-items:center;gap:8px;background:#fff8ef;border:1px solid #ead7c4;border-radius:999px;padding:9px 12px}
    button{border:0;border-radius:8px;padding:15px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer}.error{background:#fee2e2;color:#991b1b;border-radius:12px;padding:10px}
    @media(max-width:760px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}h1{font-size:34px}}
  `],
})
export class OnboardingWorkshopComponent implements OnInit {
  specialties: EspecialidadTaller[] = [];
  selectedSpecialtyIds: number[] = [];
  loading = false;
  error = '';
  admin = { username: '', email: '', full_name: '', password: '' };
  taller = {
    nombre_comercial: '',
    direccion: '',
    telefono: '',
    email_contacto: '',
    horario_atencion: 'Lunes a Sabado 08:00-18:00',
    descripcion: '',
    sitio_web: '',
    latitud: null as number | null,
    longitud: null as number | null,
  };

  constructor(
    private specialtiesService: WorkshopSpecialtyService,
    private onboarding: OnboardingService,
    private auth: AuthService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    if (!sessionStorage.getItem('onboarding_token')) {
      this.router.navigate(['/planes']);
      return;
    }
    this.specialtiesService.getSpecialties().subscribe((items) => this.specialties = items);
  }

  isSelected(id: number): boolean { return this.selectedSpecialtyIds.includes(id); }
  toggleSpecialty(id: number): void {
    this.selectedSpecialtyIds = this.isSelected(id)
      ? this.selectedSpecialtyIds.filter((item) => item !== id)
      : [...this.selectedSpecialtyIds, id];
  }

  submit(): void {
    const token = sessionStorage.getItem('onboarding_token');
    if (!token) return;
    this.loading = true;
    this.error = '';
    this.onboarding.createWorkshop({
      onboarding_token: token,
      admin: this.admin,
      taller: {
        ...this.taller,
        especialidad_ids: this.selectedSpecialtyIds,
      },
    }).subscribe({
      next: (response) => {
        sessionStorage.removeItem('onboarding_token');
        sessionStorage.removeItem('onboarding_plan');
        this.auth.persistExternalSession(response);
        this.router.navigate(['/taller']);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo crear el taller.';
      },
    });
  }
}


