import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { AuthService } from '../core/auth.service';
import { PublicWorkshop, PublicWorkshopsService } from '../core/public-workshops.service';

@Component({
  selector: 'app-login-workers',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="worker-page">
      <section class="panel">
        <a routerLink="/login" class="back">Volver</a>
        <p class="kicker">Trabajadores</p>
        <h1>Login Trabajadores</h1>
        <p class="lead">Busca tu taller, seleccionalo e ingresa con tus credenciales.</p>

        <label>Buscar taller
          <input name="query" [(ngModel)]="query" (ngModelChange)="search()" placeholder="Nombre del taller">
        </label>
        <div class="results" *ngIf="results.length">
          <button type="button" *ngFor="let item of results" (click)="select(item)" [class.active]="selected?.id === item.id">
            <strong>{{ item.nombre_comercial }}</strong>
            <span>{{ item.direccion }}</span>
          </button>
        </div>

        <form (ngSubmit)="submit()" #form="ngForm">
          <div class="selected" *ngIf="selected">Taller seleccionado: <strong>{{ selected.nombre_comercial }}</strong></div>
          <label>Usuario
            <input name="username" [(ngModel)]="username" required [disabled]="!selected">
          </label>
          <label>Contrasena
            <input name="password" [(ngModel)]="password" required type="password" [disabled]="!selected">
          </label>
          <div class="error" *ngIf="error">{{ error }}</div>
          <button type="submit" [disabled]="loading || form.invalid || !selected">{{ loading ? 'Entrando...' : 'Entrar a trabajar' }}</button>
        </form>

        <a routerLink="/login/admin" class="admin-link">Login Administrador</a>
      </section>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;font-family:Inter,Segoe UI,Arial,sans-serif;color:#2f241d}
    .worker-page{min-height:100vh;display:grid;place-items:center;padding:24px}
    .panel{width:min(560px,100%);background:#fff;border:1px solid #ead7c4;border-radius:18px;padding:28px;box-shadow:0 24px 60px rgba(86,52,28,.12)}
    .back,.admin-link{color:#8b5e34;text-decoration:none;font-weight:800}
    .kicker{margin:20px 0 6px;color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{margin:0;font-size:34px}.lead{color:#7a6554}
    label,form{display:grid;gap:8px;font-weight:800} form{margin-top:18px;gap:14px}
    input{border:1px solid #ead7c4;border-radius:12px;padding:13px 14px;font:inherit}
    .results{display:grid;gap:8px;margin:12px 0 18px}.results button{text-align:left;background:#fff8ef;color:#2f241d;border:1px solid #ead7c4;border-radius:8px;padding:12px;cursor:pointer}
    .results button.active{background:#f3e6d7;color:#8b5e34;border-color:#8b5e34}.results span{display:block;color:#7a6554;font-size:13px;margin-top:4px}.results button.active span{color:#6f5745}
    .selected{background:#f3e6d7;border:1px solid #e4c9ae;border-radius:8px;padding:10px;color:#8b5e34}
    form button{border:0;border-radius:8px;padding:14px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer}
    button:disabled{opacity:.6}.error{background:#fee2e2;color:#991b1b;border-radius:12px;padding:10px}.admin-link{display:inline-block;margin-top:18px}
  `],
})
export class LoginWorkersComponent {
  query = '';
  results: PublicWorkshop[] = [];
  selected: PublicWorkshop | null = null;
  username = '';
  password = '';
  loading = false;
  error = '';

  constructor(
    private publicWorkshops: PublicWorkshopsService,
    private auth: AuthService,
    private router: Router,
  ) {}

  search(): void {
    this.selected = null;
    this.error = '';
    const q = this.query.trim();
    if (q.length < 2) {
      this.results = [];
      return;
    }
    this.publicWorkshops.search(q).subscribe({
      next: (items) => this.results = items,
      error: () => this.results = [],
    });
  }

  select(item: PublicWorkshop): void {
    this.selected = item;
    this.results = [];
    this.query = item.nombre_comercial;
  }

  submit(): void {
    if (!this.selected) return;
    this.loading = true;
    this.error = '';
    this.auth.loginWorker(this.selected.id, this.username.trim(), this.password).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/tecnico']);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo iniciar sesion.';
      },
    });
  }
}


