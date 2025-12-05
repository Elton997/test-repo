// auth-refresh.interceptor.ts
import { Injectable } from '@angular/core';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpErrorResponse
} from '@angular/common/http';
import { BehaviorSubject, Observable, catchError, filter, switchMap, take, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  private isRefreshing = false;
  private tokenSubject = new BehaviorSubject<string | null>(null);

  constructor(private auth: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    // Attach current access token (if any) to the outgoing request
    const authReq = this.addToken(req, this.auth.accessToken);

    const url = req.url || '';
    const isRefreshCall = url.includes('/refresh');

    return next.handle(authReq).pipe(
      catchError(err => {
        if (err instanceof HttpErrorResponse && !isRefreshCall) {
          // 419: access token expired → always try refresh and then retry original request
          if (err.status === 419) {
            return this.handleTokenExpiry(req, next);
          }

          // 401: unauthorized (invalid token / refresh failed) → force logout
          if (err.status === 401) {
            this.auth.logout();
            return throwError(() => err);
          }
        }
        return throwError(() => err);
      })
    );
  }

  private handleTokenExpiry(req: HttpRequest<any>, next: HttpHandler) {
    if (!this.auth.refreshToken) {
      this.auth.logout();
      return throwError(() => new Error('Session Expired'));
    }

    // already refreshing → queue requests
    if (this.isRefreshing) {
      return this.tokenSubject.pipe(
        filter(token => token !== null),
        take(1),
        switchMap(token => next.handle(this.addToken(req, token!)))
      );
    }

    this.isRefreshing = true;
    this.tokenSubject.next(null);

    return this.auth.refreshAccessToken().pipe(
      switchMap((res: any) => {
        // Validate refresh response shape
        const newAccess = res?.access_token;
        const newRefresh = res?.refresh_token;
        if (!newAccess || !newRefresh) {
          throw new Error('Invalid refresh response');
        }

        this.auth.saveTokens(newAccess, newRefresh);
        this.isRefreshing = false;
        this.tokenSubject.next(newAccess);
        return next.handle(this.addToken(req, newAccess));
      }),
      catchError(err => {
        this.isRefreshing = false;
        this.auth.logout();
        return throwError(() => err);
      })
    );
  }

  private addToken(req: HttpRequest<any>, token: string | null) {
    if (!token) return req;

    const url = req.url || '';

    // Do not attach access token to login or refresh calls,
    // and do not override an explicitly set Authorization header.
    if (url.includes('/login') || url.includes('/refresh') || req.headers.has('Authorization')) {
      return req;
    }

    return req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
  }
}
