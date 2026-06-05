import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { finalize, timeout } from 'rxjs';

import { AuthService } from '../core/auth.service';
import { PageTransitionService } from '../core/page-transition.service';

type UserAuthMode = 'login' | 'register';

@Component({
  selector: 'app-login-users',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="login-page">
      <section class="panel">
        <button type="button" class="back" (click)="navigate('/login')">Volver</button>
        <p class="kicker">Usuarios</p>
        <h1>{{ mode === 'login' ? 'Login Usuarios' : 'Crear usuario' }}</h1>
        <p class="lead">
          Acceso para clientes que reportan emergencias, registran vehículos y eligen cotizaciones.
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

          <label *ngIf="mode === 'register'">
            Usuario
            <input name="username" [(ngModel)]="username" required autocomplete="username">
          </label>

          <label>
            Correo
            <input name="email" [(ngModel)]="email" required type="email" autocomplete="email">
          </label>

          <label>
            Contraseña
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
          <button type="button" (click)="navigate('/login/admin')">Login Administrador</button>
          <button type="button" (click)="navigate('/login/trabajadores')">Login Trabajadores</button>
        </div>
      </section>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;font-family:Inter,Segoe UI,Arial,sans-serif;color:#2f241d;animation:pageFade .42s ease both}
    .login-page{min-height:100vh;display:grid;place-items:center;padding:24px}
    .panel{width:min(500px,100%);background:#fff;border:1px solid #ead7c4;border-radius:18px;padding:28px;box-shadow:0 24px 60px rgba(86,52,28,.12);animation:panelIn .5s cubic-bezier(.2,.8,.2,1) both}
    .back,.links button{color:#8b5e34;text-decoration:none;font-weight:800;background:transparent;border:0;padding:0;cursor:pointer;font:inherit}
    .kicker{margin:20px 0 6px;color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{margin:0;font-size:34px}.lead{color:#7a6554;line-height:1.55}
    .mode-switch{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:18px 0;background:#fff8ef;border:1px solid #ead7c4;border-radius:10px;padding:6px}
    .mode-switch button{background:transparent;color:#6f5745;border:0;border-radius:8px;padding:10px;font-weight:900;cursor:pointer;transition:background .2s ease,color .2s ease,transform .2s ease}
    .mode-switch button:hover{transform:translateY(-1px)}
    .mode-switch button.active{background:#8b5e34;color:#fff;box-shadow:0 10px 22px rgba(139,94,52,.18)}
    form,label{display:grid;gap:8px}form{gap:14px;animation:formSwap .25s ease both}input{border:1px solid #ead7c4;border-radius:8px;padding:13px;font:inherit;background:#fff;transition:border-color .2s ease,box-shadow .2s ease}
    input:focus{outline:0;border-color:#8b5e34;box-shadow:0 0 0 4px rgba(139,94,52,.12)}
    form>button{border:0;border-radius:8px;padding:14px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer;transition:transform .2s ease,box-shadow .2s ease,background .2s ease}
    form>button:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 16px 30px rgba(139,94,52,.22);background:#735038}
    button:disabled{opacity:.6;cursor:not-allowed}
    .error{background:#fee2e2;color:#991b1b;border-radius:10px;padding:10px;animation:shake .28s ease}
    .links{display:flex;justify-content:space-between;gap:12px;margin-top:18px;font-size:13px}
    .links button:hover,.back:hover{text-decoration:underline}
    @keyframes pageFade{from{opacity:0}to{opacity:1}}
    @keyframes panelIn{from{opacity:0;transform:translateY(24px) scale(.98)}to{opacity:1;transform:translateY(0) scale(1)}}
    @keyframes formSwap{from{opacity:.65;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
    @keyframes shake{0%,100%{transform:translateX(0)}35%{transform:translateX(-5px)}70%{transform:translateX(5px)}}
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
  private loginGuardTimer: ReturnType<typeof setTimeout> | null = null;
  private loginAttemptId = 0;

  constructor(
    private auth: AuthService,
    private pageTransition: PageTransitionService,
    private cdr: ChangeDetectorRef,
  ) {}

  navigate(path: string): void {
    this.pageTransition.navigate(path);
  }

  setMode(mode: UserAuthMode): void {
    this.mode = mode;
    this.error = '';
  }

  submit(): void {
    if (this.loading) {
      return;
    }

    this.loading = true;
    this.error = '';
    const attemptId = ++this.loginAttemptId;

    this.clearLoginGuardTimer();
    this.loginGuardTimer = setTimeout(() => {
      if (this.loading && this.loginAttemptId === attemptId) {
        this.loading = false;
        this.error = 'No se pudo validar el correo. Verifica tus datos o intenta nuevamente.';
        this.cdr.detectChanges();
      }
    }, 3000);

    const request = this.mode === 'login'
      ? this.auth.loginClient(this.email.trim().toLowerCase(), this.password)
      : this.auth.registerClient({
          username: this.username.trim(),
          email: this.email.trim(),
          full_name: this.fullName.trim(),
          password: this.password,
        });

    request.pipe(
      timeout(12000),
      finalize(() => {
        this.clearLoginGuardTimer();
        this.loading = false;
        this.cdr.detectChanges();
      }),
    ).subscribe({
      next: () => {
        this.pageTransition.navigate('/cliente');
      },
      error: (err) => {
        this.loading = false;
        this.error = this.normalizarErrorLogin(err);
        this.cdr.detectChanges();
      },
    });
  }

  private clearLoginGuardTimer(): void {
    if (this.loginGuardTimer) {
      clearTimeout(this.loginGuardTimer);
      this.loginGuardTimer = null;
    }
  }

  private normalizarErrorLogin(err: unknown): string {
    const response = err as { status?: number; error?: { detail?: string }; name?: string };

    if (response?.name === 'TimeoutError') {
      return 'El servidor tardó demasiado en responder. Intenta nuevamente.';
    }

    if (response?.status === 401) {
      return 'Correo o contraseña incorrectos.';
    }

    if (response?.status === 403) {
      return response?.error?.detail || 'Esta cuenta no puede entrar como usuario cliente.';
    }

    return response?.error?.detail || 'No se pudo iniciar sesión como usuario.';
  }
}
