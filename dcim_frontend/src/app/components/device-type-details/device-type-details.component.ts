import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TitleService } from '../../shared/Services/title.service';

@Component({
  selector: 'app-device-type-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './device-type-details.component.html',
  styleUrl: './device-type-details.component.scss'
})
export class DeviceTypeDetailsComponent implements OnInit {

  deviceType = {
    type_name: 'Router',
    manufacturer: 'Cisco',
    height_u: 2,
    total_models: 14,
    total_devices: 224,
    comments: 'Core routing device category used in aggregation layers.'
  };

  constructor(private titleService: TitleService) { }

  ngOnInit(): void {
    this.titleService.updateTitle('DEVICE TYPE DETAILS');
  }
}