
import { Component, OnInit, ViewChild, ElementRef, Inject, PLATFORM_ID, OnDestroy } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatTreeModule, MatTreeNestedDataSource } from '@angular/material/tree';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { NestedTreeControl } from '@angular/cdk/tree';
import { environment } from '../../../environments/environment';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { TitleService } from '../../shared/Services/title.service';
import { HierarchyStateService } from '../../shared/Services/hierarchy-state.service';
import { MatTabsModule } from '@angular/material/tabs';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Menu, SubMenu } from '../../menu.enum';
import { Observable } from 'rxjs';
import { map, startWith } from 'rxjs/operators';
import Chart from 'chart.js/auto';
import { MatMenuModule } from '@angular/material/menu';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import {
    CdkDragDrop,
    CdkDropList,
    CdkDrag,
    CdkDragHandle,
    moveItemInArray
} from '@angular/cdk/drag-drop';

interface LocationNode {
    id: number;
    name: string;
    type: string;
    children?: LocationNode[];
    // Capacity info
    used_space?: number;
    total_space?: number; // Added to aggregate capacity at higher levels
    // Rack specific
    status?: string;
    height?: number;
    available_space?: number;
    devices?: number;
}

interface SpaceStats {
    total_space: number;
    used_space: number;
    used_space_percent: number;
    unit: string;
}

interface DeviceStats {
    total_devices: number;
    active_devices: number;
    inactive_devices: number;
}

interface DeviceTypeBreakdown {
    device_type: string;
    count: number;
}

interface OverviewCounts {
    buildings?: number;
    wings?: number;
    floors?: number;
    datacenters?: number;
    racks?: number;
    devices?: number;
}

interface OverviewResponse {
    location_name: string;
    entity_type: string;
    counts?: OverviewCounts;
    space_stats: SpaceStats;
    device_stats?: DeviceStats;
    device_type_breakdown?: DeviceTypeBreakdown[];
    // Properties
    address?: string;
    height?: number;
    status?: string;
}

interface RackSimple {
    id: number;
    name: string;
    status: string;
    space_used: number;
    space_available: number;
    height?: number;
}

interface DatacenterSimple {
    id: number;
    name: string;
    racks: RackSimple[];
}

interface FloorLayoutResponse {
    id: number;
    name: string;
    datacenters: DatacenterSimple[];
}

interface DashboardWidget {
    id: string; // 'capacity', 'status', 'distribution', 'planning'
    title: string;
    colSpan: number; // 1 or 2 (or more if needed)
}

@Component({
    selector: 'app-hierarchy',
    standalone: true,
    imports: [
        CommonModule,
        MatTabsModule,
        MatTreeModule,
        MatIconModule,
        MatButtonModule,
        MatCardModule,
        MatProgressSpinnerModule,
        RouterModule,
        FormsModule,
        ReactiveFormsModule,
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        MatAutocompleteModule,
        MatTooltipModule,
        MatMenuModule,
        MatDatepickerModule,
        MatNativeDateModule,
        CdkDropList,
        CdkDrag,
        CdkDragHandle
    ],
    templateUrl: './hierarchy.component.html',
    styleUrls: ['./hierarchy.component.scss']
})
export class HierarchyComponent implements OnInit, OnDestroy {
    treeControl = new NestedTreeControl<LocationNode>(node => node.children);
    dataSource = new MatTreeNestedDataSource<LocationNode>();

    selectedNode: LocationNode | null = null;
    isLoading = true;

    // Search & Filter Properties
    searchQuery = '';
    sortOption = 'name_asc'; // name_asc, name_desc, type
    filterType = 'all';

    // Global Search Properties
    globalSearchControl = new FormControl('');
    filteredGlobalOptions: Observable<LocationNode[]> | undefined;

    // Overview API data
    overviewData: OverviewResponse | null = null;
    isOverviewLoading = false;

    // Floorplan Data
    floorplanData: FloorLayoutResponse | null = null;
    isFloorplanLoading = false;
    isFullscreen = false; // Fullscreen state

    // Chart.js for device type breakdown
    private _deviceTypeChartRef?: ElementRef<HTMLCanvasElement>;

    @ViewChild('deviceTypeChart')
    set deviceTypeChartRef(ref: ElementRef<HTMLCanvasElement> | undefined) {
        this._deviceTypeChartRef = ref;
        if (ref) {
            this.updateDeviceTypeChart();
        }
    }

    private deviceTypeChart?: Chart;

    @ViewChild('floorplanContainer') floorplanContainer!: ElementRef;

