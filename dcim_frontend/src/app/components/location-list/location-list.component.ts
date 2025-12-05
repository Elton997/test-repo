import { Component, OnInit } from '@angular/core';
import { DynamicTableComponent, DynamicFilterField } from '../../shared/Components/dynamic-table/dynamic-table.component';
import { TitleService } from '../../shared/Services/title.service';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';
import { PageEvent } from '@angular/material/paginator';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-location-list',
  standalone: true,
  imports: [DynamicTableComponent, CommonModule],
  templateUrl: './location-list.component.html',
  styleUrl: './location-list.component.scss'
})
export class LocationListComponent implements OnInit {
  constructor(private titleService: TitleService, private listService: ListService) { }
  private subscriptions = new Subscription();
  loading: boolean = false;
  locations: any = [];
  // pagination variables 
  pageSize = 10; 
  offset = 0;
  totalCount = 0; 
  appliedFilters: any = {};
  columns = [
  { key: "name", label: "Location Name" },
  { key: 'buildings', label: 'No.of Buildings' },
  { key: 'actions', label: 'Edit', type: 'edit' }];

  ngOnInit(): void {
    this.titleService.updateTitle('LOCATIONS');
    this.getLocationList()
  }
  getLocationList(): void {
    try {
      this.loading = true;
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'locations',
          offset: this.offset,
          page_size: this.pageSize,
          ...this.appliedFilters,
        }).subscribe({
          next: (res: any) => {
            try {
              this.locations = res?.results;
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
    { key: 'location_name', label: 'Location Name', type: 'text', placeholder: 'Search by name' }
  ];


  onPageChange(event: PageEvent) {
    this.pageSize = event.pageSize;
    this.offset = event.pageIndex * this.pageSize;
    this.getLocationList();
  }

  onFiltersChanged(filterData: any) {
    this.appliedFilters = filterData;
    this.offset = 0;
    this.getLocationList();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}