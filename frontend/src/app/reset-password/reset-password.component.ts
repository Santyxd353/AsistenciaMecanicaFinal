import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="reset-shell">
      <section class="reset-card">
        <p class="eyebrow">Recuperación de acceso</p>
        <h1>Restablece tu contraseña</h1>
        <p class="lede" *ngIf="!successMessage">
          Define una nueva contraseña para tu cuenta. Este enlace solo funciona por tiempo limitado.
        </p>
        <p class="lede" *ngIf="successMessage">
          {{ successMessage }}
        </p>

        <div class="alert alert-error" *ngIf="error">
          {{ error }}
        </div>

        <form [formGroup]="resetForm" (ngSubmit)="onSubmit()" class="reset-form" *ngIf="!successMessage">
          <div class="form-group">
            <label for="new_password">Nueva contraseña</label>
            <input
              id="new_password"
              type="password"
              formControlName="new_password"
              placeholder="Mínimo 6 caracteres"
            />
          </div>

          <div class="form-group">
            <label for="confirm_password">Confirmar contraseña</label>
            <input
              id="confirm_password"
              type="password"
              formControlName="confirm_password"
              placeholder="Repite la nueva contraseña"
            />
          </div>

          <button type="submit" class="btn-primary" [disabled]="loading">
            <span *ngIf="!loading">Actualizar contraseña</span>
            <span *ngIf="loading">Guardando...</span>
          </button>
        </form>

        <button type="button" class="link-button" (click)="goToLogin()">
          Volver al inicio de sesión
        </button>
      </section>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(198, 90, 22, .18), transparent 32%),
        linear-gradient(180deg, #f5ecdf 0%, #f8f9fc 48%, #ffffff 100%);
    }

    .reset-shell {
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
    }

    .reset-card {
      width: min(520px, 100%);
      background: rgba(255, 255, 255, .94);
      border: 1px solid #ebdecd;
      border-radius: 30px;
      padding: 32px;
      box-shadow: 0 22px 60px rgba(54, 31, 15, .08);
    }

    .eyebrow {
      margin: 0 0 6px;
      text-transform: uppercase;
      letter-spacing: .16em;
      font-size: 12px;
      color: #9d5927;
      font-weight: 700;
    }

    h1 {
      margin: 0;
      font-size: clamp(28px, 4vw, 38px);
      line-height: 1.05;
      color: #18120f;
    }

    .lede {
      margin: 14px 0 0;
      color: #5f554b;
      line-height: 1.65;
      font-size: 15px;
    }

    .reset-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-top: 24px;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 7px;
    }

    .form-group label {
      font-size: 13px;
      font-weight: 700;
      color: #342921;
    }

    .form-group input {
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #ddcfbc;
      background: #fffdfa;
      border-radius: 16px;
      padding: 14px 15px;
      font-size: 14px;
      color: #15110f;
    }

    .form-group input:focus {
      outline: none;
      border-color: #c86118;
      box-shadow: 0 0 0 3px rgba(200, 97, 24, .14);
    }

    .alert {
      margin-top: 18px;
      border-radius: 16px;
      padding: 12px 14px;
      font-size: 13px;
    }

    .alert-error {
      border: 1px solid #f1c3bf;
      background: #fff3f2;
      color: #b53932;
    }

    .btn-primary {
      margin-top: 4px;
      width: 100%;
      border: none;
      border-radius: 18px;
      padding: 15px;
      background: linear-gradient(135deg, #19130f 0%, #39241a 100%);
      color: #fff;
      font-size: 15px;
      font-weight: 800;
      cursor: pointer;
    }

    .btn-primary:disabled {
      opacity: .6;
      cursor: not-allowed;
    }

    .link-button {
      margin-top: 18px;
      border: none;
      background: transparent;
      color: #b7611f;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      padding: 0;
    }
  `]
})
export class ResetPasswordComponent {
  resetForm: FormGroup;
  loading = false;
  error = '';
  successMessage = '';
  private token: string;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private route: ActivatedRoute,
    private router: Router
  ) {
    this.token = this.route.snapshot.queryParamMap.get('token') || '';
    this.resetForm = this.fb.group({
      new_password: ['', [Validators.required, Validators.minLength(6)]],
      confirm_password: ['', [Validators.required, Validators.minLength(6)]]
    });

    if (!this.token) {
      this.error = 'El enlace de recuperación no es válido o está incompleto.';
    }
  }

  onSubmit(): void {
    if (!this.token) {
      this.error = 'El enlace de recuperación no es válido o está incompleto.';
      return;
    }

    if (this.resetForm.invalid) {
      this.resetForm.markAllAsTouched();
      return;
    }

    const { new_password, confirm_password } = this.resetForm.getRawValue();
    if (new_password !== confirm_password) {
      this.error = 'Las contraseñas no coinciden.';
      return;
    }

    this.loading = true;
    this.error = '';

    this.authService.confirmPasswordReset({
      token: this.token,
      new_password
    }).subscribe({
      next: (response) => {
        this.loading = false;
        this.successMessage = response.message;
        this.resetForm.disable();
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo actualizar la contraseña.';
      }
    });
  }

  goToLogin(): void {
    this.router.navigate(['/login']);
  }
}
