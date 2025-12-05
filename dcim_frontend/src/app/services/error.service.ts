// error.service.ts
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ErrorService {

  showError(message: string) {
    alert(message);  
  }
}
