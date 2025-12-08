import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DynamicRackComponent } from '../../shared/Components/dynamic-rack/dynamic-rack.component';
import { TitleService } from '../../shared/Services/title.service';
import { Router, ActivatedRoute } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';

@Component({
  selector: 'app-device-details',
  standalone: true,
  imports: [CommonModule, DynamicRackComponent],
  templateUrl: './device-details.component.html',
  styleUrl: './device-details.component.scss'
})
export class DeviceDetailsComponent implements OnInit, OnDestroy {
  device: any = null;
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
    const deviceName = this.route.snapshot.paramMap.get('deviceID');
    if (deviceName) {
      this.fetchDeviceDetails(deviceName);
    } else {
      this.router.navigate([`${Menu.Device_Management}/${SubMenu.Devices}`]);
    }
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  fetchDeviceDetails(deviceName: string) {
    this.loading = true;
    const sub = this.listService.getDeviceDetails(deviceName).subscribe({
      next: (res: any) => {
        const data = res?.data;
        this.device = this.mapDeviceDetails(data, deviceName);
        // Build occupied devices from the devices array (all devices in the same rack)
        // Pass current device name to differentiate it from others
        this.occupiedDevices = this.buildOccupiedDevices(data?.devices || [], deviceName);
        if (this.device?.device_name) {
          this.titleService.updateTitle(`Device: ${this.device.device_name}`);
        }
        this.loading = false;
      },
      error: (err: any) => {
        console.error('Error fetching device details:', err);
        this.loading = false;
      }
    });

    this.subscriptions.add(sub);
  }

  private mapDeviceDetails(data: any, fallbackName: string) {
    if (!data) return null;

    // Build location string from components
    const locationParts = [
      data.building?.name,
      data.wing?.name,
      data.floor?.name
    ].filter(Boolean);
    const location = locationParts.length > 0 ? locationParts.join(', ') : data.location?.name || '';

    // Format height
    const height = data.device_type?.height ? `${data.device_type.height}U` : null;

    // Format dates
    const formatDate = (date: any) => {
      if (!date) return null;
      if (typeof date === 'string') return date.split('T')[0]; // Extract date part from ISO string
      return date;
    };

    return {
      device_name: data.name || fallbackName,
      ip_address: data.ip || null,
      status: data.status || 'Unknown',
      location: location,
      building: data.building?.name || null,
      wing: data.wing?.name || null,
      floor: data.floor?.name || null,
      data_center: data.datacenter?.name || null,
      room: null, // Not available in API response
      rack: data.rack?.name || null,
      rack_slot: data.position || null,
      role: null, // Not available in API response
      po_number: data.po_number || null,
      manufacturer: data.make?.name || null,
      device_type: data.device_type?.name || null,
      model: data.device_type?.model?.name || null,
      height: height,
      serial_number: data.serial_no || null,
      asset_tag: null, // Not available in API response
      created_date: formatDate(data.created_at),
      last_updated: formatDate(data.last_updated),
      asset_owner: data.application?.asset_owner?.name || null,
      warranty_start_date: formatDate(data.warranty?.start_date),
      warranty_end_date: formatDate(data.warranty?.end_date),
      amc_start_date: formatDate(data.amc?.start_date),
      amc_end_date: formatDate(data.amc?.end_date),
      asset_user: data.asset_user || null,
      comments: data.description || null,
      rack_height: data.rack?.height || 42, // Default to 42U if not available
    };
  }

  private buildOccupiedDevices(devices: any[] = [], currentDeviceName: string = '') {
    return devices
      .filter(d => d && (d.position !== undefined && d.position !== null))
      .map(d => {
        const isCurrentDevice = d.name && currentDeviceName && 
                                d.name.toLowerCase() === currentDeviceName.toLowerCase();
        
        // Current device gets highlighted color, others get grayed out (decreased intensity)
        let color: string | undefined;
        if (isCurrentDevice) {
          color = '#FFC107'; // Bright amber for selected device
        } else {
          color = '#b0b0b0'; // Light gray (decreased intensity) for other devices
        }
        
        return {
          start: Number(d.position) || 1,
          height: Number(d.space_required) || 1,
          label: d.name,
          color: color
        };
      });
  }

  getRackUnits(): number {
    return this.device?.rack_height || 42;
  }

  getStatusBadgeClass(): string {
    return this.device?.status ? `badge-${this.device.status.toLowerCase()}` : '';
  }

  /** Build occupied array for RackViewComponent based on device rack slot and height */
  getOccupied() {
    // The occupiedDevices already contains all devices in the rack including the current one
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