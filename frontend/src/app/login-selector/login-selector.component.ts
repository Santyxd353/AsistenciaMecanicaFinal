import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-login-selector',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <main class="auth-home">
      <section class="hero">
        <p class="kicker">SaaS vehicular</p>
        <h1>Acceso a la plataforma</h1>
        <p>Elige el acceso correcto para administrar tu taller o atender emergencias como trabajador.</p>
      </section>

      <section class="cards">
        <button class="card user-card" type="button" (click)="go('/login/usuarios')">
          <span>Usuarios</span>
          <strong>Login Usuarios</strong>
          <p>Clientes que reportan emergencias, registran vehiculos y eligen talleres.</p>
        </button>

        <button class="card primary" type="button" (click)="go('/login/admin')">
          <span>Administrativos</span>
          <strong>Login Administrador</strong>
          <p>Superadmin y administradores de taller entran sin seleccionar taller.</p>
        </button>

        <button class="card" type="button" (click)="go('/login/trabajadores')">
          <span>Trabajadores</span>
          <strong>Login Trabajadores</strong>
          <p>Busca tu taller, selecciona tu empresa e ingresa con tu usuario.</p>
        </button>

        <button class="card accent" type="button" (click)="go('/planes')">
          <span>Nuevo taller</span>
          <strong>Crear cuenta SaaS</strong>
          <p>Compara planes, simula pago y registra tu taller.</p>
        </button>
      </section>
    </main>
  `,
  styles: [`
    :host { display:block; min-height:100vh; background:#f5efe7; color:#2f241d; font-family:Inter,Segoe UI,Arial,sans-serif; }
    .auth-home { min-height:100vh; display:grid; place-items:center; padding:32px; gap:24px; }
    .hero { max-width:880px; text-align:center; }
    .kicker { margin:0 0 8px; color:#8b5e34; font-size:12px; text-transform:uppercase; letter-spacing:.16em; font-weight:900; }
    h1 { margin:0; font-size:48px; letter-spacing:0; }
    p { color:#6f5745; line-height:1.6; }
    .cards { width:min(1240px,100%); display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
    .card { text-align:left; border:1px solid #ead7c4; background:#fff; border-radius:10px; padding:24px; cursor:pointer; min-height:220px; box-shadow:0 10px 24px rgba(86,52,28,.08); }
    .card:hover { transform:translateY(-2px); }
    .card span { display:inline-flex; padding:6px 10px; border-radius:999px; background:#f3e6d7; color:#8b5e34; font-weight:900; font-size:12px; }
    .card strong { display:block; margin:22px 0 10px; font-size:26px; }
    .card.primary { border-color:#8b5e34; box-shadow:0 12px 28px rgba(139,94,52,.18); }
    .card.accent { background:#fff; }
    .card.accent span { background:#ecfdf5; color:#166534; }
    @media (max-width:1050px){ .cards{grid-template-columns:repeat(2,1fr);} }
    @media (max-width:680px){ .cards{grid-template-columns:1fr;} h1{font-size:36px;} }
  `],
})
export class LoginSelectorComponent {
  constructor(private router: Router) {}
  go(path: string): void { this.router.navigate([path]); }
}


