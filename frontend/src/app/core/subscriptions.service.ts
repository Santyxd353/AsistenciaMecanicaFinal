import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { SaaSPlan } from './plans.service';

export interface CheckoutResponse {
  checkout_id: number;
  referencia: string;
  estado: string;
  monto: number;
  moneda: string;
  plan: SaaSPlan;
}

export interface PaymentResponse {
  checkout_id: number;
  estado: string;
  onboarding_token: string;
  plan_codigo: string;
}

export interface CurrentSubscription {
  plan: SaaSPlan;
  estado: string;
  uso: {
    administradores: number;
    mecanicos: number;
  };
  limites: {
    administradores: number | null;
    mecanicos: number | null;
    solicitudes_mes: number | null;
  };
}

@Injectable({ providedIn: 'root' })
export class SubscriptionsService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/subscriptions';

  constructor(private http: HttpClient) {}

  createCheckout(planCodigo: string, email: string, nombreContacto: string): Observable<CheckoutResponse> {
    return this.http.post<CheckoutResponse>(`${this.apiUrl}/checkout`, {
      plan_codigo: planCodigo,
      email,
      nombre_contacto: nombreContacto,
    });
  }

  payCheckout(checkoutId: number): Observable<PaymentResponse> {
    return this.http.post<PaymentResponse>(`${this.apiUrl}/checkout/${checkoutId}/pay`, {});
  }

  getCurrent(): Observable<CurrentSubscription> {
    return this.http.get<CurrentSubscription>(`${this.apiUrl}/current`);
  }

  changePlan(planCodigo: string): Observable<{ message: string; subscription: CurrentSubscription }> {
    return this.http.post<{ message: string; subscription: CurrentSubscription }>(`${this.apiUrl}/change-plan`, {
      plan_codigo: planCodigo,
    });
  }
}
