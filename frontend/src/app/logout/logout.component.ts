import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-logout',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="logout-shell">
      <div class="logout-card">
        <p class="eyebrow">Cerrando sesión</p>
        <h1>Redirigiendo al acceso</h1>
        <p>Estamos limpiando la sesión actual para que puedas volver a entrar sin quedar atrapado en una pantalla intermedia.</p>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(218, 119, 30, 0.18), transparent 30%),
        linear-gradient(180deg, #f9efe2 0%, #f5f7fb 48%, #ffffff 100%);
      color: #1a1410;
    }

    .logout-shell {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .logout-card {
      max-width: 520px;
      padding: 28px;
      border-radius: 28px;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid #eadcca;
      box-shadow: 0 16px 42px rgba(64, 37, 18, 0.08);
      text-align: center;
    }

    .eyebrow {
      margin: 0 0 8px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 12px;
      color: #9a5b21;
      font-weight: 700;
    }

    h1 {
      margin: 0 0 12px;
      font-size: 34px;
      line-height: 1.08;
    }

    p:last-child {
      margin: 0;
      color: #66574a;
      line-height: 1.6;
    }
  `]
})
export class LogoutComponent implements OnInit {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
