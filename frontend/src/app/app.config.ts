import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideServiceWorker } from '@angular/service-worker';

import { routes } from './app.routes';
import { authInterceptor } from './core/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    // SW DESHABILITADO temporalmente para iteración rápida en dev/staging.
    // Razón: el SW cachea chunks JS con `installMode: prefetch` y, aunque hay
    // un listener `versionUpdates` que llama `activateUpdate + reload`, en
    // sesiones largas el navegador igual servía el bundle viejo hasta cerrar
    // todas las pestañas. Para volver a habilitar PWA en producción cambiar
    // `enabled` a `!isDevMode()`.
    provideServiceWorker('app-worker.js', {
      enabled: false,
      registrationStrategy: 'registerWhenStable:30000',
    }),
  ]
};
