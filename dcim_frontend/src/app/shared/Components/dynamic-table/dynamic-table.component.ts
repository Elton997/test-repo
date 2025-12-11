import {
  Component, Input, ViewChild, OnInit, AfterViewInit, OnChanges, SimpleChanges,
  Output, EventEmitter, TemplateRef, OnDestroy, ChangeDetectorRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator, MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule, MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatSelectModule } from '@angular/material/select';
import { MatChipsModule } from '@angular/material/chips';
import { Router } from '@angular/router';
import { Menu, SubMenu } from '../../../menu.enum';
import { LoaderComponent } from '../loader/loader.component';
import { ListService } from '../../../services/list.service';
import { TitleService } from '../../Services/title.service';

export interface DynamicFilterField {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'select' | 'date';
  placeholder?: string;
  options?: Array<{ label: string; value: any }>;
}

interface FilterChip {
  key: string;
  label: string;
  value: any;
  displayValue: string;
}

@Component({
  selector: 'app-dynamic-table',
  standalone: true,
  templateUrl: './dynamic-table.component.html',
  styleUrls: ['./dynamic-table.component.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatPaginatorModule,
    MatTableModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTooltipModule,
    MatCheckboxModule,
    MatDialogModule,
    MatSelectModule,
    MatChipsModule,
    LoaderComponent,
  ]
})
export class DynamicTableComponent implements OnInit, AfterViewInit, OnChanges, OnDestroy {

  @Input() title: string = '';
  @Input() columns: any[] = [];
  @Input() data: any[] = [];
  @Input() pageSize = 10;
  @Input() offset = 0;
  @Input() loading: boolean = false;
  @Input() filterConfig: DynamicFilterField[] = [];
  @Input() appliedFilters: Record<string, any> = {};
  @Input() totalCount: any = 0;
  @Output() rowClick = new EventEmitter<any>();
  @Output() pageChange = new EventEmitter<PageEvent>();
  @Output() filtersChanged = new EventEmitter<Record<string, any>>();
  currentPageIndex: any = 0

  displayedColumns: string[] = [];
  dataSource!: MatTableDataSource<any>;
  @ViewChild(MatPaginator) paginator!: MatPaginator;

  // Filtering state
  filterModel: Record<string, any> = {};
  activeFilters: FilterChip[] = [];
  private filterDialogRef?: MatDialogRef<any>;

  // Column configuration
  configurableColumns: any[] = [];
  pendingSelectedKeys: string[] = [];
  pendingAvailableKeys: string[] = [];
  availableSelection = new Set<string>();
  selectedSelection = new Set<string>();
  private columnDialogRef?: MatDialogRef<any>;

  constructor(
    private router: Router,
    private dialog: MatDialog,
    private cdr: ChangeDetectorRef,
    private listService: ListService,
    private titleService: TitleService

  ) { }

  private get storageKey(): string {
    return `table_columns_${this.title || 'table'}`;
  }

  // ---------------- LIFECYCLE ----------------
  permissions: any = {};
  ngOnInit() {
    this.permissions = JSON.parse(localStorage.getItem('config') || '');
    this.initializeColumnConfiguration();
    this.dataSource = new MatTableDataSource(this.data);
    // in case filterConfig already present on init
    this.initializeFilterModel(true);
  }

