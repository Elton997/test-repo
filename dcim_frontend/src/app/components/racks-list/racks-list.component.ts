import { Component, OnInit, OnDestroy } from '@angular/core';
import { DynamicTableComponent, DynamicFilterField } from '../../shared/Components/dynamic-table/dynamic-table.component';
import { Router } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';
import { TitleService } from '../../shared/Services/title.service';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';
import { PageEvent } from '@angular/material/paginator';
@Component({
  selector: 'app-racks-list',
  standalone: true,
  imports: [DynamicTableComponent],
  templateUrl: './racks-list.component.html',
  styleUrl: './racks-list.component.scss'
})
export class RacksListComponent implements OnInit, OnDestroy {
  constructor(private router: Router, private titleService: TitleService, private listService: ListService) { }

  private subscriptions = new Subscription();
  loading: boolean = false;
  racks: any = [];
  // pagination variables 
  pageSize = 10;
  offset = 0;
  totalCount = 0;
  appliedFilters: any = {};

  columns = [
    { key: 'name', label: 'Rack Name', type: 'details' },
    { key: 'building_name', label: 'Building' },
    { key: 'wing_name', label: 'Wing' },
    { key: 'floor_name', label: 'Floor' },
    { key: 'datacenter_name', label: 'Data Centre' },
    { key: 'status', label: 'Status', type: 'status' },
    { key: 'height', label: 'Height (U)' },
    { key: 'devices', label: 'No. of Devices' },
    { key: 'used_space', label: 'Used Space' },
    { key: 'available_space', label: 'Available Space' },
    { key: 'available_space_percent', label: 'Available Space(%)' },
    { key: 'actions', label: 'Edit', type: 'edit' }
  ];

  filters: DynamicFilterField[] = [
    { key: 'building_name', label: 'Building', type: 'text', placeholder: 'Search by building' },
    { key: 'wing_name', label: 'Wing', type: 'text', placeholder: 'Search by wing' },
    { key: 'floor_name', label: 'Floor', type: 'text', placeholder: 'Search by floor' },
    { key: 'datacenter_name', label: 'Data Centre', type: 'text', placeholder: 'Search by data centre' },
    {
      key: 'rack_status', label: 'Status', type: 'select', options: [
        { label: 'Active', value: 'active' },
        { label: 'Inactive', value: 'inactive' }
      ]
    },
    { key: 'rack_height', label: 'Rack Height', type: 'text', placeholder: 'Search by rack height' },

   
  ];
  dashboardLoc:any

  ngOnInit(): void {
    this.titleService.updateTitle('RACKS');
    this.dashboardLoc = localStorage.getItem('dashboard_location_name');
    if (this.dashboardLoc) {
      this.appliedFilters = { ...(this.appliedFilters || {}), location_name: this.dashboardLoc };
    }

    this.loadRackData();
  }

  loadRackData(): void {
    try {
      this.loading = true;
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'racks',
          offset: this.offset,
          page_size: this.pageSize,
          ...this.appliedFilters,
        }).subscribe({
          next: (res: any) => {
            try {
              this.racks = res?.results;
              this.totalCount = res?.total;
              this.loading = false
            } catch (innerErr) {
              console.error('Error processing result:', innerErr);
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
    this.loadRackData();
  }

  onFiltersChanged(filterData: any) {
    this.appliedFilters = filterData;
    if (this.dashboardLoc) {
      this.appliedFilters = { ...(this.appliedFilters || {}), location_name: this.dashboardLoc };
    }
    this.offset = 0;
    this.loadRackData();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }


  handleRowClick(data: any) {
    this.router.navigate([Menu.Rack_Management + '/' + SubMenu.Racks, data]);
  }
}