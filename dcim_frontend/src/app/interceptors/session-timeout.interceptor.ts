import { Injectable } from '@angular/core';
import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest
} from '@angular/common/http';
import { Observable, catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { ErrorService } from '../services/error.service';

@Injectable()
export class SessionTimeoutInterceptor implements HttpInterceptor {

  private readonly timeoutStatuses = [401];
  private readonly timeoutHeader = 'X-Session-Expired';

  constructor(
    private auth: AuthService,
    private errorService: ErrorService
  ) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    return next.handle(req).pipe(
      catchError((err: HttpErrorResponse) => {

        const url = req.url.toLowerCase();

        if (url.includes('login')) {
          return throwError(() => err);
        }

        if (err instanceof HttpErrorResponse && this.isSessionTimeout(err)) {
          this.handleTimeout();
        }

        return throwError(() => err);
      })
    );
  }

  private isSessionTimeout(err: HttpErrorResponse): boolean {
    if (this.timeoutStatuses.includes(err.status)) {
      return true;
    }

    const headerValue = err.headers?.get(this.timeoutHeader);
    if (headerValue?.toLowerCase() === 'true') {
      return true;
    }

    const message = this.extractMessage(err);
    return message.includes('session expired') || message.includes('session timeout');
  }

  private extractMessage(err: HttpErrorResponse): string {
    const error = err.error;

    if (!error) return err.message?.toLowerCase() || '';

    if (typeof error === 'string') return error.toLowerCase();

    return (
      error?.message?.toLowerCase() ||
      error?.detail?.toLowerCase() ||
      err.message?.toLowerCase() ||
      ''
    );
  }

  private handleTimeout(): void {
    this.errorService.showError('Your session expired. Please sign in again.');
    this.auth.logout();
  }
}
