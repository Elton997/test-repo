import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ListService {

  private baseUrl = `${environment.apiUrl}/api/dcim`;

  readonly options = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json'
    })
  };

  constructor(private http: HttpClient) {}

  listItems(filters: any) {
    try {
      let params = new HttpParams();

      Object.keys(filters).forEach(key => {
        if (filters[key] !== null && filters[key] !== '' && filters[key] !== undefined) {
          params = params.append(key, filters[key]);
        }
      });

      return this.http.get(`${this.baseUrl}/list`, {
        params,
        headers: this.options.headers
      }).pipe(
        catchError((error) => {
          console.error('Error while fetching items:', error);
          return throwError(() => error);
        })
      );

    } catch (err) {
      console.error("Client-side error in listItems(): ", err);
      return throwError(() => err);
    }
  }
}
