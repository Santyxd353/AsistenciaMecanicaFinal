import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

import { AuthService } from '../core/auth.service';
import { PageTransitionService } from '../core/page-transition.service';
import { PublicWorkshop, PublicWorkshopsService } from '../core/public-workshops.service';

@Component({
  selector: 'app-login-workers',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="worker-page">
      <section class="panel">
        <button type="button" class="back" (click)="navigate('/login')">Volver</button>
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

        <button type="button" class="admin-link" (click)="navigate('/login/admin')">Login Administrador</button>
      </section>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;font-family:Inter,Segoe UI,Arial,sans-serif;color:#2f241d;animation:pageFade .42s ease both}
    .worker-page{min-height:100vh;display:grid;place-items:center;padding:24px}
    .panel{width:min(560px,100%);background:#fff;border:1px solid #ead7c4;border-radius:18px;padding:28px;box-shadow:0 24px 60px rgba(86,52,28,.12);animation:panelIn .5s cubic-bezier(.2,.8,.2,1) both}
    .back,.admin-link{color:#8b5e34;text-decoration:none;font-weight:800;background:transparent;border:0;padding:0;cursor:pointer;font:inherit}
    .kicker{margin:20px 0 6px;color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{margin:0;font-size:34px}.lead{color:#7a6554}
    label,form{display:grid;gap:8px;font-weight:800} form{margin-top:18px;gap:14px}
    input{border:1px solid #ead7c4;border-radius:12px;padding:13px 14px;font:inherit;transition:border-color .2s ease,box-shadow .2s ease}
    input:focus{outline:0;border-color:#8b5e34;box-shadow:0 0 0 4px rgba(139,94,52,.12)}
    .results{display:grid;gap:8px;margin:12px 0 18px;animation:listIn .24s ease both}.results button{text-align:left;background:#fff8ef;color:#2f241d;border:1px solid #ead7c4;border-radius:8px;padding:12px;cursor:pointer;transition:transform .18s ease,border-color .18s ease,background .18s ease}
    .results button:hover{transform:translateX(4px);border-color:#8b5e34}
    .results button.active{background:#f3e6d7;color:#8b5e34;border-color:#8b5e34}.results span{display:block;color:#7a6554;font-size:13px;margin-top:4px}.results button.active span{color:#6f5745}
    .selected{background:#f3e6d7;border:1px solid #e4c9ae;border-radius:8px;padding:10px;color:#8b5e34}
    form button{border:0;border-radius:8px;padding:14px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer;transition:transform .2s ease,box-shadow .2s ease,background .2s ease}
    form button:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 16px 30px rgba(139,94,52,.22);background:#735038}
    button:disabled{opacity:.6}.error{background:#fee2e2;color:#991b1b;border-radius:12px;padding:10px;animation:shake .28s ease}.admin-link{display:inline-block;margin-top:18px}
    .back:hover,.admin-link:hover{text-decoration:underline}
    @keyframes pageFade{from{opacity:0}to{opacity:1}}
    @keyframes panelIn{from{opacity:0;transform:translateY(24px) scale(.98)}to{opacity:1;transform:translateY(0) scale(1)}}
    @keyframes listIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
    @keyframes shake{0%,100%{transform:translateX(0)}35%{transform:translateX(-5px)}70%{transform:translateX(5px)}}
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
    private pageTransition: PageTransitionService,
  ) {}

  navigate(path: string): void {
    this.pageTransition.navigate(path);
  }

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
        this.pageTransition.navigate('/tecnico');
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo iniciar sesión.';
      },
    });
  }
}


