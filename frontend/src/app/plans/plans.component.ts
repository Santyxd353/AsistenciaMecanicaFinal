import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router, RouterModule } from '@angular/router';

import { DEFAULT_SAAS_PLANS, PlansService, SaaSPlan } from '../core/plans.service';

@Component({
  selector: 'app-plans',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <main class="plans-page">
      <header>
        <a routerLink="/login">Volver</a>
        <p class="kicker">Planes SaaS</p>
        <h1>Elige el plan para tu taller</h1>
        <p>Cada plan controla administradores, mecanicos y capacidad de operacion.</p>
      </header>

      <section class="grid">
        <article class="plan" *ngFor="let plan of plans" [class.featured]="plan.codigo === 'premium'">
          <span>{{ plan.nombre }}</span>
          <strong>{{ plan.precio_mensual === 0 ? 'Gratis' : ('Bs ' + plan.precio_mensual + '/mes') }}</strong>
          <p>{{ plan.descripcion }}</p>
          <div class="limits">
            <b>{{ limit(plan.max_administradores) }} admins</b>
            <b>{{ limit(plan.max_mecanicos) }} mecanicos</b>
            <b>{{ limit(plan.max_solicitudes_mes) }} solicitudes/mes</b>
          </div>
          <ul>
            <li *ngFor="let item of plan.beneficios">{{ item }}</li>
          </ul>
          <a class="choose" [routerLink]="['/checkout', plan.codigo]">Elegir plan</a>
        </article>
      </section>

      <p class="notice" *ngIf="usingFallback">
        Mostrando planes base. El sistema actualizará estos datos desde el servidor cuando esté disponible.
      </p>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;color:#2f241d;font-family:Inter,Segoe UI,Arial,sans-serif}
    .plans-page{min-height:100vh;padding:32px} header{max-width:980px;margin:0 auto 24px} a{color:#8b5e34;text-decoration:none;font-weight:900}
    .kicker{margin:24px 0 6px;color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{font-size:46px;margin:0} header p{color:#7a6554}
    .grid{max-width:1240px;margin:0 auto;display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
    .plan{background:#fff;border:1px solid #ead7c4;border-radius:10px;padding:22px;display:flex;flex-direction:column;gap:14px;box-shadow:0 10px 24px rgba(86,52,28,.08)}
    .plan.featured{border-color:#8b5e34;box-shadow:0 12px 28px rgba(139,94,52,.18)}
    .plan span{font-size:12px;text-transform:uppercase;letter-spacing:.14em;color:#8b5e34;font-weight:900}
    .plan strong{font-size:30px}.plan p{color:#7a6554;line-height:1.5}.limits{display:grid;gap:8px}.limits b{background:#fff8ef;border:1px solid #ead7c4;border-radius:8px;padding:8px}
    ul{padding-left:18px;margin:0;display:grid;gap:8px;color:#4b3528}.choose{margin-top:auto;border:0;border-radius:8px;padding:13px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer;text-align:center;text-decoration:none}
    .notice{max-width:1240px;margin:16px auto 0;color:#7a6554;font-size:13px}
    @media(max-width:1100px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:640px){.grid{grid-template-columns:1fr}h1{font-size:34px}}
  `],
})
export class PlansComponent implements OnInit {
  plans: SaaSPlan[] = DEFAULT_SAAS_PLANS;
  usingFallback = true;
  constructor(private plansService: PlansService, private router: Router) {}
  ngOnInit(): void {
    this.plansService.getPlans().subscribe((plans) => {
      this.plans = plans.length ? plans : DEFAULT_SAAS_PLANS;
      this.usingFallback = plans === DEFAULT_SAAS_PLANS;
    });
  }
  limit(value: number | null): string { return value === null ? 'Ilimitados' : String(value); }
  choose(plan: SaaSPlan): void { this.router.navigate(['/checkout', plan.codigo]); }
}


