import { Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { ClientPortalComponent } from './client-portal/client-portal.component';
import { LogoutComponent } from './logout/logout.component';
import { ResetPasswordComponent } from './reset-password/reset-password.component';
import { WorkshopDashboardComponent } from './workshop-dashboard/workshop-dashboard.component';
import { WorkshopSetupComponent } from './workshop-setup/workshop-setup.component';
import { ClientGuard } from './core/client.guard';
import { CreateWorkshopGuard } from './core/create-workshop.guard';
import { TecnicoGuard } from './core/tecnico.guard';
import { WorkshopGuard } from './core/workshop.guard';
import { WorkshopLikeGuard } from './core/workshop-like.guard';
import { PanelTecnicoComponent } from './tecnicos/panel-tecnico.component';
import { TallerSolicitudesComponent } from './taller-solicitudes/taller-solicitudes.component';

import { TecnicosComponent } from './workshop-dashboard/tecnicos/tecnicos.component';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'reset-password', component: ResetPasswordComponent },
  { path: 'logout', component: LogoutComponent },
  { path: 'cliente', component: ClientPortalComponent, canActivate: [ClientGuard] },
  { path: 'tecnico', component: PanelTecnicoComponent, canActivate: [TecnicoGuard] },
  { path: 'dashboard', component: DashboardComponent, canActivate: [WorkshopLikeGuard] },
  {
    path: 'taller',
    component: WorkshopDashboardComponent,
    canActivate: [WorkshopGuard]
  },
  {
    path: 'crear-taller',
    component: WorkshopSetupComponent,
    canActivate: [CreateWorkshopGuard]
  },
  {
    path: 'taller/perfil',
    component: WorkshopSetupComponent,
    canActivate: [WorkshopGuard]
  },
  {
    path: 'taller/tecnicos',
    component: TecnicosComponent,
    canActivate: [WorkshopGuard]
  },
  {
    path: 'taller/solicitudes',
    component: TallerSolicitudesComponent,
    canActivate: [WorkshopGuard]
  },
  { path: '**', redirectTo: '/login' }
];
