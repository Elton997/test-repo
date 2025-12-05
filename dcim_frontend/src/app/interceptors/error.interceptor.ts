import { Injectable } from '@angular/core';
import {
  HttpInterceptor, HttpHandler, HttpRequest,
  HttpErrorResponse, HttpEvent
} from '@angular/common/http';

import { Observable, catchError, throwError } from 'rxjs';
import { ERROR_CODES } from '../shared/error-codes';
import { ErrorService } from '../services/error.service';

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {

  constructor(private errorService: ErrorService) { }

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {

    return next.handle(req).pipe(
      catchError((err: HttpErrorResponse) => {

        const url = req.url.toLowerCase();

        if (url.includes('login')) {
          return throwError(() => err);
        }

        if (err.status === 419) {
          return throwError(() => err);
        }

        let message = 'Unexpected error occurred';

        if (err.status in ERROR_CODES) {
          message = ERROR_CODES[err.status];
        }

        this.errorService.showError(message);

        return throwError(() => err);
      })
    );
  }
}
