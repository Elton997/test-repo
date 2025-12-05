import { Injectable } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TitleService {

  private _title$ = new BehaviorSubject<string>('Dashboard');  // default title
  private _loc$ = new BehaviorSubject<string>(localStorage.getItem('dashboard_location_name') || '')
  title$ = this._title$.asObservable();
  loc$ = this._loc$.asObservable();
  constructor(private title: Title) { }

  updateTitle(newTitle: string) {
    this._title$.next(newTitle);
    this.title.setTitle(newTitle); // updates browser tab title
  }

  setLoc(newLoc:string){
    this._loc$.next(newLoc)
  }
}
