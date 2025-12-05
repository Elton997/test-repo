import { Component, OnInit, OnDestroy } from '@angular/core';
import { DynamicTableComponent, DynamicFilterField } from '../../shared/Components/dynamic-table/dynamic-table.component';
import { TitleService } from '../../shared/Services/title.service';
import { Router } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';
import { PageEvent } from '@angular/material/paginator';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-device-list',
  standalone: true,
  imports: [DynamicTableComponent, CommonModule],
  templateUrl: './device-list.component.html',
  styleUrl: './device-list.component.scss'
})
export class DeviceListComponent implements OnInit, OnDestroy {

  private loadingTimeout: any;

  constructor(private titleService: TitleService, private router: Router, private listService: ListService) { }

  private subscriptions = new Subscription();
  loading: boolean = false;
  devicelist: any = [];
  // pagination variables 
  pageSize = 10;
  offset = 0;
  totalCount = 0;
  appliedFilters: any = {};

  columns = [
    { key: "name", label: "Device Name", type: "details" },
    { key: "device_type", label: "Device Type" },
    { key: "rack_name", label: "Rack Name" },
    { key: "position", label: "Position" },
    { key: "face", label: "Face" },
    { key: "status", label: "Status", type: "status" },
    { key: "description", label: "Description" },
    { key: "building_name", label: "Building" },
    { key: "wing_name", label: "Wing" },
    { key: "floor_name", label: "Floor" },
    { key: "datacenter_name", label: "Data Center" },
    { key: "height", label: "Height (U)" },
    { key: "model_name", label: "Model Name" },
    { key: "serial_number", label: "Serial Number" },
    { key: "make", label: "Make" },
    { key: "ip_address", label: "IP Address" },
    { key: "po_number", label: "PO Number" },
    { key: "warranty_start_date", label: "Warranty Start Date" },
    { key: "warranty_end_date", label: "Warranty End Date" },
    { key: "amc_start_date", label: "AMC Start Date" },
    { key: "amc_end_date", label: "AMC End Date" },
    { key: "asset_owner", label: "Asset Owner" },
    { key: "asset_user", label: "Asset User" },
    { key: "applications_mapped_name", label: "Application Mapping" },
    { key: "actions", label: "Edit", type: "edit" }
  ];

  filters: DynamicFilterField[] = [
    { key: 'device_name', label: 'Device Name', type: 'text', placeholder: 'Search by device name' },
    { key: 'device_type', label: 'Device Type', type: 'text', placeholder: 'Search by device type' },
    { key: "rack_name", label: "Rack", type: 'text', placeholder: 'Search by rack' },
    { key: 'device_position', label: 'Position', type: 'text', placeholder: 'Search by position' },
    { key: 'device_face', label: 'Face', type: 'text', placeholder: 'Search by face' },
    {
      key: 'device_status', label: 'Status', type: 'select', options: [
        { label: 'Active', value: 'Active' },
        { label: 'Maintenance', value: 'Maintenance' },
        { label: 'Inactive', value: 'Inactive' }
      ]
    },
    { key: 'building_name', label: 'Building', type: 'text', placeholder: 'Search by Building' },
    { key: 'wing_name', label: 'Wing', type: 'text', placeholder: 'Search by wing' },
    { key: 'floor_name', label: 'Floor', type: 'text', placeholder: 'Search by floor' },
    { key: 'datacenter_name', label: 'Data Center', type: 'text', placeholder: 'Search by data center' },
    { key: 'make', label: 'Make', type: 'text', placeholder: 'Search by make' },
    { key: 'ip_address', label: 'IP Address', type: 'text', placeholder: 'Search by IP address' },
    { key: 'po_number', label: 'PO Number', type: 'text', placeholder: 'Search by PO number' },
    { key: 'warranty_start_date', label: 'Warranty Start Date', type: 'date' },
    { key: 'warranty_end_date', label: 'Warranty End Date', type: 'date' },
    { key: 'amc_start_date', label: 'AMC Start Date', type: 'date' },
    { key: 'amc_end_date', label: 'AMC End Date', type: 'date' },
    { key: 'asset_owner', label: 'Asset Owner', type: 'text', placeholder: 'Search by asset owner' },
    { key: 'asset_user', label: 'Asset User', type: 'text', placeholder: 'Search by asset user' },
    { key: 'applications_mapped_name', label: 'Application Mapping', type: 'text', placeholder: 'Search by application' }
  ];

  dashboardLoc: any;
  ngOnInit(): void {
    this.titleService.updateTitle('DEVICES');

    this.dashboardLoc = localStorage.getItem('dashboard_location_name');
    if (this.dashboardLoc) {
      this.appliedFilters = { ...(this.appliedFilters || {}), location_name: this.dashboardLoc };
    }
    console.log(this.appliedFilters)
    this.getdevicelist();
  }

  getdevicelist(): void {
    try {
      this.loading = true;
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'devices',
          offset: this.offset,
          page_size: this.pageSize,
          ...this.appliedFilters,
        }).subscribe({
          next: (res: any) => {
            try {
              this.devicelist = res?.results;
              this.totalCount = res?.total;
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
        }));
    } catch (outerErr) {
      console.error('Unexpected error:', outerErr);
      this.loading = false;
    }
  }

  onPageChange(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.offset = event.pageIndex * this.pageSize;
    this.getdevicelist();
  }

  onFiltersChanged(filterData: any) {
    this.appliedFilters = filterData;
    if (this.dashboardLoc) {
      this.appliedFilters = { ...(this.appliedFilters || {}), location_name: this.dashboardLoc };
    }
    this.offset = 0;
    this.getdevicelist();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  handleRowClick(data: any) {
    this.router.navigate([Menu.Device_Management + '/' + SubMenu.Devices, data]);
  }
}
