import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';

import { DEFAULT_SAAS_PLANS, PlansService, SaaSPlan } from '../core/plans.service';
import { SubscriptionsService } from '../core/subscriptions.service';

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <main class="checkout-page">
      <section class="panel plan-summary" *ngIf="plan">
        <a routerLink="/planes">Cambiar plan</a>
        <p class="kicker">Compra simulada</p>
        <h1>{{ plan.nombre }}</h1>
        <strong class="price">{{ plan.precio_mensual === 0 ? 'Gratis' : ('Bs ' + plan.precio_mensual + '/mes') }}</strong>
        <p class="muted">
          Esta pantalla simula el flujo de pago. Luego se puede reemplazar por Stripe manteniendo la misma salida:
          token de onboarding y plan seleccionado.
        </p>
        <ul>
          <li *ngFor="let item of plan.beneficios">{{ item }}</li>
        </ul>
      </section>

      <section class="panel payment-panel" *ngIf="plan">
        <div class="gateway">
          <span>Stripe mock</span>
          <strong>{{ plan.precio_mensual === 0 ? 'Bs 0.00' : ('Bs ' + (plan.precio_mensual | number:'1.2-2')) }}</strong>
        </div>

        <h2>Datos de compra</h2>
        <form (ngSubmit)="pay()" #form="ngForm">
          <label>Nombre contacto <input name="name" [(ngModel)]="name" required></label>
          <label>Email <input name="email" [(ngModel)]="email" required type="email"></label>
          <label>Metodo
            <select name="method" [(ngModel)]="method">
              <option>Tarjeta simulada</option>
              <option>QR simulado</option>
              <option>Transferencia simulada</option>
            </select>
          </label>

          <div class="card-fields" *ngIf="method === 'Tarjeta simulada'">
            <label>Numero de tarjeta <input name="card" [(ngModel)]="cardNumber" placeholder="4242 4242 4242 4242" required></label>
            <label>Expira <input name="exp" [(ngModel)]="cardExp" placeholder="12/30" required></label>
            <label>CVC <input name="cvc" [(ngModel)]="cardCvc" placeholder="123" required></label>
          </div>

          <div class="steps" *ngIf="loading || paid">
            <div class="step" *ngFor="let step of steps; let i = index" [class.done]="i < activeStep" [class.active]="i === activeStep">
              <span>{{ i < activeStep ? 'OK' : (i === activeStep ? '...' : i + 1) }}</span>
              <p>{{ step }}</p>
            </div>
          </div>

          <div class="error" *ngIf="error">{{ error }}</div>
          <button [disabled]="loading || form.invalid">
            {{ loading ? 'Procesando compra simulada...' : (plan.precio_mensual === 0 ? 'Activar plan gratis' : 'Pagar simulado y continuar') }}
          </button>
        </form>
      </section>
    </main>
  `,
  styles: [`
    :host{display:block;min-height:100vh;background:#f5efe7;color:#2f241d;font-family:Inter,Segoe UI,Arial,sans-serif}
    .checkout-page{min-height:100vh;display:grid;grid-template-columns:.9fr 1.1fr;gap:18px;align-items:center;padding:32px;max-width:1120px;margin:0 auto}
    .panel{background:#fff;border:1px solid #ead7c4;border-radius:10px;padding:28px;box-shadow:0 10px 28px rgba(86,52,28,.10)}
    a{color:#8b5e34;text-decoration:none;font-weight:900}.kicker{color:#8b5e34;text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:900}
    h1{font-size:42px;margin:0}.price{display:block;font-size:34px;margin:12px 0}.muted{color:#7a6554;line-height:1.55} ul{display:grid;gap:8px;color:#6f5745}
    .gateway{display:flex;justify-content:space-between;align-items:center;background:#f3e6d7;border:1px solid #e4c9ae;border-radius:10px;padding:14px;margin-bottom:18px}.gateway span{font-weight:900;color:#8b5e34}.gateway strong{font-size:24px}
    form,label{display:grid;gap:8px} form{gap:14px} input,select{border:1px solid #ead7c4;border-radius:8px;padding:13px;font:inherit;background:#fff} button{border:0;border-radius:8px;padding:14px;background:#8b5e34;color:#fff;font-weight:900;cursor:pointer}button:disabled{opacity:.65;cursor:not-allowed}.error{background:#fee2e2;color:#991b1b;border-radius:10px;padding:10px}
    .card-fields{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px}.steps{display:grid;gap:8px;background:#fff8ef;border:1px solid #ead7c4;border-radius:10px;padding:12px}.step{display:flex;align-items:center;gap:10px;color:#7a6554}.step span{width:30px;height:30px;border-radius:999px;display:grid;place-items:center;background:#ead7c4;font-size:11px;font-weight:900}.step.active span{background:#f3e6d7;color:#8b5e34}.step.done span{background:#dcfce7;color:#166534}.step p{margin:0}
    @media(max-width:800px){.checkout-page{grid-template-columns:1fr}}
  `],
})
export class CheckoutComponent implements OnInit {
  plan: SaaSPlan | null = null;
  name = 'Administrador del taller';
  email = 'demo@taller.local';
  method = 'Tarjeta simulada';
  cardNumber = '4242 4242 4242 4242';
  cardExp = '12/30';
  cardCvc = '123';
  loading = false;
  paid = false;
  error = '';
  activeStep = 0;
  readonly steps = [
    'Creando checkout de suscripcion',
    'Validando metodo de pago simulado',
    'Confirmando pago mock',
    'Preparando registro del taller',
  ];

  constructor(
    private route: ActivatedRoute,
    private plans: PlansService,
    private subscriptions: SubscriptionsService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    const code = this.route.snapshot.paramMap.get('plan') || 'gratis';
    this.plan = DEFAULT_SAAS_PLANS.find((plan) => plan.codigo === code) ?? DEFAULT_SAAS_PLANS[0];
    this.plans.getPlan(code).subscribe({
      next: (plan) => this.plan = plan,
      error: () => {
        this.error = 'No se pudo sincronizar con el servidor de planes. Puedes continuar con la simulacion local.';
      },
    });
  }

  async pay(): Promise<void> {
    if (!this.plan) return;
    this.loading = true;
    this.paid = false;
    this.error = '';
    this.activeStep = 0;

    await this.delay(450);
    this.subscriptions.createCheckout(this.plan.codigo, this.email, this.name).subscribe({
      next: async (checkout) => {
        this.activeStep = 1;
        await this.delay(700);
        this.activeStep = 2;
        this.subscriptions.payCheckout(checkout.checkout_id).subscribe({
          next: async (paid) => {
            this.activeStep = 3;
            await this.delay(650);
            sessionStorage.setItem('onboarding_token', paid.onboarding_token);
            sessionStorage.setItem('onboarding_plan', paid.plan_codigo);
            this.paid = true;
            this.activeStep = 4;
            this.router.navigate(['/onboarding/taller']);
          },
          error: (err) => this.fail(err),
        });
      },
      error: (err) => this.fail(err),
    });
  }

  private fail(err: any): void {
    this.loading = false;
    this.error = err?.error?.detail || 'No se pudo procesar el pago simulado.';
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}


