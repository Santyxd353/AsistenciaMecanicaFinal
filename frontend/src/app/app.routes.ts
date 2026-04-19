import { Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { ClientPortalComponent } from './client-portal/client-portal.component';
import { LogoutComponent } from './logout/logout.component';
import { WorkshopDashboardComponent } from './workshop-dashboard/workshop-dashboard.component';
import { WorkshopSetupComponent } from './workshop-setup/workshop-setup.component';
import { ClientGuard } from './core/client.guard';
import { WorkshopGuard } from './core/workshop.guard';
import { WorkshopLikeGuard } from './core/workshop-like.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'logout', component: LogoutComponent },
  { path: 'cliente', component: ClientPortalComponent, canActivate: [ClientGuard] },
  { path: 'dashboard', component: DashboardComponent, canActivate: [WorkshopLikeGuard] },
  {
    path: 'taller',
    component: WorkshopDashboardComponent,
    canActivate: [WorkshopGuard]
  },
  {
    path: 'crear-taller',
    component: WorkshopSetupComponent,
    canActivate: [WorkshopGuard]
  },
  {
    path: 'taller/perfil',
    component: WorkshopSetupComponent,
    canActivate: [WorkshopGuard]
  }
];
