import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';

export type UserRole = 'driver' | 'workshop' | 'admin';

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  full_name?: string | null;
  role: UserRole;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  user: AuthUser;
}

export interface RegisterPayload {
  username: string;
  email: string;
  full_name?: string;
  password: string;
}

export interface UpdateProfilePayload {
  username?: string;
  email?: string;
  full_name?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000/api/v1/auth';
  private currentUserSubject = new BehaviorSubject<AuthUser | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {
    const userRaw = localStorage.getItem('currentUser');
    if (userRaw) {
      this.currentUserSubject.next(JSON.parse(userRaw) as AuthUser);
    }
  }

  get currentUserValue(): AuthUser | null {
    return this.currentUserSubject.value;
  }

  login(username: string, password: string): Observable<AuthResponse> {
    const formData = new URLSearchParams();
    formData.set('username', username);
    formData.set('password', password);

    return this.http.post<AuthResponse>(`${this.apiUrl}/login`, formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    }).pipe(
      tap((response) => this.persistSession(response))
    );
  }

  registerClient(payload: RegisterPayload): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.apiUrl}/register/client`, payload).pipe(
      tap((response) => this.persistSession(response))
    );
  }

  registerWorkshop(payload: RegisterPayload): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.apiUrl}/register/workshop`, payload).pipe(
      tap((response) => this.persistSession(response))
    );
  }

  getProfile(): Observable<AuthUser> {
    return this.http.get<AuthUser>(`${this.apiUrl}/me`).pipe(
      tap((user) => this.persistUser(user))
    );
  }

  updateProfile(payload: UpdateProfilePayload): Observable<AuthUser> {
    return this.http.put<AuthUser>(`${this.apiUrl}/me`, payload).pipe(
      tap((user) => this.persistUser(user))
    );
  }

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('currentUser');
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }

  isLoggedIn() {
    return !!localStorage.getItem('token');
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  getCurrentUser(): AuthUser | null {
    return this.currentUserSubject.value;
  }

  getCurrentRole(): UserRole | null {
    return this.currentUserSubject.value?.role ?? (localStorage.getItem('role') as UserRole | null);
  }

  isWorkshopLike(): boolean {
    const role = this.getCurrentRole();
    return role === 'workshop' || role === 'admin';
  }

  getDefaultRouteForRole(role: UserRole | null = this.getCurrentRole()): string {
    if (role === 'driver') {
      return '/cliente';
    }

    if (role === 'workshop') {
      return '/taller';
    }

    if (role === 'admin') {
      return '/dashboard';
    }

    return '/login';
  }

  private persistSession(response: AuthResponse) {
    localStorage.setItem('token', response.access_token);
    localStorage.setItem('role', response.role);
    localStorage.setItem('currentUser', JSON.stringify(response.user));
    this.currentUserSubject.next(response.user);
  }

  private persistUser(user: AuthUser) {
    localStorage.setItem('role', user.role);
    localStorage.setItem('currentUser', JSON.stringify(user));
    this.currentUserSubject.next(user);
  }
}
