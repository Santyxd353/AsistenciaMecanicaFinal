import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

/**
 * Adjunta el `Bearer` token a cada request autenticado, y maneja globalmente
 * la respuesta 401:
 *   1. Limpia el localStorage (token + role + currentUser) para no quedar con
 *      una sesión zombie que vuelva a fallar en cada request siguiente.
 *   2. Redirige al login conservando la URL actual como `returnUrl`.
 *
 * Esto evita el caso reportado donde un token caducado dejaba al usuario en
 * un modal "Guardando..." sin feedback claro: el observable de error sí
 * disparaba, pero el usuario veía el flujo siguiente fallar y asumía que
 * estaba colgado. Ahora 401 = vuelta al login inmediata + flag claro.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  const publicAuthPaths = [
    '/api/v1/auth/login',
    '/api/v1/auth/login/worker',
    '/api/v1/auth/login/admin',
    '/api/v1/auth/login/client',
    '/api/v1/auth/register/client',
    '/api/v1/auth/register/workshop',
    '/api/v1/auth/forgot-password',
    '/api/v1/auth/reset-password',
  ];

  const isPublic = publicAuthPaths.some(path => req.url.includes(path));
  const token = localStorage.getItem('token');

  const authedReq = !isPublic && token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authedReq).pipe(
    catchError((err: unknown) => {
      // Solo redirigimos cuando el 401 corresponde a una "sesión expirada":
      //   * había un token en localStorage (el usuario CREÍA estar logueado)
      //   * y la request NO era pública.
      // Si el usuario está anónimo (sin token), el 401 lo maneja la pantalla
      // que disparó la request — redirigir al /login bloquea flujos públicos
      // como `/planes` → `/checkout` → `/onboarding/taller`, que solo se
      // autentica al final del registro del taller.
      if (
        err instanceof HttpErrorResponse &&
        err.status === 401 &&
        !isPublic &&
        token
      ) {
        localStorage.removeItem('token');
        localStorage.removeItem('role');
        localStorage.removeItem('currentUser');
        const returnUrl = router.routerState.snapshot.url;
        router.navigate(['/login'], { queryParams: returnUrl ? { returnUrl } : undefined });
      }
      return throwError(() => err);
    }),
  );
};
