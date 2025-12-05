import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { Subscription, filter } from 'rxjs';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent implements OnInit, OnDestroy {

  isCollapsed = true;
  currentRoute = '';
  private routerSubscription!: Subscription;

  apiMenuList: any[] = [];
  menuList: any[] = [];

  constructor(private router: Router) { }

  ngOnInit(): void {

    this.apiMenuList = this.safeParseArray(localStorage.getItem('menu'));

    if (!this.apiMenuList.length) {
      this.router.navigate(['/login']);
      return;
    }

    this.menuList = this.apiMenuList.map((m: any) => ({
      ...m,
      open: false
    }));

    this.currentRoute = this.router.url;

    this.routerSubscription = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe((event: any) => {
        this.currentRoute = event.urlAfterRedirects || event.url;
        this.expandActiveMenu();
      });
  }

  ngOnDestroy(): void {
    this.routerSubscription?.unsubscribe();
  }

  safeParseArray(value: any): any[] {
    try {
      const parsed = value ? JSON.parse(value) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  isActiveSubmenu(sub: any): boolean {
    const submenuPath = '/' + sub.page_url;
    return this.currentRoute.startsWith(submenuPath);
  }

  hasActiveSubmenu(menu: any): boolean {
    return menu.menu_detail?.some((sub: any) => this.isActiveSubmenu(sub));
  }

  expandActiveMenu(): void {
    this.menuList.forEach(menu => {
      if (this.hasActiveSubmenu(menu)) {
        menu.open = true;
      }
    });
  }

  onClickMenu(menu: any, submenu: any): void {
    localStorage.setItem('selectedMenu', JSON.stringify(menu));
    localStorage.setItem('selectedSubMenu', submenu.display_name);
    this.router.navigateByUrl(submenu.page_url);
  }

  toggleSidebar(): void {
    this.isCollapsed = !this.isCollapsed;
  }

  onMenuHeaderClick(menu: any): void {
    this.isCollapsed = false;
    menu.open = !menu.open;
  }
}
