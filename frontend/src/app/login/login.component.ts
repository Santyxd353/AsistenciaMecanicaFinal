import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService, UserRole } from '../core/auth.service';

type AuthMode = 'login' | 'register';
type RegistrationRole = 'client' | 'workshop';

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
  mode: AuthMode = 'login';
  registerRole: RegistrationRole = 'client';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
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
    return this.registerRole === 'client' ? 'Registro de cliente' : 'Registro de taller';
  }

  setMode(mode: AuthMode) {
    this.mode = mode;
    this.error = '';
    this.syncValidators();
  }

  setRegisterRole(role: RegistrationRole) {
    this.registerRole = role;
    this.error = '';
    this.syncValidators();
  }

  onSubmit() {
    if (this.authForm.invalid) {
      this.authForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.error = '';

    if (this.mode === 'login') {
      const { username, password } = this.authForm.value;
      this.authService.login(username, password).subscribe({
        next: (response) => {
          localStorage.setItem('access_token', response.access_token);
          this.finishAuth(response.role);
        },
        error: (err) => {
          this.loading = false;
          this.error = err?.error?.detail || 'Credenciales inválidas.';
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
        localStorage.setItem('access_token', response.access_token);
        this.finishAuth(response.role);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'No se pudo completar el registro.';
      }
    });
  }

  private finishAuth(role: UserRole) {
    this.loading = false;
    this.router.navigate([this.authService.getDefaultRouteForRole(role)]);
  }

  private syncValidators() {
    const nameControl = this.authForm.get('full_name');
    const emailControl = this.authForm.get('email');

    if (this.mode === 'register') {
      nameControl?.setValidators([Validators.required]);
      emailControl?.setValidators([Validators.required, Validators.email]);
    } else {
      nameControl?.clearValidators();
      emailControl?.clearValidators();
    }

    nameControl?.updateValueAndValidity();
    emailControl?.updateValueAndValidity();
  }
}
