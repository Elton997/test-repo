import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DynamicRackComponent } from '../../shared/Components/dynamic-rack/dynamic-rack.component';
import { TitleService } from '../../shared/Services/title.service';
import { Router } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';

@Component({
  selector: 'app-device-details',
  standalone: true,
  imports: [CommonModule, DynamicRackComponent],
  templateUrl: './device-details.component.html',
  styleUrl: './device-details.component.scss'
})
export class DeviceDetailsComponent implements OnInit {

  // Sample device data - in real app, this would come from a service
  device = {
    device_name: 'dmi01-r01-s46',
    ip_address: '192.168.1.10',
    status: 'Active',
    location: 'Building A, Wing B, Floor 2, Room 101',
    building: 'Building A',
    wing: 'Wing B',
    floor: '2',
    data_center: 'DMI Data Center',
    room: '101',
    rack: 'A42',
    rack_slot: '10',
    role: 'Router',
    po_number: 'PO-2024-0012',
    manufacturer: 'Juniper',
    device_type: 'MX480',
    model: 'MX480-DC',
    height: '4U',
    serial_number: 'JX924U45D001',
    asset_tag: 'AT-2024-0047',
    created_date: '2023-06-15',
    last_updated: '2024-11-20',
    asset_owner: 'IT Department',
    warranty_start_date: '2023-06-15',
    warranty_end_date: '2026-06-15',
    amc_start_date: '2023-06-15',
    amc_end_date: '2026-06-15',
    asset_user: 'John Doe',
    comments: 'Core router for data center routing and backbone connectivity.',
  };

  constructor(private router: Router, private titleService: TitleService) { }


  ngOnInit(): void {
    this.titleService.updateTitle('DEVICE DETAILS');
    console.log('DeviceDetailsComponent initialized', { deviceName: this.device.device_name, rack: this.device.rack });
  }

  getStatusBadgeClass(): string {
    return `badge-${this.device.status}`;
  }

  /** Build occupied array for RackViewComponent based on device rack slot and height */
  getOccupied() {
    // Interpret rack_slot as bottom-based U (number) or top; adjust as needed
    const slot = parseInt(String(this.device.rack_slot), 10) || 1;
    // Parse numeric height from strings like '4U' or numbers
    const height = parseInt(String(this.device.height || '1').replace(/[^0-9]/g, ''), 10) || 1;
    // In our RackViewComponent, start is the bottom U number. If your rack_slot is top-based,
    // convert it here. Currently we assume rack_slot is bottom-based.
    const occupied = [{ start: slot, height: height, label: this.device.device_name }];
    console.log('getOccupied()', { slot, height, occupied });
    return occupied;
  }


  onDeviceClick(event: any) {
    console.log("Device click event:", event);

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