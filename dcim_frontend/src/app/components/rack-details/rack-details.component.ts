import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TitleService } from '../../shared/Services/title.service';
import { DynamicRackComponent } from '../../shared/Components/dynamic-rack/dynamic-rack.component';
import { Router } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';

@Component({
  selector: 'app-rack-details',
  standalone: true,
  imports: [CommonModule, DynamicRackComponent],
  templateUrl: './rack-details.component.html',
  styleUrl: './rack-details.component.scss'
})
export class RackDetailsComponent implements OnInit {

  rack = {
    rack_name: 'RACK-001',
    location: 'Mumbai',
    building: 'B1',
    wing: 'A',
    floor: '2',
    data_centre: 'MUM-DC1',
    status: 'Active',
    width_mm: 600,
    height_u: 2,
    device_count: 18,
    space_utilisation: '70%',
    available_space: '12U',
    comments: 'Primary rack for core network aggregation.'
  };

  constructor(private router: Router, private titleService: TitleService) { }

  ngOnInit(): void {
    this.titleService.updateTitle('RACK DETAILS');
  }

  getStatusBadgeClass(): string {
    return `badge-${this.rack.status}`;
  }

  getOccupied() {
    // Interpret rack_slot as bottom-based U (number) or top; adjust as needed
    const slot = parseInt(String(this.rack.rack_name), 10) || 1;
    // Parse numeric height from strings like '4U' or numbers
    const height = parseInt(String(this.rack.height_u || '1').replace(/[^0-9]/g, ''), 10) || 1;
    // In our RackViewComponent, start is the bottom U number. If your rack_slot is top-based,
    // convert it here. Currently we assume rack_slot is bottom-based.
    const occupied = [{ start: slot, height: height, label: this.rack.rack_name }];
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