    // Dashboard Widgets State
    widgets: DashboardWidget[] = [
        { id: 'capacity', title: 'Capacity Utilization', colSpan: 1 },
        { id: 'status', title: 'Device Status', colSpan: 1 },
        { id: 'distribution', title: 'Distribution by Type', colSpan: 1 },
        { id: 'planning', title: 'Resource Planning', colSpan: 1 }
    ];

    constructor(
        private http: HttpClient,
        private router: Router,
        private route: ActivatedRoute,
        private titleService: TitleService,
        private stateService: HierarchyStateService,
        @Inject(PLATFORM_ID) private platformId: Object
    ) {
        this.loadDashboardState();
    }

    // Helpers for Resource Planning Widget
    get availableSpace(): number {
        if (!this.overviewData?.space_stats) return 0;
        return this.overviewData.space_stats.total_space - this.overviewData.space_stats.used_space;
    }

    get avgDensity(): string {
        const racks = this.overviewData?.counts?.racks || 0;
        const devices = this.overviewData?.device_stats?.total_devices || 0;
        if (racks === 0) return 'N/A';
        return (devices / racks).toFixed(1);
    }

    get expansionPotential(): number {
        // Assuming standard 2U servers
        return Math.floor(this.availableSpace / 2);
    }

    ngOnInit(): void {
        this.titleService.updateTitle('BUILDINGS');
        this.loadHierarchy();

        // Listen for fullscreen changes (ESC key or browser UI)
        if (isPlatformBrowser(this.platformId)) {
            document.addEventListener('fullscreenchange', this.onFullscreenChange);
            document.addEventListener('webkitfullscreenchange', this.onFullscreenChange);
            document.addEventListener('mozfullscreenchange', this.onFullscreenChange);
            document.addEventListener('MSFullscreenChange', this.onFullscreenChange);
        }

        // Subscribe to expansion changes to save state
        this.treeControl.expansionModel.changed.subscribe(change => {
            const expandedIds = new Set<number>();
            this.treeControl.expansionModel.selected.forEach(node => expandedIds.add(node.id));
            this.stateService.setExpanded(expandedIds);
        });

        this.filteredGlobalOptions = this.globalSearchControl.valueChanges.pipe(
            startWith(''),
            map(value => {
                const searchVal = value as string | LocationNode;
                const name = typeof searchVal === 'string' ? searchVal : searchVal?.name;
                return name ? this._filterGlobals(name as string) : [];
            })
        );
    }

    ngOnDestroy(): void {
        if (isPlatformBrowser(this.platformId)) {
            if (this.deviceTypeChart) {
                this.deviceTypeChart.destroy();
            }
            document.removeEventListener('fullscreenchange', this.onFullscreenChange);
            document.removeEventListener('webkitfullscreenchange', this.onFullscreenChange);
            document.removeEventListener('mozfullscreenchange', this.onFullscreenChange);
            document.removeEventListener('MSFullscreenChange', this.onFullscreenChange);
        }
    }

    private onFullscreenChange = (): void => {
        const isFullscreenNow = !!document.fullscreenElement ||
            !!(document as any).webkitFullscreenElement ||
            !!(document as any).mozFullScreenElement ||
            !!(document as any).msFullscreenElement;

        if (this.isFullscreen !== isFullscreenNow) {
            this.isFullscreen = isFullscreenNow;
        }
    }

    displayFn(node: LocationNode): string {
        return node && node.name ? node.name : '';
    }

    private _filterGlobals(name: string): LocationNode[] {
        const filterValue = name.toLowerCase();
        const results: LocationNode[] = [];

        if (!this.dataSource.data) return [];

        const searchNodes = (nodes: LocationNode[]) => {
            for (const node of nodes) {
                if (node.name.toLowerCase().includes(filterValue)) {
                    results.push(node);
                }
                if (node.children) {
                    searchNodes(node.children);
                }
            }
        };

        searchNodes(this.dataSource.data);
        return results.slice(0, 50); // Limit results to 50 for performance
    }

    onGlobalOptionSelected(event: any): void {
        const node = event.option.value as LocationNode;
        if (node) {
            this.selectNode(node);
        }
    }

    getNodeIcon(type: string): string {
        switch (type) {
            case 'Organization': return 'domain';
            case 'Location': return 'location_city';
            case 'Building': return 'business';
            case 'Wing': return 'meeting_room';
            case 'Floor': return 'layers';
            case 'Datacenter': return 'storage';
            case 'Rack': return 'dns';
            default: return 'help_outline';
        }
    }

