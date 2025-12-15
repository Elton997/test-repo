import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { RackPayload } from '../components/add-racks/add-racks.component';

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

  constructor(private http: HttpClient) { }

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

  addRack(rackData: RackPayload) {
    return this.http.post(
      `${this.baseUrl}/add?entity=racks`,
      rackData,
      this.options
    ).pipe(
      catchError((error) => {
        console.error('Error while adding rack:', error);
        return throwError(() => error);
      })
    );
  }

  updateRack(rackName: string, rackData: any) {
    return this.http.put(
      `${this.baseUrl}/update/${rackName}?entity=racks`,
      rackData,
      this.options
    ).pipe(
      catchError((error) => {
        console.error('Error while updating rack:', error);
        return throwError(() => error);
      })
    );
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

  addModel(modelData: any) {
    return this.http.post(
      `${this.baseUrl}/add?entity=models`,
      modelData,
      this.options
    ).pipe(
      catchError((error) => {
        console.error('Error while adding model:', error);
        return throwError(() => error);
      })
    );
  }

  updateModel(modelName: string, modelData: any) {
    const encodedName = encodeURIComponent(modelName);
    return this.http.put(
      `${this.baseUrl}/update/${encodedName}?entity=models`,
      modelData,
      this.options
    ).pipe(
      catchError((error) => {
        console.error('Error while updating model:', error);
        return throwError(() => error);
      })
    );
  }

  addMake(makeData: any) {
    return this.http.post(
      `${this.baseUrl}/add?entity=makes`,
      makeData,
      this.options
    ).pipe(
      catchError((error) => {
        console.error('Error while adding make:', error);
        return throwError(() => error);
      })
    );
  }

  updateMake(makeName: string, makeData: any) {
    const encodedName = encodeURIComponent(makeName);
    return this.http.put(
      `${this.baseUrl}/update/${encodedName}?entity=makes`,
      makeData,
      this.options
    ).pipe(
      catchError((error) => {
        console.error('Error while updating make:', error);
        return throwError(() => error);
      })
    );
  }

  exportItems(entity: string, filters: any = {}) {
    let params = new HttpParams()
      .set('entity', entity)
      .set('export', 'true'); // backend returns JSON, we convert to CSV

    Object.keys(filters).forEach(key => {
      if (filters[key] !== null && filters[key] !== undefined && filters[key] !== '') {
        params = params.set(key, filters[key]);
      }
    });

    return this.http.get(`${this.baseUrl}/list`, {
      params,
      responseType: 'blob'
    }).pipe(
      catchError(err => throwError(() => err))
    );
  }


  createDevice(payload: any) {
    // POST /api/dcim/add?entity=devices with JSON body
    return this.http.post(`${this.baseUrl}/add?entity=devices`, payload, this.options)
      .pipe(
        catchError((error) => {
          console.error('Error while creating device:', error);
          return throwError(() => error);
        })
      );
  }
  importItems(entity: string, file: File) {
    const formattedFile = new File([file], `${entity}.csv`, { type: file.type });
    const formData = new FormData();
    formData.append("file", formattedFile);

    return this.http.post(
      `${this.baseUrl}/bulk-upload?entity_type=${entity}`,
      formData,
      {
        responseType: "json",
        headers: new HttpHeaders({})  // allow multipart/form-data
      }
    );
  }

  updateDevice(deviceName: string, payload: any) {
    // PUT /api/dcim/update/{name}?entity=devices with JSON body
    return this.http.put(`${this.baseUrl}/update/${encodeURIComponent(deviceName)}?entity=devices`, payload, this.options)
      .pipe(
        catchError((error) => {
          console.error('Error while updating device:', error);
          return throwError(() => error);
        })
      );
  }

  createDeviceType(payload: any) {
    return this.http.post(`${this.baseUrl}/add?entity=device_types`, payload, this.options)
      .pipe(
        catchError((error) => {
          console.error('Error while creating device type:', error);
          return throwError(() => error);
        })
      );
  }

  updateDeviceType(name: string, payload: any) {
    return this.http.put(`${this.baseUrl}/update/${encodeURIComponent(name)}?entity=device_types`, payload, this.options)
      .pipe(
        catchError((error) => {
          console.error('Error while updating device type:', error);
          return throwError(() => error);
        })
      );
  }
}