  ngAfterViewInit() {
    if (this.paginator) {
      this.dataSource.paginator = this.paginator;

      setTimeout(() => {
        this.paginator.pageIndex = this.currentPageIndex;
      });
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    // data change (parent API updated)
    if (changes['data'] && !changes['data'].firstChange) {
      if (this.dataSource) {
        this.dataSource.data = this.data;
      } else {
        this.dataSource = new MatTableDataSource(this.data);
        this.dataSource.paginator = this.paginator;
      }

      if (this.paginator) {
        this.paginator.pageIndex = this.currentPageIndex;
      }
    }

    // filter config change (parent provides filters)
    if (changes['filterConfig'] && this.filterConfig?.length > 0) {
      this.initializeFilterModel(true);
    }

    // If parent passes applied filters (e.g., after reloading data), hydrate model and rebuild chips
    if (changes['appliedFilters'] && this.appliedFilters) {
      if (this.filterConfig && this.filterConfig.length) {
        // ensure the model has all keys
        this.initializeFilterModel(false);

        // normalize appliedFilters (allow JSON string or object)
        let af: Record<string, any> = {};
        try {
          af = typeof this.appliedFilters === 'string' ? JSON.parse(this.appliedFilters) : (this.appliedFilters || {});
        } catch {
          af = this.appliedFilters || {};
        }

        const afKeys = Object.keys(af || {});

        const findMatchingKey = (targetKey: string) => {
          // exact match
          if (af[targetKey] !== undefined) return targetKey;
          const lower = targetKey.toLowerCase();
          // case-insensitive exact
          for (const k of afKeys) {
            if (k.toLowerCase() === lower) return k;
          }
          // partial match (either contains)
          for (const k of afKeys) {
            const kl = k.toLowerCase();
            if (kl.includes(lower) || lower.includes(kl)) return k;
          }
          return undefined;
        };

        Object.keys(this.filterModel).forEach(k => {
          const match = findMatchingKey(k);
          if (match) {
            this.filterModel[k] = af[match];
          } else {
            this.filterModel[k] = this.filterModel[k] ?? '';
          }
        });

        this.buildActiveFiltersFromModel();
      }
    }

    if (changes['columns'] && !changes['columns'].firstChange) {
      this.initializeColumnConfiguration();
    }
  }

  // ---------------- FILTERING ----------------

  initializeFilterModel(reset = true) {
    if (!this.filterConfig || this.filterConfig.length === 0) {
      return;
    }

    const newModel: any = {};
    this.filterConfig.forEach(f => {
      newModel[f.key] = reset ? '' : (this.filterModel[f.key] ?? '');
    });

    this.filterModel = newModel;
  }

  applyFilters(): void {
    this.activeFilters = [];

    for (const key of Object.keys(this.filterModel)) {
      const value = this.filterModel[key];

      if (value !== '' && value !== null && value !== undefined) {
        const config = this.filterConfig.find(f => f.key === key);
        const displayValue = this.getDisplayValue(config, value);

        this.activeFilters.push({
          key,
          label: config?.label || key,
          displayValue,
          value
        });
      }
    }

    // Build clean payload for parent / API
    const payload: Record<string, any> = { ...this.filterModel };
    Object.keys(payload).forEach(k => {
      if (payload[k] === '' || payload[k] === null || payload[k] === undefined) {
        delete payload[k];
      }
    });
    this.closeFilterDialog();
    this.filtersChanged.emit(payload);
    this.cdr.detectChanges();
  }

  openFilterDialog(templateRef: TemplateRef<any>): void {
    this.filterDialogRef = this.dialog.open(templateRef, {
      width: '600px',
      maxWidth: '90vw'
    });
  }

  closeFilterDialog(): void {
    if (this.filterDialogRef) {
      this.filterDialogRef.close();
    }
  }

  removeFilter(key: string): void {
    this.filterModel[key] = '';
    this.applyFilters();
  }

  resetFilters(): void {
    this.initializeFilterModel(true);
    this.activeFilters = [];
    this.filtersChanged.emit({});
    this.cdr.detectChanges();
  }

  private getDisplayValue(filter: DynamicFilterField | undefined, value: any): string {
    if (!filter) return String(value);
    if (filter.type === 'select') {
      const opt = filter.options?.find(o => o.value === value);
      return opt ? opt.label : String(value);
    }
    return String(value);
  }

  private buildActiveFiltersFromModel(): void {
    this.activeFilters = [];

    for (const key of Object.keys(this.filterModel)) {
      const value = this.filterModel[key];

      if (value !== '' && value !== null && value !== undefined) {
        const config = this.filterConfig.find(f => f.key === key);
        const displayValue = this.getDisplayValue(config, value);

        this.activeFilters.push({
          key,
          label: config?.label || key,
          displayValue,
          value
        });
      }
    }

    // ensure template updates
    this.cdr.detectChanges();
  }

  // ---------------- COLUMNS CONFIG ----------------

  initializeColumnConfiguration() {
    if (typeof window === 'undefined' || !window?.localStorage) {
      this.setDefaultColumns();
      this.updateDisplayedColumns();
      return;
    }

    const saved = localStorage.getItem(this.storageKey);

    if (saved) {
      try {
        const savedConfig = JSON.parse(saved);
        this.configurableColumns = this.columns.map((col, index) => {
          const savedCol = savedConfig.find((s: any) => s.key === col.key);
          return {
            ...col,
            visible: savedCol?.visible ?? true,
            order: savedCol?.order ?? index
          };
        });
        this.configurableColumns.sort((a, b) => a.order - b.order);
      } catch {
        this.setDefaultColumns();
      }
    } else {
      this.setDefaultColumns();
    }

    this.updateDisplayedColumns();
  }

  setDefaultColumns() {
    this.configurableColumns = this.columns.map((col, index) => ({
      ...col,
      visible: true,
      order: index
    }));
  }

  updateDisplayedColumns() {
    // Always include a serial number column as the first column (reserved key: _sr)
    const cols = this.configurableColumns
      .filter(col => col.visible)
      .map(col => col.key);

    this.displayedColumns = ['_sr', ...cols.filter(c => c !== '_sr')];
  }

  toggleColumnVisibility(column: any) {
    column.visible = !column.visible;
    this.updateDisplayedColumns();
    this.saveColumnPreferences();
  }

  resetColumnConfiguration() {
    this.setDefaultColumns();
    this.updateDisplayedColumns();
    this.saveColumnPreferences();
  }

  toggleAllColumns(show: boolean) {
    this.configurableColumns.forEach(col => {
      if (col.type !== 'edit') {
        col.visible = show;
      }
    });
    this.updateDisplayedColumns();
    this.saveColumnPreferences();
  }

  getVisibleColumnCount(): number {
    return this.configurableColumns.filter(col => col.visible).length;
  }

  openColumnConfig(templateRef: TemplateRef<any>): void {
    this.resetDialogSelection();
    this.columnDialogRef = this.dialog.open(templateRef, {
      width: '640px',
    });
  }

  resetDialogSelection(): void {
    this.pendingSelectedKeys = this.configurableColumns
      .filter(col => col.visible)
      .map(col => col.key);

    this.pendingAvailableKeys = this.configurableColumns
      .filter(col => !col.visible)
      .map(col => col.key);

    this.availableSelection.clear();
    this.selectedSelection.clear();
  }

  resetDialogToDefaults(): void {
    this.setDefaultColumns();
    this.updateDisplayedColumns();
    this.saveColumnPreferences();
    this.resetDialogSelection();
  }

  getAvailableColumnsForDialog() {
    return this.pendingAvailableKeys
      .map(key => this.configurableColumns.find(col => col.key === key))
      .filter(Boolean);
  }

  getSelectedColumnsForDialog() {
    return this.pendingSelectedKeys
      .map(key => this.configurableColumns.find(col => col.key === key))
      .filter(Boolean);
  }

  toggleAvailableSelection(key: string): void {
    if (this.availableSelection.has(key)) {
      this.availableSelection.delete(key);
    } else {
      this.availableSelection.add(key);
    }
  }

  toggleSelectedSelection(key: string): void {
    if (this.selectedSelection.has(key)) {
      this.selectedSelection.delete(key);
    } else {
      this.selectedSelection.add(key);
    }
  }

  addSelectedColumns(): void {
    if (!this.availableSelection.size) return;

    const toAdd = Array.from(this.availableSelection);

    this.pendingAvailableKeys = this.pendingAvailableKeys.filter(key => !this.availableSelection.has(key));
    this.pendingSelectedKeys = [...this.pendingSelectedKeys, ...toAdd.filter(key => !this.pendingSelectedKeys.includes(key))];

    this.availableSelection.clear();
  }

  removeSelectedColumns(): void {
    if (!this.selectedSelection.size) return;

    const toRemove = Array.from(this.selectedSelection);

    this.pendingSelectedKeys = this.pendingSelectedKeys.filter(key => !this.selectedSelection.has(key));
    this.pendingAvailableKeys = [...this.pendingAvailableKeys, ...toRemove.filter(key => !this.pendingAvailableKeys.includes(key))];

    this.selectedSelection.clear();
  }

  saveDialogSelection(): void {
    const selectedSet = new Set(this.pendingSelectedKeys);

    this.configurableColumns.forEach(col => {
      col.visible = selectedSet.has(col.key);
      col.order = this.pendingSelectedKeys.indexOf(col.key);
    });

    this.configurableColumns.sort((a, b) => a.order - b.order);

    this.updateDisplayedColumns();
    this.saveColumnPreferences();

    if (this.columnDialogRef) {
      this.columnDialogRef.close();
    }
  }

  saveColumnPreferences(): void {
    if (typeof window === 'undefined' || !window?.localStorage) {
      return;
    }
    const payload = this.configurableColumns.map(col => ({
      key: col.key,
      visible: col.visible,
      order: col.order
    }));
    localStorage.setItem(this.storageKey, JSON.stringify(payload));
  }

  // ---------------- OTHER HANDLERS ----------------

  get hasData(): boolean {
    return !!(this.dataSource?.data && this.dataSource.data.length > 0);
  }

  get isEmpty(): boolean {
    return !this.dataSource || !this.dataSource.data || this.dataSource.data.length === 0;
  }

  getStatusClass(status: string): string {
    if (!status) return 'status-default';

    const normalizedStatus = status.toLowerCase().trim();

    if (['active', 'online', 'running', 'enabled', 'up', 'connected'].includes(normalizedStatus)) {
      return 'status-active';
    }

    if (['passive', 'maintenance', 'planned', 'pending', 'standby', 'idle'].includes(normalizedStatus)) {
      return 'status-passive';
    }

    if (['disabled', 'inactive', 'offline', 'down', 'disconnected', 'error', 'failed'].includes(normalizedStatus)) {
      return 'status-disabled';
    }

    return 'status-default';
  }

  getUsedSpacePercent(value: any): number {
    if (value == null || value === undefined) return 0;

    // Handle string percentage like "70%"
    if (typeof value === 'string') {
      const match = value.match(/(\d+(?:\.\d+)?)/);
      if (match) {
        return parseFloat(match[1]);
      }
    }

    // Handle number (assumed to be percentage)
    if (typeof value === 'number') {
      return Math.min(100, Math.max(0, value));
    }

    // Handle object with used_space and available_space or available_space_percent
    if (typeof value === 'object') {
      if (value.used_space !== undefined && value.height !== undefined && value.height > 0) {
        return Math.min(100, Math.max(0, (value.used_space / value.height) * 100));
      }
      if (value.available_space_percent !== undefined) {
        // If we have available_space_percent, used = 100 - available
        return Math.min(100, Math.max(0, 100 - value.available_space_percent));
      }
    }

    return 0;
  }

  getAvailableSpacePercent(value: any): number {
    return 100 - this.getUsedSpacePercent(value);
  }

  getSpaceDisplayValue(value: any): string {
    if (value == null || value === undefined) return '0%';

    // If it's already a string like "70%", return it
    if (typeof value === 'string') {
      return value;
    }

    // If it's a number, format as percentage
    if (typeof value === 'number') {
      return `${Math.round(value)}%`;
    }

    // Handle object with available_space_percent
    if (typeof value === 'object') {
      if (value.available_space_percent !== undefined) {
        return `${Math.round(value.available_space_percent)}%`;
      }
      if (value.used_space !== undefined && value.height !== undefined && value.height > 0) {
        const usedPercent = (value.used_space / value.height) * 100;
        return `${Math.round(usedPercent)}%`;
      }
    }

    return '0%';
  }

  onCLickDetails(data: any) {
    this.rowClick.emit(data);
  }

  onPagination(event: PageEvent) {
    this.currentPageIndex = event.pageIndex;
    this.pageChange.emit(event);
  }

  onImport(event: any) {
    const file = event.target.files?.[0];
    if (!file) return;

    // ---- CSV VALIDATION ----
    const fileName = file.name.toLowerCase();
    const validMimeTypes = [
      "text/csv",
      "application/vnd.ms-excel" // sometimes CSV is detected as Excel MIME
    ];

    if (!fileName.endsWith(".csv") || !validMimeTypes.includes(file.type)) {
      alert("Invalid file type! Please upload a .csv file only.");
      event.target.value = ""; // reset input
      return;
    }
    // ---- END VALIDATION ----

    const entity = this.getEntityFromTitle();
    if (!entity) {
      console.error("Cannot import: unknown entity from title");
      return;
    }

    this.listService.importItems(entity, file).subscribe({
      next: (res) => {
        console.log("Import success:", res);
        alert("Import completed successfully!");
      },
      error: (err) => {
        console.error("Import failed:", err);
        alert("Import failed! Check console for error details.");
      }
    });
  }


  convertJsonToCsv(items: any[]): string {
    if (!items || !items.length) return '';

    const headers = Object.keys(items[0]).join(',');

    const rows = items.map(row =>
      Object.values(row)
        .map(v => `"${v ?? ''}"`)
        .join(',')
    );

    return [headers, ...rows].join('\n');
  }

  downloadCsv(csv: string, entity: string) {
    const blob = new Blob([csv], { type: 'text/csv' });
    this.downloadBlob(blob, `${entity}.csv`);
  }

  downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    const timestamp = new Date().toISOString()?.replace(/[:.]/g, '-');

    a.href = url;
    a.download = `${filename?.replace('.csv', '')}_${timestamp}.csv`;
    a.click();

    URL.revokeObjectURL(url);
  }

