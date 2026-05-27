import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router, RouterModule } from '@angular/router';

import { PlansService, SaaSPlan } from '../core/plans.service';
import { CurrentSubscription, SubscriptionsService } from '../core/subscriptions.service';

@Component({
  selector: 'app-upgrade-plan',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <main class="upgrade">
      <header>
        <a routerLink="/taller">Volver al taller</a>
        <p class="kicker">Limite de plan</p>
        <h1>Sube de plan para continuar</h1>
        <p *ngIf="current">Plan actual: <strong>{{ current.plan.nombre }}</strong> Â· {{ current.uso.administradores }} admins Â· {{ current.uso.mecanicos }} mecanicos</p>
      </header>
      <section class="grid">
        <article class="plan" *ngFor="let plan of plans">
          <span>{{ plan.nombre }}</span>
          <strong>{{ plan.precio_mensual === 0 ? 'Gratis' : ('Bs ' + plan.precio_mensual + '/mes') }}</strong>
          <p>{{ plan.descripcion }}</p>
          <button (click)="change(plan)" [disabled]="loading || current?.plan?.codigo === plan.codigo">
            {{ current?.plan?.codigo === plan.codigo ? 'Plan actual' : 'Cambiar a este plan' }}
          </button>
        </article>
      </section>
      <div class="message" *ngIf="message">{{ message }}</div>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;color:#2f241d;font-family:Inter,Segoe UI,Arial,sans-serif}
    .upgrade{max-width:1120px;margin:0 auto;padding:32px} a{color:#8b5e34;text-decoration:none;font-weight:900}.kicker{color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{font-size:42px;margin:0}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.plan{background:#fff;border:1px solid #ead7c4;border-radius:16px;padding:20px;display:grid;gap:12px;box-shadow:0 14px 35px rgba(86,52,28,.10)}
    .plan span{color:#8b5e34;text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:900}.plan strong{font-size:26px}.plan p{color:#7a6554}button{border:0;border-radius:8px;padding:12px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer}button:disabled{opacity:.55}.message{margin-top:16px;background:#dcfce7;color:#166534;border-radius:12px;padding:12px}
    @media(max-width:900px){.grid{grid-template-columns:1fr 1fr}}@media(max-width:620px){.grid{grid-template-columns:1fr}}
  `],
})
export class UpgradePlanComponent implements OnInit {
  plans: SaaSPlan[] = [];
  current: CurrentSubscription | null = null;
  loading = false;
  message = '';
  constructor(private plansService: PlansService, private subscriptions: SubscriptionsService, private router: Router) {}
  ngOnInit(): void {
    this.plansService.getPlans().subscribe((plans) => this.plans = plans);
    this.subscriptions.getCurrent().subscribe({ next: (current) => this.current = current });
  }
  change(plan: SaaSPlan): void {
    this.loading = true;
    this.subscriptions.changePlan(plan.codigo).subscribe({
      next: (response) => {
        this.current = response.subscription;
        this.message = response.message;
        this.loading = false;
        setTimeout(() => this.router.navigate(['/taller']), 800);
      },
      error: () => {
        this.message = 'No se pudo cambiar el plan.';
        this.loading = false;
      },
    });
  }
}


