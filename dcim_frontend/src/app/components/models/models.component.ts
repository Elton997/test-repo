import { Component, OnInit } from '@angular/core';
import { TitleService } from '../../shared/Services/title.service';
import { Subscription } from 'rxjs';
import { Router } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';
import { ListService } from '../../services/list.service';
import { PageEvent } from '@angular/material/paginator';
import { CommonModule } from '@angular/common';
import { DynamicTableComponent, DynamicFilterField } from '../../shared/Components/dynamic-table/dynamic-table.component';

@Component({
  selector: 'app-models',
  standalone: true,
  imports: [DynamicTableComponent, CommonModule],
  templateUrl: './models.component.html',
  styleUrl: './models.component.scss'
})
export class ModelsComponent implements OnInit {

  constructor(private titleService: TitleService, private router: Router, private listService: ListService) { }

  private subscriptions = new Subscription();
  loading: boolean = false;
  modellist: any = [];
  // pagination variables 
  pageSize = 10;
  offset = 0;
  totalCount = 0;
  appliedFilters: any = {};

  columns = [
    { key: "name", label: "Model Name", type: "details" },
    { key: "make_name", label: "Make" },
    { key: "device_type", label: "Device Type" },
    { key: "height", label: "Height (U)" },
    { key: "description", label: "Description" },
    { key: "actions", label: "Edit", type: "edit" }
  ];

  filters: DynamicFilterField[] = [
    {
      key: 'model_name',
      label: 'Model Name',
      type: 'text',
      placeholder: 'Search by model name'
    },
    {
      key: 'make_name',
      label: 'Make',
      type: 'text',
      placeholder: 'Search by make'
    },
    {
      key: 'device_type',
      label: 'Device Type Name',
      type: 'text',
      placeholder: 'Search by device type name'
    },
    {
      key: 'model_height',
      label: 'Height',
      type: 'text',
      placeholder: 'Search by height'
    }
  ];


  ngOnInit(): void {
    this.titleService.updateTitle('MODELS');
    this.loadmodeldata();
  }

  loadmodeldata(): void {

    try {
      this.loading = true;
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'models',
          offset: this.offset,
          page_size: this.pageSize,
          ...this.appliedFilters,
        }).subscribe({
          next: (res: any) => {
            try {
              this.modellist = res?.results;
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
    this.loadmodeldata();
  }

  onFiltersChanged(filterData: any) {
    this.appliedFilters = filterData;
    this.offset = 0;
    this.loadmodeldata();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  handleRowClick(data: any) {
    this.router.navigate([Menu.Device_Management + '/' + SubMenu.Models, data]);
  }

}
