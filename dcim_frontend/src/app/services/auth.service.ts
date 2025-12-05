// auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, catchError, of } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {

 private baseUrl = `${environment.apiUrl}/api/dcim`;

  constructor(private http: HttpClient, private router: Router) { }

  login(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/login`, data).pipe(catchError(err => of(err)));;
  }

  get accessToken() {
    return localStorage.getItem('access_token');
  }

  get refreshToken() {
    return localStorage.getItem('refresh_token');
  }

  saveTokens(access: string, refresh: string) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }

  refreshAccessToken(): Observable<any> {
    const refresh = this.refreshToken;
    if (!refresh) {
      return of(null);
    }

    const headers = new HttpHeaders({
      Authorization: `Bearer ${refresh}`,
    });

    // Backend refresh endpoint: POST /api/dcim/refresh
    return this.http.post(`${this.baseUrl}/refresh`, {}, { headers });
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('access_token');
  }

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('config');
    localStorage.removeItem('user');
    localStorage.removeItem('menu');
    this.router.navigate(['/login']);
  }
}
