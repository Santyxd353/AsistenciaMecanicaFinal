import { Routes } from '@angular/router';
import { AdminGuard } from './core/admin.guard';
import { ClientGuard } from './core/client.guard';
import { CreateWorkshopGuard } from './core/create-workshop.guard';
import { TecnicoGuard } from './core/tecnico.guard';
import { WorkshopGuard } from './core/workshop.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  {
    path: 'login/admin',
    loadComponent: () => import('./login-admin/login-admin.component').then((m) => m.LoginAdminComponent),
  },
  {
    path: 'login/usuarios',
    loadComponent: () => import('./login-users/login-users.component').then((m) => m.LoginUsersComponent),
  },
  {
    path: 'login/trabajadores',
    loadComponent: () => import('./login-workers/login-workers.component').then((m) => m.LoginWorkersComponent),
  },
  {
    path: 'login',
    loadComponent: () => import('./login-selector/login-selector.component').then((m) => m.LoginSelectorComponent),
  },
  {
    path: 'login/legacy',
    loadComponent: () => import('./login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'planes',
    loadComponent: () => import('./plans/plans.component').then((m) => m.PlansComponent),
  },
  {
    path: 'checkout/:plan',
    loadComponent: () => import('./checkout/checkout.component').then((m) => m.CheckoutComponent),
  },
  {
    path: 'onboarding/taller',
    loadComponent: () => import('./onboarding-workshop/onboarding-workshop.component').then((m) => m.OnboardingWorkshopComponent),
  },
  {
    path: 'upgrade-plan',
    loadComponent: () => import('./upgrade-plan/upgrade-plan.component').then((m) => m.UpgradePlanComponent),
    canActivate: [WorkshopGuard],
  },
  {
    path: 'reset-password',
    loadComponent: () => import('./reset-password/reset-password.component').then((m) => m.ResetPasswordComponent),
  },
  {
    path: 'logout',
    loadComponent: () => import('./logout/logout.component').then((m) => m.LogoutComponent),
  },
  {
    path: 'cliente',
    loadComponent: () => import('./client-portal/client-portal.component').then((m) => m.ClientPortalComponent),
    canActivate: [ClientGuard],
  },
  {
    path: 'cliente/perfil',
    loadComponent: () => import('./client-portal/cliente-perfil.component').then((m) => m.ClientePerfilComponent),
    canActivate: [ClientGuard],
  },
  {
    path: 'cliente/vehiculos',
    loadComponent: () => import('./client-portal/cliente-vehiculos.component').then((m) => m.ClienteVehiculosComponent),
    canActivate: [ClientGuard],
  },
  {
    path: 'cliente/solicitudes',
    loadComponent: () => import('./client-portal/cliente-solicitudes.component').then((m) => m.ClienteSolicitudesComponent),
    canActivate: [ClientGuard],
  },
  {
    path: 'tecnico',
    loadComponent: () => import('./tecnicos/panel-tecnico.component').then((m) => m.PanelTecnicoComponent),
    canActivate: [TecnicoGuard],
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./dashboard/dashboard.component').then((m) => m.DashboardComponent),
    canActivate: [AdminGuard],
  },
  {
    path: 'superadmin',
    loadComponent: () => import('./dashboard/dashboard.component').then((m) => m.DashboardComponent),
    canActivate: [AdminGuard],
  },
  {
    path: 'taller',
    loadComponent: () => import('./workshop-dashboard/workshop-dashboard.component').then((m) => m.WorkshopDashboardComponent),
    canActivate: [WorkshopGuard]
  },
  {
    path: 'crear-taller',
    loadComponent: () => import('./workshop-setup/workshop-setup.component').then((m) => m.WorkshopSetupComponent),
    canActivate: [CreateWorkshopGuard]
  },
  {
    path: 'taller/perfil',
    loadComponent: () => import('./workshop-setup/workshop-setup.component').then((m) => m.WorkshopSetupComponent),
    canActivate: [WorkshopGuard]
  },
  {
    path: 'taller/tecnicos',
    loadComponent: () => import('./workshop-dashboard/tecnicos/tecnicos.component').then((m) => m.TecnicosComponent),
    canActivate: [WorkshopGuard]
  },
  {
    path: 'taller/administradores',
    loadComponent: () => import('./workshop-dashboard/admins/admins.component').then((m) => m.AdminsComponent),
    canActivate: [WorkshopGuard]
  },
  {
    path: 'taller/solicitudes',
    loadComponent: () => import('./taller-solicitudes/taller-solicitudes.component').then((m) => m.TallerSolicitudesComponent),
    canActivate: [WorkshopGuard]
  },
  {
    // Perfil público del mecánico: accesible para cualquier usuario
    // autenticado (taller, cliente, mecánico viendo perfiles ajenos, admin).
    path: 'mecanicos/:id',
    loadComponent: () =>
      import('./mechanic-profile/mechanic-profile.component').then(
        (m) => m.MechanicProfileComponent,
      ),
  },
  { path: '**', redirectTo: '/login' }
];
