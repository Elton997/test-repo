import { Component, OnInit, OnDestroy } from '@angular/core';
import { DynamicTableComponent, DynamicFilterField } from '../../shared/Components/dynamic-table/dynamic-table.component';
import { TitleService } from '../../shared/Services/title.service';
import { Menu, SubMenu } from '../../menu.enum';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';
import { PageEvent } from '@angular/material/paginator';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-manufacturers',
  standalone: true,
  imports: [DynamicTableComponent, CommonModule],
  templateUrl: './manufacturers.component.html',
  styleUrl: './manufacturers.component.scss'
})
export class ManufacturersComponent implements OnInit, OnDestroy {

  private loadingTimeout: any;

  constructor(private titleService: TitleService, private router: Router, private listService: ListService) { }
  private subscriptions = new Subscription();
  loading: boolean = false;
  makelist: any = [];
  // pagination variables 
  pageSize = 10;
  offset = 0;
  totalCount = 0;
  appliedFilters: any = {};

  columns = [
    { key: "name", label: "Make", type: "details" },
    { key: "racks", label: "racks" },
    { key: "devices", label: "devices" },
    { key: "models", label: "models" },
    { key: "description", label: "Description" },
    { key: 'actions', label: 'Edit', type: 'edit' }
  ];

  filters: DynamicFilterField[] = [
    {
      key: 'make_name',
      label: 'Make',
      type: 'text',
      placeholder: 'Search by make'
    }
  ];
  ngOnInit(): void {
    this.titleService.updateTitle('MAKE');
    this.loadmakeData();
  }

  loadmakeData(): void {

    try {
      this.loading = true;
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'makes',
          offset: this.offset,
          page_size: this.pageSize,
          ...this.appliedFilters,
        }).subscribe({
          next: (res: any) => {
            try {
              this.makelist = res?.results;
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
    this.loadmakeData();
  }

  onFiltersChanged(filterData: any) {
    this.appliedFilters = filterData;
    this.offset = 0;
    this.loadmakeData();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  handleRowClick(data: any) {
    this.router.navigate([Menu.Device_Management + '/' + SubMenu.Manufacturers, data]);
  }
}
