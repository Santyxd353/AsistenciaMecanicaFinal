import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

import { PageTransitionService } from '../core/page-transition.service';

interface AccessCard {
  badge: string;
  title: string;
  description: string;
  detail: string;
  action: string;
  route: string;
  featured?: boolean;
}

interface FeatureItem {
  icon: string;
  title: string;
  text: string;
}

@Component({
  selector: 'app-login-selector',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <main class="home-shell">
      <section class="hero-panel">
        <header class="brand">
          <div class="brand-main">
            <span class="brand-mark">RS</span>
            <strong>RutaSOS</strong>
          </div>
          <p>Asistencia vehicular inteligente</p>
        </header>

        <div class="hero-content">
          <h1>Conecta conductores, talleres y mecánicos en tiempo real.</h1>
          <p>
            Pide ayuda cuando tu auto falla, recibe respuesta de talleres cercanos
            y sigue la llegada del mecánico desde un solo lugar.
          </p>

          <div class="hero-actions">
            <button type="button" class="primary-action" (click)="go('/planes')">
              Registrar mi taller
            </button>
            <button type="button" class="secondary-action" (click)="go('/login/admin')">
              Entrar como administrador
            </button>
          </div>
        </div>
      </section>

      <section class="features-bar" aria-label="Beneficios principales">
        <article class="feature-card" *ngFor="let item of features">
          <span class="feature-icon">{{ item.icon }}</span>
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.text }}</p>
          </div>
        </article>
      </section>

      <section class="access-section">
        <p class="section-kicker">Elige tu acceso</p>

        <div class="access-grid">
          <button
            type="button"
            class="access-card"
            *ngFor="let card of cards"
            [class.featured]="card.featured"
            (click)="go(card.route)"
          >
            <span class="access-badge">{{ card.badge }}</span>
            <h2>{{ card.title }}</h2>
            <p>{{ card.description }}</p>
            <small>{{ card.detail }}</small>
            <strong>{{ card.action }} <span aria-hidden="true">→</span></strong>
          </button>
        </div>
      </section>
    </main>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      color: #3d2b1f;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      background:
        linear-gradient(to bottom, #f1e4d4 0, #f1e4d4 560px, #fdf8f4 560px, #fdf8f4 100%);
      animation: loginHomeEnter .48s ease both;
    }

    .home-shell {
      width: min(1180px, 100%);
      min-height: 100vh;
      margin: 0 auto;
      padding: 30px 24px 72px;
    }

    .hero-panel {
      min-height: 540px;
      display: grid;
      justify-items: center;
      align-content: start;
      text-align: center;
    }

    .brand {
      display: grid;
      justify-items: center;
      gap: 3px;
      margin-bottom: 44px;
      animation: fadeDown .55s ease both;
    }

    .brand-main {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-size: 16px;
      font-weight: 900;
      color: #3d2b1f;
      letter-spacing: -0.02em;
    }

    .brand-mark {
      width: 20px;
      height: 20px;
      border-radius: 5px;
      display: grid;
      place-items: center;
      background: #735038;
      color: #fff8ef;
      font-size: 9px;
      font-weight: 950;
      letter-spacing: 0;
    }

    .brand p,
    .section-kicker {
      margin: 0;
      color: #735038;
      font-size: 10px;
      font-weight: 900;
      line-height: 1;
      text-transform: uppercase;
      letter-spacing: .18em;
    }

    .hero-content {
      max-width: 850px;
      animation: fadeUp .7s ease .08s both;
    }

    h1 {
      margin: 0;
      color: #1a0f0a;
      font-size: clamp(40px, 5vw, 58px);
      font-weight: 950;
      line-height: 1.08;
      letter-spacing: 0;
    }

    .hero-content p {
      width: min(660px, 100%);
      margin: 22px auto 0;
      color: #5c4a3d;
      font-size: 18px;
      line-height: 1.55;
    }

    .hero-actions {
      display: flex;
      justify-content: center;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
      margin-top: 40px;
    }

    button {
      font: inherit;
    }

    .primary-action,
    .secondary-action {
      min-height: 46px;
      border-radius: 999px;
      padding: 0 28px;
      font-size: 14px;
      font-weight: 850;
      cursor: pointer;
      transition: transform .22s ease, box-shadow .22s ease, background .22s ease, color .22s ease;
    }

    .primary-action {
      border: 0;
      background: #735038;
      color: #fff;
      box-shadow: 0 18px 34px -10px rgba(115, 80, 56, .58);
    }

    .secondary-action {
      border: 2px solid #3d2b1f;
      background: transparent;
      color: #3d2b1f;
    }

    .primary-action:hover,
    .secondary-action:hover {
      transform: translateY(-3px);
    }

    .primary-action:hover {
      background: #5c402d;
      box-shadow: 0 22px 42px -12px rgba(115, 80, 56, .68);
    }

    .secondary-action:hover {
      background: #3d2b1f;
      color: #fff8ef;
      box-shadow: 0 18px 34px -16px rgba(61, 43, 31, .42);
    }

    .features-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-top: 26px;
      animation: fadeUp .75s ease .16s both;
    }

    .feature-card {
      min-height: 74px;
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 14px 18px;
      border: 1px solid rgba(255, 255, 255, .7);
      border-radius: 24px;
      background: #fcf8f3;
      box-shadow: 0 14px 44px -18px rgba(61, 43, 31, .16);
      transition: transform .22s ease, box-shadow .22s ease;
    }

    .feature-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 20px 52px -22px rgba(61, 43, 31, .3);
    }

    .feature-icon {
      width: 42px;
      height: 42px;
      flex: 0 0 42px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: #f4e9dc;
      color: #735038;
      font-size: 18px;
      font-weight: 900;
    }

    .feature-card strong {
      display: block;
      color: #1a0f0a;
      font-size: 14px;
      font-weight: 900;
    }

    .feature-card p {
      margin: 3px 0 0;
      color: #5c4a3d;
      font-size: 12px;
      line-height: 1.25;
    }

    .access-section {
      padding-top: 84px;
      text-align: center;
    }

    .access-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 22px;
      margin-top: 30px;
    }

    .access-card {
      min-height: 320px;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      text-align: left;
      border: 1px solid rgba(255, 255, 255, .7);
      border-radius: 28px;
      background: #fcf8f3;
      padding: 32px;
      color: #3d2b1f;
      cursor: pointer;
      box-shadow: 0 18px 48px -22px rgba(61, 43, 31, .18);
      transition: transform .26s ease, box-shadow .26s ease, border-color .26s ease;
      animation: fadeUp .72s ease both;
    }

    .access-card:nth-child(1) { animation-delay: .05s; }
    .access-card:nth-child(2) { animation-delay: .12s; }
    .access-card:nth-child(3) { animation-delay: .19s; }
    .access-card:nth-child(4) { animation-delay: .26s; }

    .access-card.featured {
      box-shadow:
        0 0 90px 20px rgba(220, 150, 80, .16),
        0 18px 48px -22px rgba(61, 43, 31, .2);
    }

    .access-card:hover {
      transform: translateY(-8px);
      border-color: rgba(115, 80, 56, .28);
      box-shadow:
        0 28px 70px -26px rgba(61, 43, 31, .34),
        0 0 80px 10px rgba(220, 150, 80, .14);
    }

    .access-badge {
      width: 52px;
      height: 52px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: #735038;
      color: #fff;
      font-size: 12px;
      font-weight: 950;
      margin-bottom: 26px;
    }

    .access-card h2 {
      margin: 0 0 16px;
      color: #1a0f0a;
      font-size: 22px;
      line-height: 1.12;
      font-weight: 950;
      letter-spacing: 0;
    }

    .access-card p {
      margin: 0 0 18px;
      color: #7a6556;
      font-size: 14px;
      line-height: 1.65;
    }

    .access-card small {
      display: block;
      margin-bottom: auto;
      color: #8c7362;
      font-size: 12px;
      font-weight: 750;
      line-height: 1.45;
    }

    .access-card > strong {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      margin-top: 32px;
      color: #3d2b1f;
      font-size: 14px;
      font-weight: 900;
    }

    .access-card > strong span {
      transition: transform .22s ease;
    }

    .access-card:hover > strong span {
      transform: translateX(5px);
    }

    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(24px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes fadeDown {
      from { opacity: 0; transform: translateY(-12px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes loginHomeEnter {
      from { opacity: 0; transform: translateY(14px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 1050px) {
      .features-bar,
      .access-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    @media (max-width: 720px) {
      :host {
        background:
          linear-gradient(to bottom, #f1e4d4 0, #f1e4d4 600px, #fdf8f4 600px, #fdf8f4 100%);
      }

      .home-shell {
        padding: 24px 16px 52px;
      }

      .hero-panel {
        min-height: 570px;
      }

      h1 {
        font-size: 42px;
      }

      .hero-content p {
        font-size: 16px;
      }

      .features-bar,
      .access-grid {
        grid-template-columns: 1fr;
      }

      .access-section {
        padding-top: 56px;
      }

      .access-card {
        min-height: 260px;
      }
    }
  `],
})
export class LoginSelectorComponent {
  readonly features: FeatureItem[] = [
    { icon: '24', title: '24/7', text: 'atención disponible' },
    { icon: 'GPS', title: 'GPS', text: 'seguimiento en vivo' },
    { icon: 'IA', title: 'IA', text: 'apoyo para diagnóstico' },
    { icon: 'Bs', title: 'Planes', text: 'para cada taller' },
  ];

  readonly cards: AccessCard[] = [
    {
      badge: 'US',
      title: 'Login Usuarios',
      description: 'Para conductores que necesitan pedir ayuda, guardar sus vehículos y elegir un taller.',
      detail: 'Emergencias, vehículos, pagos de prueba y seguimiento.',
      action: 'Entrar como cliente',
      route: '/login/usuarios',
      featured: true,
    },
    {
      badge: 'AD',
      title: 'Login Administrador',
      description: 'Para dueños o encargados que administran talleres, solicitudes y personal.',
      detail: 'Talleres, solicitudes, pagos, trabajadores y reportes.',
      action: 'Ir al panel administrativo',
      route: '/login/admin',
    },
    {
      badge: 'ME',
      title: 'Login Trabajadores',
      description: 'Para mecánicos que reciben trabajos, actualizan su disponibilidad y atienden servicios.',
      detail: 'Trabajos asignados, llegada al cliente y cierre del servicio.',
      action: 'Entrar como trabajador',
      route: '/login/trabajadores',
    },
    {
      badge: 'GO',
      title: 'Registrar mi taller',
      description: 'Elige un plan, prueba el pago de demostración y publica los datos de tu taller.',
      detail: 'Gratis, Intermedio, Premium y Pro.',
      action: 'Ver planes disponibles',
      route: '/planes',
    },
  ];

  constructor(private pageTransition: PageTransitionService) {}

  go(path: string): void {
    this.pageTransition.navigate(path);
  }
}
