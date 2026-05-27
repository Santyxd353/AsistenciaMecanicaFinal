import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { AuthService } from '../core/auth.service';

type UserAuthMode = 'login' | 'register';

@Component({
  selector: 'app-login-users',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="login-page">
      <section class="panel">
        <a routerLink="/login" class="back">Volver</a>
        <p class="kicker">Usuarios</p>
        <h1>{{ mode === 'login' ? 'Login Usuarios' : 'Crear usuario' }}</h1>
        <p class="lead">
          Acceso para clientes que reportan emergencias, registran vehiculos y eligen cotizaciones.
        </p>

        <div class="mode-switch">
          <button type="button" [class.active]="mode === 'login'" (click)="setMode('login')">Ingresar</button>
          <button type="button" [class.active]="mode === 'register'" (click)="setMode('register')">Registrarme</button>
        </div>

        <form (ngSubmit)="submit()" #form="ngForm">
          <label *ngIf="mode === 'register'">
            Nombre completo
            <input name="fullName" [(ngModel)]="fullName" required>
          </label>

          <label>
            Usuario
            <input name="username" [(ngModel)]="username" required autocomplete="username">
          </label>

          <label *ngIf="mode === 'register'">
            Email
            <input name="email" [(ngModel)]="email" required type="email" autocomplete="email">
          </label>

          <label>
            Contrasena
            <input name="password" [(ngModel)]="password" required minlength="6" type="password" autocomplete="current-password">
          </label>

          <div class="error" *ngIf="error">{{ error }}</div>

          <button type="submit" [disabled]="loading || form.invalid">
            {{
              loading
                ? (mode === 'login' ? 'Ingresando...' : 'Creando cuenta...')
                : (mode === 'login' ? 'Entrar como usuario' : 'Crear usuario y entrar')
            }}
          </button>
        </form>

        <div class="links">
          <a routerLink="/login/admin">Login Administrador</a>
          <a routerLink="/login/trabajadores">Login Trabajadores</a>
        </div>
      </section>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;font-family:Inter,Segoe UI,Arial,sans-serif;color:#2f241d}
    .login-page{min-height:100vh;display:grid;place-items:center;padding:24px}
    .panel{width:min(500px,100%);background:#fff;border:1px solid #ead7c4;border-radius:18px;padding:28px;box-shadow:0 24px 60px rgba(86,52,28,.12)}
    .back,.links a{color:#8b5e34;text-decoration:none;font-weight:800}
    .kicker{margin:20px 0 6px;color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{margin:0;font-size:34px}.lead{color:#7a6554;line-height:1.55}
    .mode-switch{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:18px 0;background:#fff8ef;border:1px solid #ead7c4;border-radius:10px;padding:6px}
    .mode-switch button{background:transparent;color:#6f5745;border:0;border-radius:8px;padding:10px;font-weight:900;cursor:pointer}
    .mode-switch button.active{background:#8b5e34;color:#fff}
    form,label{display:grid;gap:8px}form{gap:14px}input{border:1px solid #ead7c4;border-radius:8px;padding:13px;font:inherit;background:#fff}
    form>button{border:0;border-radius:8px;padding:14px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer}button:disabled{opacity:.6;cursor:not-allowed}
    .error{background:#fee2e2;color:#991b1b;border-radius:10px;padding:10px}
    .links{display:flex;justify-content:space-between;gap:12px;margin-top:18px;font-size:13px}
    @media(max-width:520px){.links{display:grid}.panel{padding:22px}}
  `],
})
export class LoginUsersComponent {
  mode: UserAuthMode = 'login';
  username = '';
  password = '';
  fullName = '';
  email = '';
  loading = false;
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  setMode(mode: UserAuthMode): void {
    this.mode = mode;
    this.error = '';
  }

  submit(): void {
    this.loading = true;
    this.error = '';

    const request = this.mode === 'login'
      ? this.auth.loginClient(this.username.trim(), this.password)
      : this.auth.registerClient({
          username: this.username.trim(),
          email: this.email.trim(),
          full_name: this.fullName.trim(),
          password: this.password,
        });

    request.subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/cliente']);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo iniciar sesion como usuario.';
      },
    });
  }
}
