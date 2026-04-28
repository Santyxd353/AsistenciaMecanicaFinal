import { Injectable } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { AuthService } from './auth.service';
import { WorkshopProfileService } from './workshop-profile.service';

@Injectable({
  providedIn: 'root'
})
export class CreateWorkshopGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private workshopProfileService: WorkshopProfileService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean | UrlTree> | boolean | UrlTree {
    const currentUser = this.authService.currentUserValue;

    if (!currentUser) {
      return this.router.createUrlTree(['/login']);
    }

    if (currentUser.role !== 'workshop' || !currentUser.is_active) {
      return this.router.createUrlTree([this.authService.getDefaultRouteForRole(currentUser.role)]);
    }

    return this.workshopProfileService.getMyWorkshop().pipe(
      map(() => this.router.createUrlTree(['/taller'])),
      catchError((error: { status?: number }) => {
        if (error?.status === 404) {
          return of(true);
        }

        return of(this.router.createUrlTree(['/taller']));
      })
    );
  }
}
