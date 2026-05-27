import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';

import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-login-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="login-page">
      <section class="panel">
        <a routerLink="/login" class="back">Volver</a>
        <p class="kicker">Administrativos</p>
        <h1>Login Administrador</h1>
        <p class="lead">Acceso para superadmin y administradores de taller.</p>

        <form (ngSubmit)="submit()" #form="ngForm">
          <label>Usuario
            <input name="username" [(ngModel)]="username" required autocomplete="username">
          </label>
          <label>Contrasena
            <input name="password" [(ngModel)]="password" required type="password" autocomplete="current-password">
          </label>
          <div class="error" *ngIf="error">{{ error }}</div>
          <button type="submit" [disabled]="loading || form.invalid">{{ loading ? 'Entrando...' : 'Entrar' }}</button>
        </form>

        <div class="links">
          <a routerLink="/planes">Crear taller nuevo</a>
          <a routerLink="/login/trabajadores">Login trabajadores</a>
        </div>
      </section>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;font-family:Inter,Segoe UI,Arial,sans-serif;color:#2f241d}
    .login-page{min-height:100vh;display:grid;place-items:center;padding:24px}
    .panel{width:min(460px,100%);background:#fff;border:1px solid #ead7c4;border-radius:18px;padding:28px;box-shadow:0 24px 60px rgba(86,52,28,.12)}
    .back,.links a{color:#8b5e34;text-decoration:none;font-weight:800}
    .kicker{margin:20px 0 6px;color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{margin:0;font-size:34px}.lead{color:#7a6554}
    form{display:grid;gap:14px;margin-top:22px} label{display:grid;gap:7px;font-weight:800}
    input{border:1px solid #ead7c4;border-radius:12px;padding:13px 14px;font:inherit}
    button{border:0;border-radius:8px;padding:14px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer}
    button:disabled{opacity:.6}.error{background:#fee2e2;color:#991b1b;border-radius:12px;padding:10px}
    .links{display:flex;justify-content:space-between;gap:12px;margin-top:18px;flex-wrap:wrap}
  `],
})
export class LoginAdminComponent {
  username = '';
  password = '';
  loading = false;
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  submit(): void {
    this.loading = true;
    this.error = '';
    this.auth.loginAdmin(this.username.trim(), this.password).subscribe({
      next: (response) => {
        this.loading = false;
        this.router.navigate([this.auth.getDefaultRouteForRole(response.role)]);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo iniciar sesion.';
      },
    });
  }
}


