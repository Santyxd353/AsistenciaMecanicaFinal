import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { CurrentSubscription, SubscriptionsService } from '../../core/subscriptions.service';
import { WorkshopAdmin, WorkshopAdminsService } from '../../core/workshop-admins.service';

@Component({
  selector: 'app-workshop-admins',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="admins">
      <header>
        <a routerLink="/taller">Volver</a>
        <p class="kicker">Administradores</p>
        <h1>Administradores del taller</h1>
        <p *ngIf="subscription">
          Plan {{ subscription.plan.nombre }}:
          {{ subscription.uso.administradores }}/{{ subscription.limites.administradores ?? 'ilimitados' }} administradores.
        </p>
      </header>

      <section class="layout">
        <article class="panel">
          <h2>Crear administrador</h2>
          <form (ngSubmit)="create()" #form="ngForm">
            <label>Nombre <input name="full" [(ngModel)]="payload.full_name" required></label>
            <label>Usuario <input name="username" [(ngModel)]="payload.username" required></label>
            <label>Email <input name="email" [(ngModel)]="payload.email" required type="email"></label>
            <label>Contrasena <input name="password" [(ngModel)]="payload.password" required minlength="6" type="password"></label>
            <div class="error" *ngIf="error">{{ error }}</div>
            <button [disabled]="loading || form.invalid">{{ loading ? 'Creando...' : 'Crear administrador' }}</button>
          </form>
        </article>

        <article class="panel">
          <h2>Equipo administrativo</h2>
          <div class="admin-row" *ngFor="let admin of admins">
            <div>
              <strong>{{ admin.full_name || admin.username }}</strong>
              <span>{{ admin.email }}</span>
            </div>
            <button type="button" (click)="deactivate(admin)" [disabled]="!admin.is_active">{{ admin.is_active ? 'Desactivar' : 'Inactivo' }}</button>
          </div>
        </article>
      </section>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;color:#2f241d;font-family:Inter,Segoe UI,Arial,sans-serif}
    .admins{max-width:1120px;margin:0 auto;padding:32px}a{color:#8b5e34;text-decoration:none;font-weight:900}.kicker{color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{margin:0;font-size:42px}.layout{display:grid;grid-template-columns:420px 1fr;gap:16px}.panel{background:#fff;border:1px solid #ead7c4;border-radius:18px;padding:22px;box-shadow:0 18px 45px rgba(86,52,28,.10)}
    form,label{display:grid;gap:8px}form{gap:12px}input{border:1px solid #ead7c4;border-radius:8px;padding:12px;font:inherit}button{border:0;border-radius:8px;padding:12px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer}button:disabled{opacity:.55}.error{background:#fee2e2;color:#991b1b;border-radius:12px;padding:10px}
    .admin-row{display:flex;justify-content:space-between;gap:12px;align-items:center;border-bottom:1px solid #ead7c4;padding:13px 0}.admin-row span{display:block;color:#7a6554;margin-top:3px}
    @media(max-width:900px){.layout{grid-template-columns:1fr}}
  `],
})
export class AdminsComponent implements OnInit {
  admins: WorkshopAdmin[] = [];
  subscription: CurrentSubscription | null = null;
  loading = false;
  error = '';
  payload = { username: '', email: '', full_name: '', password: '' };

  constructor(
    private adminsService: WorkshopAdminsService,
    private subscriptions: SubscriptionsService,
    private router: Router,
  ) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.adminsService.list().subscribe((items) => this.admins = items);
    this.subscriptions.getCurrent().subscribe((item) => this.subscription = item);
  }

  create(): void {
    this.loading = true;
    this.error = '';
    this.adminsService.create(this.payload).subscribe({
      next: () => {
        this.loading = false;
        this.payload = { username: '', email: '', full_name: '', password: '' };
        this.load();
      },
      error: (err) => {
        this.loading = false;
        const detail = err?.error?.detail;
        if (detail?.code === 'PLAN_LIMIT_ADMIN') {
          this.router.navigate(['/upgrade-plan'], { queryParams: { reason: 'admins' } });
          return;
        }
        this.error = detail?.message || detail || 'No se pudo crear el administrador.';
      },
    });
  }

  deactivate(admin: WorkshopAdmin): void {
    this.adminsService.deactivate(admin.id).subscribe({ next: () => this.load() });
  }
}