    loadHierarchy(): void {
        this.isLoading = true;
        this.http.get<LocationNode[]>(`${environment.apiUrl}/api/dcim/hierarchy`)
            .subscribe({
                next: (data) => {
                    let buildings = data.flatMap(location => location.children || []);

                    const dashboardLoc = localStorage.getItem('dashboard_location_name');
                    if (dashboardLoc) {
                        const filteredLocations = data.filter(loc => loc.name === dashboardLoc);
                        if (filteredLocations.length > 0) {
                            buildings = filteredLocations.flatMap(location => location.children || []);
                        } else {
                            buildings = [];
                        }
                    } else {
                        // All Buildings mode
                        if (!this.stateService.getSelected()) {
                            this.selectedNode = null;
                            this.stateService.setSelected(null);
                            this.stateService.setExpanded(new Set());
                            this.treeControl.collapseAll();
                        }
                    }

                    this.dataSource.data = buildings;

                    // Restore selection from URL if present
                    const nodeIdInUrl = this.route.snapshot.queryParamMap.get('node');
                    if (nodeIdInUrl) {
                        const nodeId = parseInt(nodeIdInUrl, 10);
                        const node = this.findNodeById(buildings, nodeId);
                        if (node) {
                            // Expand parents? (Optional, requires parent map or recursive expansion)
                            this.selectNode(node, false); // Pass false to avoid updating URL again
                        }
                    } else if (this.stateService.getSelected()) {
                        // Fallback to service state if no URL param (legacy)
                        // logic existing...
                        // Actually, existing logic for state restoration was weak.
                        // Let's stick to URL param as the primary source of truth.
                    }

                    // Always try to restore state if available, or if dashboardLoc dictates it
                    if (dashboardLoc || this.stateService.getSelected()) {
                        if (dashboardLoc) {
                            this.titleService.setLoc(dashboardLoc);
                        } else {
                            this.titleService.setLoc('All Buildings');
                        }
                        this.restoreState();
                    } else {
                        // All Buildings mode default
                        this.titleService.setLoc('All Buildings');
                    }

                    this.isLoading = false;
                },
                error: (err) => {
                    console.error('Failed to load hierarchy', err);
                    this.isLoading = false;
                }
            });
    }

    restoreState(): void {
        const expandedIds = this.stateService.getExpanded();
        const selectedState = this.stateService.getSelected();

        const restoreNode = (nodes: LocationNode[]) => {
            for (const node of nodes) {
                if (expandedIds.has(node.id)) {
                    this.treeControl.expand(node);
                }
                // Check both ID and Type to avoid ID collisions (e.g. Rack ID 5 vs Building ID 5)
                if (selectedState && node.id === selectedState.id && node.type === selectedState.type) {
                    this.selectedNode = node;
                    this.loadOverview(node);
                }
                if (node.children) {
                    restoreNode(node.children);
                }
            }
        };

        if (this.dataSource.data) {
            restoreNode(this.dataSource.data);
        }
    }

    hasChild = (_: number, node: LocationNode) => !!node.children && node.children.length > 0;

    selectNode(node: LocationNode, updateUrl: boolean = true): void {
        if (node.type === 'Device') {
            // Navigate to Device Details
            this.router.navigate([Menu.Device_Management, SubMenu.Devices, node.name]);

            // For state persistence: Save the PARENT RACK as the selected node
            const path = this.findPath(this.dataSource.data, node);
            if (path && path.length >= 2) {
                const parentRack = path[path.length - 2];
                this.selectedNode = parentRack;
                this.stateService.setSelected(parentRack.id, parentRack.type);
                this.expandParents(parentRack);
            } else {
                // Fallback
                this.selectedNode = node;
                this.stateService.setSelected(node.id, node.type);
                this.expandParents(node);
            }
        } else {
            this.selectedNode = node;
            this.stateService.setSelected(node.id, node.type);
            this.isFullscreen = false; // Reset fullscreen on new selection

            if (updateUrl) {
                this.router.navigate([], {
                    relativeTo: this.route,
                    queryParams: { node: node.id },
                    queryParamsHandling: 'merge'
                });
            }

            // Auto-expand the tree to show this node
            this.expandParents(node);
        }

        // Load overview stats for the selected node
        if (node.type !== 'Device') {
            this.loadOverview(node);
        }
    }

    viewRackLayout(): void {
        if (this.selectedNode && this.selectedNode.type === 'Rack') {
            this.router.navigate([Menu.Rack_Management, SubMenu.Racks, this.selectedNode.name]);
        }
    }

