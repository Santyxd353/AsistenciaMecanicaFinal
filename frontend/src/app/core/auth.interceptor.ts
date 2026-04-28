import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const publicAuthPaths = [
    '/api/v1/auth/login',
    '/api/v1/auth/register/client',
    '/api/v1/auth/register/workshop',
    '/api/v1/auth/forgot-password',
    '/api/v1/auth/reset-password',
  ];

  if (publicAuthPaths.some(path => req.url.includes(path))) {
    return next(req);
  }

  const token = localStorage.getItem('token');
  if (!token) {
    return next(req);
  }

  return next(
    req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    })
  );
};
