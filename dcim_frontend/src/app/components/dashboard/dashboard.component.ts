import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { TitleService } from '../../shared/Services/title.service';
import { LoaderComponent } from '../../shared/Components/loader/loader.component';
import { CommonService } from '../../shared/Services/common.service';
import { Subscription } from 'rxjs';
import { Menu, SubMenu } from '../../menu.enum';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, LoaderComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit, OnDestroy {
  constructor(private titleService: TitleService, private commonService: CommonService, private router: Router) { }
  private subscriptions = new Subscription();
  locations: any[] = [];
  loading = true;

  ngOnInit(): void {
    this.titleService.updateTitle('DASHBOARD');
    // Clear any location filter set by dashboard navigation when showing dashboard
    localStorage.removeItem('dashboard_location_name');
    this.loadData();
  }

  navigateToBuildings(loc: any, param?:any): void {
    if (!loc || !loc.name) return;
    // Store selected location name for Buildings page to pick up as a filter
    this.titleService.setLoc(loc.name);
    localStorage.setItem('dashboard_location_name', loc.name);
    if(param == 'devices'){
      this.router.navigate([Menu.Device_Management + '/' + SubMenu.Devices]);
    }else if(param == 'racks'){
      this.router.navigate([Menu.Rack_Management + '/' + SubMenu.Racks]);
    }else if(param == 'device_type'){
      this.router.navigate([Menu.Device_Management + '/' + SubMenu.DeviceTypes]);
    }else {
      this.router.navigate([Menu.Organization + '/' + SubMenu.Buildings]);
    }
  }

  loadData(): void {
    try {
      this.loading = true;
      this.subscriptions.add(
        this.commonService.summary().subscribe({
          next: (res: any) => {
            try {
              this.locations = res?.results;
            } catch (innerErr) {
              console.error('Error processing result:', innerErr);
            } finally {
              this.loading = false;
            }
          },
          error: (err: any) => {
            console.error('API error:', err);
            this.loading = false;
          }
        })
      );

    } catch (outerErr) {
      console.error('Unexpected error:', outerErr);
      this.loading = false;
    }
  }


  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}
