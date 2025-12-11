import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormGroup, FormBuilder, Validators, FormControl } from '@angular/forms';
import { TitleService } from '../../shared/Services/title.service';
import { isPlatformBrowser } from '@angular/common';
import { Inject, PLATFORM_ID } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatInputModule } from '@angular/material/input';
import { Router } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';
import { distinctUntilChanged } from 'rxjs/operators';

@Component({
  selector: 'app-add-racks',
  templateUrl: './add-racks.component.html',
  styleUrls: ['./add-racks.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatIconModule, MatAutocompleteModule, MatInputModule]
})
export class AddRacksComponent implements OnInit {

  rackForm!: FormGroup;
  editData: any = null;
  buildings: any[] = [];
  filteredBuildings: any[] = [];
  floors: any[] = [];
  wings: any[] = [];
  filteredFloors: any[] = [];
  filteredWings: any[] = [];
  datacenters: any[] = [];
  filteredDatacenters: any = [];
  private subscriptions = new Subscription();
  dashboardLoc: any;
  submit: boolean = false

  constructor(
    private fb: FormBuilder,
    private titleService: TitleService,
    @Inject(PLATFORM_ID) private platformId: any,
    private listService: ListService,
    private router: Router
  ) { }

  get win(): any {
    return typeof window !== 'undefined' ? window : null;
  }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      const state = this.win.history.state;
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }

    this.titleService.updateTitle(this.editData ? 'EDIT RACK' : 'ADD RACK');
    this.dashboardLoc = localStorage.getItem('dashboard_location_name');
    this.rackForm = this.fb.group({
      location: [this.editData?.location_name ? this.editData?.location_name : this.dashboardLoc, Validators.required],
      building: [this.editData?.building_name ? this.editData?.building_name : '', Validators.required],
      wing: [this?.editData?.wing_name ? this.editData?.wing_name : '', Validators.required],
      floor: [this?.editData?.floor_name ? this?.editData?.floor_name : '', Validators.required],
      datacenter: [this?.editData?.datacenter_name ? this?.editData?.datacenter_name : '', Validators.required],
      rackName: [this?.editData?.name ? this?.editData?.name : '', [Validators.required, Validators.maxLength(50), Validators.pattern(/^[A-Za-z0-9_-]+$/)]],
      status: [this?.editData?.status ? this?.editData?.status : 'active', Validators.required],
      height: [{ value: this?.editData?.height ? this?.editData?.height : '42', disabled: true }],
      width: [{ value: this?.editData?.width ? this?.editData?.width : '24', disabled: true }],
      description: [this?.editData?.description ? this?.editData?.description : '', Validators.maxLength(200)]
    });

    this.getBuildings();

    if (this.editData) {
      this.buildingInputControl.setValue(this.editData?.building_name);
      this.wingInputControl.setValue(this.editData?.wing_name);
      this.floorInputControl.setValue(this.editData?.floor_name);
      this.dcInputControl.setValue(this.editData?.datacenter_name);
      this.getData("buildings")
      this.getData("wings");
      this.getData("floors");
      this.getData("DC");

    }
  }

  get f() {
    return this.rackForm.controls;
  }

  getBuildings(): void {
    this.buildings = [];
    this.filteredBuildings = [];
    this.wings = [];
    this.filteredWings = [];
    this.floors = [];
    this.filteredFloors = [];
    this.datacenters = [];
    this.filteredDatacenters = [];
    this.getData("buildings");
  }

  wingInputControl = new FormControl('');
  floorInputControl = new FormControl('');
  dcInputControl = new FormControl('');
  getWings(event: any) {
    if (this.rackForm.value.building != event.option.value) {
      this.rackForm.get('building')?.setValue(event.option.value);
      this.rackForm.patchValue({
        floor: '',
        datacenter: ''
      });
      this.wingInputControl.setValue('')
      this.floorInputControl.setValue('')
      this.dcInputControl.setValue('')
      this.wings = [];
      this.filteredWings = [];
      this.floors = [];
      this.filteredFloors = [];
      this.datacenters = [];
      this.filteredDatacenters = [];
      this.getData("wings");
    }
  }

  getFloors(event: any) {
    if (this.rackForm.value.wing != event.option.value) {
      this.rackForm.get('wing')?.setValue(event.option.value);
      this.rackForm.patchValue({
        floor: '',
        datacenter: ''
      });
      this.floorInputControl.setValue('')
      this.dcInputControl.setValue('')
      this.floors = [];
      this.filteredFloors = [];
      this.datacenters = [];
      this.filteredDatacenters = [];
      this.getData("floors")
      this.getData("floors");
    }

  }

  getDataCenters(event: any) {
    if (this.rackForm.value.floor != event.option.value) {
      this.rackForm.get('floor')?.setValue(event.option.value)
      this.rackForm.patchValue({
        datacenter: ''
      });
      this.dcInputControl.setValue('')
      this.datacenters = [];
      this.filteredDatacenters = [];
      this.getData("DC");
    }

    this.getData("DC")
  }

  getData(val: any) {
    if (val == "buildings") {
      this.subscriptions.add(
        this.listService.listItems({ entity: 'buildings', location_name: this.rackForm.value.location })
          .subscribe({
            next: (res: any) => {
              this.buildings = res?.results;
              this.filteredBuildings = this.buildings
            },
            error: (err: any) => {
              console.error("API error fetching buildings:", err);
            }
          })
      );
    }
    if (val == "wings") {
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'wings', location_name: this.rackForm.value.location,
          building_name: this.rackForm.value.building
        })
          .subscribe({
            next: (res: any) => {
              this.wings = res?.results;
              this.filteredWings = this.wings
            },
            error: (err: any) => {
              console.error("API error fetching wings:", err);
            }
          })
      );
    }
    if (val == "floors") {
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'floors', location_name: this.rackForm.value.location,
          building_name: this.rackForm.value.building, wing_name: this.rackForm.value.wing
        })
          .subscribe({
            next: (res: any) => {
              this.floors = res?.results;
              this.filteredFloors = this.floors
            },
            error: (err: any) => {
              console.error("API error fetching floors:", err);
            }
          })
      );
    }
    if (val == "DC") {
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'datacenters', location_name: this.rackForm.value.location,
          building_name: this.rackForm.value.building, wing_name: this.rackForm.value.wing,
          floor_name: this.rackForm.value.floor
        })
          .subscribe({
            next: (res: any) => {
              this.datacenters = res?.results;
              this.filteredDatacenters = this.datacenters
            },
            error: (err: any) => {
              console.error("API error fetching data centers:", err);
            }
          })
      );
    }
  }

  onSearch(event: any, key: any) {
    if (event.target.value) {
      const search = event.target.value.toLowerCase();
      if (key == 'building') {
        this.filteredBuildings = this.buildings.filter(b =>
          b.name.toLowerCase().includes(search)
        );
      }
      if (key == 'wing') {
        this.filteredWings = this.wings.filter(b =>
          b.name.toLowerCase().includes(search)
        );
      }
      if (key == 'floor') {
        this.filteredFloors = this.floors.filter(b =>
          b.name.toLowerCase().includes(search)
        );
      }
      if (key == 'datacenter') {
        this.filteredDatacenters = this.datacenters.filter(b =>
          b.name.toLowerCase().includes(search)
        );
      }
    }
  }

  buildingInputControl = new FormControl('');

  resetAllFields() {
    this.buildingInputControl.reset('');
    this.wingInputControl.reset('');
    this.floorInputControl.reset('');
    this.dcInputControl.reset('');

    this.filteredBuildings = [];
    this.filteredWings = [];
    this.filteredFloors = [];
    this.filteredDatacenters = [];

    this.rackForm.get('rackName')?.setValue('');
    this.rackForm.get('description')?.setValue('');
    this.rackForm.get('building')?.setValue('');
    this.rackForm.get('wing')?.setValue('');
    this.rackForm.get('floor')?.setValue('');
    this.rackForm.get('datacenter')?.setValue('');

    this.getBuildings();
  }

  saveRack(val: any) {
    this.submit = true;
    if (this.rackForm.valid) {
      const rackData: RackPayload = {
        name: this.rackForm.value.rackName,
        location_name: this.rackForm.value.location,
        building_name: this.rackForm.value.building,
        wing_name: this.rackForm.value.wing,
        floor_name: this.rackForm.value.floor,
        datacenter_name: this.rackForm.value.datacenter,
        status: this.rackForm.value.status.toLowerCase(),
        width: Math.floor(Number(this.rackForm.getRawValue().width)),
        height: Math.floor(Number(this.rackForm.getRawValue().height)),
        description: this.rackForm.value.description
      };
      if (this.editData) {
        this.listService.updateRack(this.editData?.name, rackData).subscribe({
          next: () => {
            this.submit = false;
            this.router.navigate([Menu.Rack_Management + '/' + SubMenu.Racks]);
          },
          error: (err: any) => {
            this.submit = false;
          }
        });
      } else {
        this.listService.addRack(rackData).subscribe({
          next: () => {
            this.submit = false;
            if (val == 'save') {
              alert("Rack saved successfully!");
              this.router.navigate([Menu.Rack_Management + '/' + SubMenu.Racks]);
            } else if (val == 'addAnother') {
              alert("Rack saved successfully!");
              this.resetAllFields();
            }
          },

          error: (err: any) => {
            this.submit = false;
          }
        });
      }

    }

  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}

export interface RackPayload {
  name: string;
  location_name: string;
  building_name: string;
  wing_name: string;
  floor_name: string;
  datacenter_name: string;
  status: string;
  width: number;
  height: number;
  description: string;
}