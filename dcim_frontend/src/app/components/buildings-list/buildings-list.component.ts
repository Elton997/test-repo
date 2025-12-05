import { Component, OnInit } from '@angular/core';
import { DynamicTableComponent, DynamicFilterField } from '../../shared/Components/dynamic-table/dynamic-table.component';
import { TitleService } from '../../shared/Services/title.service';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';
import { PageEvent } from '@angular/material/paginator';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-buildings-list',
  standalone: true,
  imports: [DynamicTableComponent, CommonModule],
  templateUrl: './buildings-list.component.html',
  styleUrl: './buildings-list.component.scss'
})
export class BuildingsListComponent implements OnInit {

  constructor(private titleService: TitleService, private listService: ListService) { }
  private subscriptions = new Subscription();
  loading: boolean = false;
  buildings: any = [];
  // pagination variables 
  pageSize = 10;
  offset = 0;
  totalCount = 0;
  appliedFilters: any = {};
  columns = [
    { key: 'name', label: 'Building Name' },
    { key: 'location_name', label: 'Location Name' },
    { key: 'status', label: 'Status' },
    { key: 'racks', label: 'Number of Racks' },
    { key: 'devices', label: 'Number of Devices' },
    { key: 'description', label: 'Description' },
    { key: 'actions', label: 'Edit', type: 'edit' }
  ];
  dashboardLoc: any;

  ngOnInit(): void {
    this.titleService.updateTitle('BUILDINGS');
    // If navigated from dashboard, apply that location filter
    this.dashboardLoc = localStorage.getItem('dashboard_location_name');
    if (this.dashboardLoc) {
      this.appliedFilters = { ...(this.appliedFilters || {}), location_name: this.dashboardLoc };
      // keep the stored value so UI can show it; do not remove here so user can navigate back
    }

    this.getBuildings();
  }

  getBuildings(): void {
    try {
      this.loading = true;
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'buildings',
          offset: this.offset,
          page_size: this.pageSize,
          ...this.appliedFilters,
        }).subscribe({
          next: (res: any) => {
            try {
              this.buildings = res?.results;
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

  filterConfig: DynamicFilterField[] = [
    { key: 'buidling_name', label: 'Building Name', type: 'text', placeholder: 'Search by name' }
  ];


  onPageChange(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.offset = event.pageIndex * this.pageSize;
    this.getBuildings();
  }

  onFiltersChanged(filterData: any) {
    this.appliedFilters = filterData;
    this.offset = 0;
    if (this.dashboardLoc) {
      this.appliedFilters = { ...(this.appliedFilters || {}), location_name: this.dashboardLoc };
    }
    this.getBuildings();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}
