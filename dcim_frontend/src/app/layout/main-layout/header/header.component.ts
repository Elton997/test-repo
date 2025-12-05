import { Component, OnInit, OnDestroy } from '@angular/core';
import { AuthService } from '../../../services/auth.service';
import { TitleService } from '../../../shared/Services/title.service';
import { Subscription } from 'rxjs';
import { Location } from '@angular/common';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent implements OnInit, OnDestroy {

  private titleSubscription!: Subscription;
  private locSubscription!: Subscription;
  title: string = '';
  user: any = null;
  hideSidebar = false;
  dashboardLoc:any
  constructor(
    private titleService: TitleService,
    private authService: AuthService,
    private location: Location,private router: Router
  ) { }

  ngOnInit(): void {
    this.user = this.safeParseObject(localStorage.getItem('user'));
    this.titleSubscription = this.titleService.title$.subscribe(title => {
      this.title = title;
    });
   this.locSubscription = this.titleService.loc$.subscribe(loc => {
      this.dashboardLoc = loc;
    });
    this.updateSidebarVisibility(this.router.url);

    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        this.updateSidebarVisibility(event.urlAfterRedirects);
      });
  }

  safeParseObject(value: any): any {
    try {
      if (!value) return null;
      const parsed = JSON.parse(value);
      return typeof parsed === 'object' ? parsed : null;
    } catch {
      return null;
    }
  }

  goBack(): void {
    this.location.back();
  }

  ngOnDestroy(): void {
    this.titleSubscription?.unsubscribe();
    this.locSubscription?.unsubscribe();
  }

  logout() {
    this.authService.logout();
  }

  private updateSidebarVisibility(url: string): void {
    // Hide only on dashboard route
    this.hideSidebar = url === '/dashboard';
  }
}