  exportCSV() {
    const entity = this.getEntityFromTitle();
    if (!entity) return;

    this.listService.exportItems(entity, this.appliedFilters).subscribe({
      next: (blob: Blob) => {

        // Detect JSON
        if (blob.type.includes("application/json")) {
          blob.text().then(jsonText => {
            const json = JSON.parse(jsonText);

            // Convert JSON to CSV
            const csv = this.convertJsonToCsv(json.results || json.data || json);

            // Download CSV
            this.downloadCsv(csv, entity);
          });
        } else {
          // Backend returned CSV (just in case)
          this.downloadBlob(blob, `${entity}.csv`);
        }
      },
      error: err => console.error("Export failed:", err)
    });
  }



  getEntityFromTitle(): string {
    const title = (this.titleService.currentTitle || '').toLowerCase().trim();

    switch (title) {
      case 'racks': return 'racks';
      case 'devices': return 'devices';
      case 'device types': return 'device_types';
      case 'models': return 'models';
      case 'make': return 'makes';
      case 'locations': return 'locations';
      case 'buildings': return 'buildings';
      case 'floors': return 'floors';
      case 'wings': return 'wings';
      case 'datacenters': return 'datacenters';
    }
    return '';
  }


  ngOnDestroy(): void {
    if (typeof window !== 'undefined' && window?.localStorage) {
      localStorage.removeItem(this.storageKey);
    }
  }

