import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class WorkshopGuard implements CanActivate {

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  canActivate(): boolean {
    const currentUser = this.authService.currentUserValue;

    if (currentUser && currentUser.role === 'workshop' && currentUser.is_active) {
      return true;
    }

    if (currentUser) {
      this.router.navigate([this.authService.getDefaultRouteForRole(currentUser.role)]);
      return false;
    }

    this.router.navigate(['/login']);
    return false;
  }
}
