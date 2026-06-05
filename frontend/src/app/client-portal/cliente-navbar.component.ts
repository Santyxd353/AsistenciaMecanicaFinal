import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-cliente-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  template: `
    <header class="navbar">
      <div class="navbar-brand">PORTAL CLIENTE</div>
      <nav class="navbar-links">
        <a class="nav-link" routerLink="/cliente" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }">Inicio</a>
        <a class="nav-link" routerLink="/cliente/vehiculos" routerLinkActive="active">Vehículos</a>
        <a class="nav-link" routerLink="/cliente/solicitudes" routerLinkActive="active">Solicitudes</a>
        <a class="nav-link" routerLink="/cliente/perfil" routerLinkActive="active">Perfil</a>
      </nav>
      <div class="navbar-user">
        <div class="user-chip">
          <span>Cuenta activa</span>
          <strong>{{ displayName }}</strong>
        </div>
        <button class="btn-logout" type="button" (click)="logout()">Cerrar sesión</button>
      </div>
    </header>
  `,
  styles: [`
    .navbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      background: #1a1410;
      color: #f4e6d3;
      border-radius: 14px;
      padding: 12px 20px;
      margin-bottom: 18px;
    }
    .navbar-brand { font-weight: 800; letter-spacing: 0.18em; font-size: 13px; }
    .navbar-links { display: flex; gap: 22px; flex: 1; justify-content: center; }
    .nav-link {
      color: #d8c4a8;
      text-decoration: none;
      font-size: 13px;
      cursor: pointer;
      letter-spacing: 0.02em;
    }
    .nav-link.active, .nav-link:hover { color: #fff8ef; }
    .navbar-user { display: flex; align-items: center; gap: 12px; }
    .user-chip { text-align: right; font-size: 12px; color: #c19a6a; }
    .user-chip strong { display: block; color: #fff8ef; font-size: 13px; }
    .btn-logout {
      background: transparent;
      border: 1px solid #5a3a22;
      color: #f4c58e;
      padding: 8px 14px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 0.04em;
    }
    .btn-logout:hover { background: #2a1d14; }
  `]
})
export class ClienteNavbarComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  get displayName(): string {
    return this.auth.getCurrentUser()?.full_name || 'Cliente';
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
