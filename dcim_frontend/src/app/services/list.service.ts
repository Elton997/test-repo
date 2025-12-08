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

  getDetails(entity: string, name: string) {
    try {
      const params = new HttpParams()
        .set('entity', entity)
        .set('name', name);

      return this.http.get(`${this.baseUrl}/details`, {
        params,
        headers: this.options.headers
      }).pipe(
        catchError((error) => {
          console.error('Error while fetching details:', error);
          return throwError(() => error);
        })
      );
    } catch (err) {
      console.error("Client-side error in getDetails(): ", err);
      return throwError(() => err);
    }
  }
  getDeviceDetails(deviceName: string) {
    try {
      const params = new HttpParams()
        .set('entity', 'devices')
        .set('name', deviceName);

      return this.http.get(`${this.baseUrl}/details`, {
        params,
        headers: this.options.headers
      }).pipe(
        catchError((error) => {
          console.error('Error while fetching device details:', error);
          return throwError(() => error);
        })
      );
    } catch (err) {
      console.error("Client-side error in getDeviceDetails(): ", err);
      return throwError(() => err);
    }
  }
}