    expandParents(node: LocationNode): void {
        const path = this.findPath(this.dataSource.data, node);
        if (path) {
            path.forEach(parent => this.treeControl.expand(parent));
        }
    }

    findPath(nodes: LocationNode[], target: LocationNode): LocationNode[] | null {
        for (const node of nodes) {
            if (node === target) {
                return [node];
            }
            if (node.children) {
                const childPath = this.findPath(node.children, target);
                if (childPath) {
                    return [node, ...childPath];
                }
            }
        }
        return null;
    }

    private mapEntityType(nodeType: string): string {
        switch (nodeType) {
            case 'Location':
                return 'location';
            case 'Building':
                return 'building';
            case 'Wing':
                return 'wing';
            case 'Floor':
                return 'floor';
            case 'Datacenter':
                return 'datacenter';
            case 'Rack':
                return 'rack';
            default:
                return 'rack';
        }
    }

    loadOverview(node: LocationNode): void {
        if (!node?.name || !node?.type) {
            this.overviewData = null;
            return;
        }

        const entityType = this.mapEntityType(node.type);
        const encodedName = encodeURIComponent(node.name);

        let hierarchyParams: { [key: string]: string } = {};
        hierarchyParams = this.buildHierarchyParams(node);
        this.isOverviewLoading = true;

        this.http.get<OverviewResponse>(
            `${environment.apiUrl}/api/dcim/overview/${encodedName}`,
            {
                params: {
                    entity_type: entityType,
                    ...hierarchyParams
                }
            }
        ).subscribe({
            next: (data) => {
                this.overviewData = data;
                this.isOverviewLoading = false;
                this.updateDeviceTypeChart();
            },
            error: (err) => {
                console.error('Failed to load overview data', err);
                this.overviewData = null;
                this.isOverviewLoading = false;

                if (this.deviceTypeChart) {
                    this.deviceTypeChart.destroy();
                    this.deviceTypeChart = undefined;
                }
            }
        });

        // Also load floorplan if it's a floor
        if (node.type === 'Floor') {
            this.loadFloorplan(node.id);
        } else {
            this.floorplanData = null;
        }
    }

    loadFloorplan(floorId: number): void {
        this.isFloorplanLoading = true;
        this.http.get<FloorLayoutResponse>(`${environment.apiUrl}/api/dcim/floors/${floorId}/floorplan`)
            .subscribe({
                next: (data) => {
                    this.floorplanData = data;
                    // Pre-process aisles to avoid infinite loop in template
                    if (this.floorplanData && this.floorplanData.datacenters) {
                        (this.floorplanData as any).datacenters = this.floorplanData.datacenters.map(dc => ({
                            ...dc,
                            aisles: this.chunkRacks(dc.racks, 5)
                        }));
                    }
                    this.isFloorplanLoading = false;
                },
                error: (err) => {
                    console.error('Failed to load floorplan', err);
                    this.floorplanData = null;
                    this.isFloorplanLoading = false;
                }
            });
    }

    toggleFullscreen(): void {
        this.isFullscreen = !this.isFullscreen;

        // Use browser Fullscreen API on the specific element
        if (this.isFullscreen && this.floorplanContainer) {
            const elem = this.floorplanContainer.nativeElement;
            if (elem.requestFullscreen) {
                elem.requestFullscreen();
            } else if ((elem as any).webkitRequestFullscreen) { /* Safari */
                (elem as any).webkitRequestFullscreen();
            } else if ((elem as any).msRequestFullscreen) { /* IE11 */
                (elem as any).msRequestFullscreen();
            }
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if ((document as any).webkitExitFullscreen) { /* Safari */
                (document as any).webkitExitFullscreen();
            } else if ((document as any).msExitFullscreen) { /* IE11 */
                (document as any).msExitFullscreen();
            }
        }
    }

    navigateToRack(rack: RackSimple): void {
        this.router.navigate([Menu.Rack_Management, SubMenu.Racks, rack.name]);
    }


    private buildHierarchyParams(node: LocationNode): { [key: string]: string } {
        const params: { [key: string]: string } = {};

        const location = localStorage.getItem('dashboard_location_name');
        if (location) {
            params['location'] = location;
        }

        const path = this.findPath(this.dataSource.data, node);
        if (!path) return params;
        for (const n of path) {
            if (n === node) break;
            switch (n.type) {
                case 'Building':
                    params['building'] = n.name;
                    break;
                case 'Wing':
                    params['wing'] = n.name;
                    break;
                case 'Floor':
                    params['floor'] = n.name;
                    break;
                case 'Datacenter':
                    params['datacenter'] = n.name;
                    break;
            }
        }

        return params;
    }

