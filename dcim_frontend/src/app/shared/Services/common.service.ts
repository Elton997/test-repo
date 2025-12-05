import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { catchError, Observable, of } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class CommonService {
  private baseUrl = `${environment.apiUrl}/api/dcim`;
  readonly options = {
  headers: new HttpHeaders({
    'Content-Type': 'application/json'
  })
};

  constructor(private http: HttpClient) { }

  summary(): Observable<any> {
    return this.http.get(`${this.baseUrl}/summary/locations`,this.options).pipe(catchError(err => of(err)));
  }
}
