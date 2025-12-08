import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TitleService } from '../../shared/Services/title.service';
import { DynamicRackComponent } from '../../shared/Components/dynamic-rack/dynamic-rack.component';
import { Router, ActivatedRoute } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';

@Component({
  selector: 'app-rack-details',
  standalone: true,
  imports: [CommonModule, DynamicRackComponent],
  templateUrl: './rack-details.component.html',
  styleUrl: './rack-details.component.scss'
})
export class RackDetailsComponent implements OnInit, OnDestroy {
  rack: any = null;
  occupiedDevices: Array<{ start: number; height: number; label?: string; color?: string }> = [];
  loading = false;
  private subscriptions = new Subscription();

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private titleService: TitleService,
    private listService: ListService
  ) { }

  ngOnInit(): void {
    const rackName = this.route.snapshot.paramMap.get('rackId');
    if (rackName) {
      this.fetchRackDetails(rackName);
    } else {
      this.router.navigate([`${Menu.Rack_Management}/${SubMenu.Racks}`]);
    }
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  fetchRackDetails(rackName: string) {
    this.loading = true;
    const sub = this.listService.getDetails('racks', rackName).subscribe({
      next: (res: any) => {
        const data = res?.data;
        this.rack = this.mapRackDetails(data, rackName);
        this.occupiedDevices = this.buildOccupiedDevices(data?.devices);
        if (this.rack?.rack_name) {
          this.titleService.updateTitle(`Rack: ${this.rack.rack_name}`);
        }
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Error fetching rack details:', err);
        this.loading = false;
      }
    });

    this.subscriptions.add(sub);
  }

  private mapRackDetails(data: any, fallbackName: string) {
    if (!data) return null;
    const stats = data.stats || {};
    const utilization = stats.utilization_percent;

    return {
      rack_name: data.name || fallbackName,
      location: data.location?.name,
      building: data.building?.name,
      wing: data.wing?.name,
      floor: data.floor?.name,
      data_centre: data.datacenter?.name,
      status: data.status || 'Unknown',
      width_mm: data.width,
      height_u: data.height,
      device_count: stats.total_devices ?? (data.devices?.length || 0),
      space_utilisation: utilization !== undefined && utilization !== null ? `${utilization}%` : undefined,
      available_space: stats.available_space !== undefined && stats.available_space !== null ? `${stats.available_space}U` : undefined,
      comments: data.description
    };
  }

  private buildOccupiedDevices(devices: any[] = []) {
    return devices
      .filter(d => d && (d.position !== undefined && d.position !== null))
      .map(d => ({
        start: Number(d.position) || 1,
        height: Number(d.space_required) || 1,
        label: d.name,
        color: d.status === 'active' ? '#FFC107' : undefined
      }));
  }

  getRackUnits(): number {
    return this.rack?.height_u || 42;
  }

  getStatusBadgeClass(): string {
    return this.rack?.status ? `badge-${this.rack.status}` : '';
  }

  getOccupied() {
    return this.occupiedDevices;
  }


  onDeviceClick(event: any) {
    // Empty slot → Add Device page
    if (event.empty) {
      this.router.navigate([`${Menu.Device_Management}/${SubMenu.Devices}/add`]);
      return;

    }

    // Occupied → navigate to device details
    const deviceName = event.label;
    this.router.navigate([`${Menu.Device_Management}/${SubMenu.Devices}`, deviceName]);
  }

}