    // Chart.js update logic

    private updateDeviceTypeChart(): void {
        if (!isPlatformBrowser(this.platformId)) {
            return;
        }

        if (!this.overviewData || !this.overviewData.device_type_breakdown) {
            if (this.deviceTypeChart) {
                this.deviceTypeChart.destroy();
                this.deviceTypeChart = undefined;
            }
            return;
        }

        if (!this._deviceTypeChartRef) {
            // Canvas not available yet, wait for ViewChild setter
            return;
        }

        const labels = this.overviewData.device_type_breakdown.map(d => d.device_type);
        const data = this.overviewData.device_type_breakdown.map(d => d.count);

        const ctx = this._deviceTypeChartRef.nativeElement.getContext('2d');
        if (!ctx) {
            return;
        }

        if (this.deviceTypeChart) {
            this.deviceTypeChart.destroy();
        }

        this.deviceTypeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Devices',
                        data,
                        backgroundColor: '#3b82f6',
                        hoverBackgroundColor: '#1d4ed8',
                        borderRadius: 4,
                        maxBarThickness: 32,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#f1f5f9',
                        bodyColor: '#f1f5f9',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: {
                            family: "'Inter', sans-serif",
                            size: 13
                        },
                        bodyFont: {
                            family: "'Inter', sans-serif",
                            size: 13
                        },
                        displayColors: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                family: "'Inter', sans-serif",
                                size: 11
                            }
                        },
                        border: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#e2e8f0',
                            // drawBorder: false, // Chart.js v4 migration (if needed later) or border prop
                        },
                        border: {
                            dash: [4, 4],
                            display: false
                        },
                        ticks: {
                            precision: 0,
                            color: '#64748b',
                            font: {
                                family: "'Inter', sans-serif",
                                size: 11
                            }
                        }
                    }
                }
            }
        });
    }

    // Note: children list and filters have been removed from the UI,
    // so helper getters for filtered children/types are no longer needed.

    // Dashboard State Management
    loadDashboardState(): void {
        if (!isPlatformBrowser(this.platformId)) return;

        const savedState = localStorage.getItem('hierarchy_dashboard_layout');
        if (savedState) {
            try {
                const parsedState = JSON.parse(savedState) as DashboardWidget[];
                // Merge with default to ensure all widgets exist (in case of updates)
                const savedMap = new Map(parsedState.map(w => [w.id, w]));

                const newWidgets: DashboardWidget[] = [];

                // 1. Add widgets that are in saved state AND valid
                parsedState.forEach(savedW => {
                    const validWidget = this.widgets.find(w => w.id === savedW.id);
                    if (validWidget) {
                        newWidgets.push({ ...validWidget, colSpan: savedW.colSpan || validWidget.colSpan });
                    }
                });

                // 2. Append new widgets that weren't in saved state
                this.widgets.forEach(defaultW => {
                    if (!savedMap.has(defaultW.id)) {
                        newWidgets.push(defaultW);
                    }
                });

                this.widgets = newWidgets;

            } catch (e) {
                console.warn('Failed to parse dashboard state', e);
            }
        }
    }

    saveDashboardState(): void {
        if (!isPlatformBrowser(this.platformId)) return;
        localStorage.setItem('hierarchy_dashboard_layout', JSON.stringify(this.widgets));
    }

    drop(event: CdkDragDrop<string[]>): void {
        moveItemInArray(this.widgets, event.previousIndex, event.currentIndex);
        this.saveDashboardState();
        setTimeout(() => this.updateDeviceTypeChart(), 100);
    }

    resizeWidget(widget: DashboardWidget): void {
        if (widget.colSpan === 1) {
            widget.colSpan = 2;
        } else {
            widget.colSpan = 1;
        }
        this.saveDashboardState();
        setTimeout(() => this.updateDeviceTypeChart(), 100);
    }

    // Aisle layout helper
    chunkRacks(racks: RackSimple[], size: number = 10): RackSimple[][] {
        if (!racks || !Array.isArray(racks)) return [];
        const chunks: RackSimple[][] = [];
        for (let i = 0; i < racks.length; i += size) {
            chunks.push(racks.slice(i, i + size));
        }
        return chunks;
    }

    private findNodeById(nodes: LocationNode[], id: number): LocationNode | null {
        for (const node of nodes) {
            if (node.id === id) return node;
            if (node.children) {
                const found = this.findNodeById(node.children, id);
                if (found) return found;
            }
        }
        return null;
    }
}