  onAdd() {
    if (this.title == 'Racks') {
      this.router.navigate([Menu.Rack_Management + '/' + SubMenu.Racks + '/add']);
    } else if (this.title == 'Devices') {
      this.router.navigate([Menu.Device_Management + '/' + SubMenu.Devices + '/add']);
    } else if (this.title == 'Device Types') {
      this.router.navigate([Menu.Device_Management + '/' + SubMenu.DeviceTypes + '/add']);
    } else if (this.title == 'Locations') {
      this.router.navigate([Menu.Organization + '/' + SubMenu.Locations + '/add']);
    } else if (this.title == 'Buildings') {
      this.router.navigate([Menu.Organization + '/' + SubMenu.Buildings + '/add']);
    } else if (this.title == 'Models') {
      this.router.navigate([Menu.Device_Management + '/' + SubMenu.Models + '/add']);
    } else if (this.title == 'Make') {
      this.router.navigate([Menu.Device_Management + '/' + SubMenu.Manufacturers + '/add']);
    }
  }

  onEdit(row: any) {
    if (this.title == 'Racks') {
      this.router.navigate(
        [Menu.Rack_Management + '/' + SubMenu.Racks + '/edit', row?.name],
        { state: row }
      );
    } else if (this.title == 'Devices') {
      this.router.navigate(
        [Menu.Device_Management + '/' + SubMenu.Devices + '/edit', (row?.name || row?.Device_name)],
        { state: row }
      );
    } else if (this.title == 'Device Types') {
      this.router.navigate(
        [Menu.Device_Management + '/' + SubMenu.DeviceTypes + '/edit', (row?.name || row?.device_type || row?.device_name)],
        { state: row }
      );
    } else if (this.title == 'Locations') {
      this.router.navigate(
        [Menu.Organization + '/' + SubMenu.Locations + '/edit', row?.location_id],
        { state: row }
      );
    } else if (this.title == 'Buildings') {
      this.router.navigate(
        [Menu.Organization + '/' + SubMenu.Buildings + '/edit', row?.building_id],
        { state: row }
      );
    } else if (this.title == 'Make') {
      this.router.navigate(
        [Menu.Device_Management + '/' + SubMenu.Manufacturers + '/edit', row?.name],
        { state: row }
      );
    } else if (this.title == 'Models') {
      this.router.navigate(
        [Menu.Device_Management + '/' + SubMenu.Models + '/edit', row?.name],
        { state: row }
      );
    }
  }
}
