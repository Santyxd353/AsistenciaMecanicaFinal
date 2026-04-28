import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize, timeout } from 'rxjs';

import { AuthService, UserRole } from '../core/auth.service';

type AuthMode = 'login' | 'register' | 'forgot-password';
type RegistrationRole = 'client' | 'workshop';
const FORGOT_PASSWORD_GENERIC_MESSAGE =
  'Si el correo existe, te enviamos instrucciones para restablecer la contraseña.';
const TECNICO_FORGOT_PASSWORD_MESSAGE =
  'Usted no tiene autorización para poder solicitar recuperación de contraseña';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  authForm: FormGroup;
  loading = false;
  error = '';
  infoMessage = '';
  mode: AuthMode = 'login';
  registerRole: RegistrationRole = 'client';
  forgotPasswordEmailSent = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {
    this.authForm = this.fb.group({
      full_name: [''],
      username: ['', Validators.required],
      email: [''],
      password: ['', [Validators.required, Validators.minLength(6)]]
    });

    if (this.authService.isLoggedIn()) {
      this.router.navigate([this.authService.getDefaultRouteForRole()]);
    }
  }

  get pageTitle(): string {
    if (this.mode === 'login') {
      return 'Acceso al sistema';
    }
    if (this.mode === 'forgot-password') {
      return 'Recuperar contraseña';
    }
    return this.registerRole === 'client' ? 'Registro de cliente' : 'Registro de taller';
  }

  setMode(mode: AuthMode) {
    this.mode = mode;
    this.error = '';
    this.infoMessage = '';
    this.loading = false;
    this.forgotPasswordEmailSent = false;
    this.syncValidators();
    this.cdr.detectChanges();
  }

  setRegisterRole(role: RegistrationRole) {
    this.registerRole = role;
    this.error = '';
    this.infoMessage = '';
    this.loading = false;
    this.syncValidators();
    this.cdr.detectChanges();
  }

  onSubmit() {
    if (this.authForm.invalid) {
      this.authForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.error = '';
    this.infoMessage = '';

    if (this.mode === 'forgot-password') {
      const { email } = this.authForm.value;
      this.error = '';
      this.infoMessage = '';
      this.forgotPasswordEmailSent = false;

      this.authService.requestPasswordReset(email)
        .pipe(
          timeout(10000),
          finalize(() => {
            this.loading = false;
            this.cdr.detectChanges();
          })
        )
        .subscribe({
        next: (response) => {
          const message = response?.message || FORGOT_PASSWORD_GENERIC_MESSAGE;

          if (message === TECNICO_FORGOT_PASSWORD_MESSAGE) {
            this.loading = false;
            this.error = message;
            this.infoMessage = '';
            this.forgotPasswordEmailSent = false;
            this.cdr.detectChanges();
            return;
          }

          this.infoMessage = message;
          this.error = '';
          this.forgotPasswordEmailSent = true;
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.loading = false;
          this.forgotPasswordEmailSent = false;
          this.infoMessage = '';

          if (err?.status === 403) {
            this.error = err?.error?.detail || TECNICO_FORGOT_PASSWORD_MESSAGE;
            this.cdr.detectChanges();
            return;
          }

          this.error = err?.name === 'TimeoutError'
            ? 'La solicitud tardó demasiado, pero si el correo existe es posible que el enlace ya se haya generado.'
            : (err?.error?.detail || 'No se pudo procesar la solicitud de recuperación.');
          this.cdr.detectChanges();
        }
      });
      return;
    }

    if (this.mode === 'login') {
      const { username, password } = this.authForm.value;
      this.authService.login(username, password).subscribe({
        next: (response) => {
          this.finishAuth(response.role);
        },
        error: (err) => {
          this.loading = false;
          this.error = err?.error?.detail || 'Credenciales inválidas.';
          this.cdr.detectChanges();
        }
      });
      return;
    }

    const payload = {
      username: this.authForm.value.username,
      email: this.authForm.value.email,
      full_name: this.authForm.value.full_name,
      password: this.authForm.value.password
    };

    const request = this.registerRole === 'client'
      ? this.authService.registerClient(payload)
      : this.authService.registerWorkshop(payload);

    request.subscribe({
      next: (response) => {
        this.finishAuth(response.role);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo completar el registro.';
        this.cdr.detectChanges();
      }
    });
  }

  private finishAuth(role: UserRole) {
    this.loading = false;
    this.cdr.detectChanges();
    this.router.navigate([this.authService.getDefaultRouteForRole(role)]);
  }

  private syncValidators() {
    const nameControl = this.authForm.get('full_name');
    const emailControl = this.authForm.get('email');
    const usernameControl = this.authForm.get('username');
    const passwordControl = this.authForm.get('password');

    if (this.mode === 'register') {
      nameControl?.setValidators([Validators.required]);
      emailControl?.setValidators([Validators.required, Validators.email]);
      usernameControl?.setValidators([Validators.required]);
      passwordControl?.setValidators([Validators.required, Validators.minLength(6)]);
    } else if (this.mode === 'forgot-password') {
      nameControl?.clearValidators();
      emailControl?.setValidators([Validators.required, Validators.email]);
      usernameControl?.clearValidators();
      passwordControl?.clearValidators();
    } else {
      nameControl?.clearValidators();
      emailControl?.clearValidators();
      usernameControl?.setValidators([Validators.required]);
      passwordControl?.setValidators([Validators.required, Validators.minLength(6)]);
    }

    nameControl?.updateValueAndValidity();
    emailControl?.updateValueAndValidity();
    usernameControl?.updateValueAndValidity();
    passwordControl?.updateValueAndValidity();
  }

  resendPasswordReset() {
    this.forgotPasswordEmailSent = false;
    this.infoMessage = '';
    this.error = '';
    this.cdr.detectChanges();
    this.onSubmit();
  }
}
