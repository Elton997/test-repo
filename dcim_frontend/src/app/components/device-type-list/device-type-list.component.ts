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
  selector: 'app-device-type-list',
  standalone: true,
  imports: [DynamicTableComponent, CommonModule],
  templateUrl: './device-type-list.component.html',
  styleUrl: './device-type-list.component.scss'
})
export class DeviceTypeListComponent implements OnInit {

  private loadingTimeout: any;

  constructor(private titleService: TitleService, private router: Router, private listService: ListService) { }
  private subscriptions = new Subscription();
  loading: boolean = false;
  devicetypelist: any = [];

  pageSize = 10;
  offset = 0;
  totalCount = 0;
  appliedFilters: any = {};

  columns = [
    { key: "name", label: "Device Type Name", type: 'details' },
    { key: "make", label: "Make" },
    { key: "u_height", label: "U_height" },
    { key: "description", label: "Description" },
    { key: 'actions', label: 'Edit', type: 'edit' }
  ];

  filters: DynamicFilterField[] = [
    {
      key: 'device_type',
      label: 'Device Type Name',
      type: 'text',
      placeholder: 'Search by device type name'
    },
    {
      key: 'make_name',
      label: 'Make',
      type: 'text',
      placeholder: 'Search by make'
    }
  ];


  ngOnInit(): void {
    this.titleService.updateTitle('DEVICE TYPES');
    this.getdevicetypelist();
  }

  getdevicetypelist(): void {
    try {
      this.loading = true;
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'device_types',
          offset: this.offset,
          page_size: this.pageSize,
          ...this.appliedFilters,
        }).subscribe({
          next: (res: any) => {
            try {
              this.devicetypelist = res?.results;
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
    this.getdevicetypelist();
  }

  onFiltersChanged(filterData: any) {
    this.appliedFilters = filterData;
    this.offset = 0;
    this.getdevicetypelist();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  handleRowClick(data: any) {
    this.router.navigate([Menu.Device_Management + '/' + SubMenu.DeviceTypes, data]);
  }
}
