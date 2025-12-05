import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormGroup, FormBuilder, Validators } from '@angular/forms';
import { distinctUntilChanged } from 'rxjs/operators';
import { TitleService } from '../../shared/Services/title.service';
import { ActivatedRoute, Router } from '@angular/router';
import { isPlatformBrowser } from '@angular/common';
import { Inject, PLATFORM_ID } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-add-racks',
  templateUrl: './add-racks.component.html',
  styleUrls: ['./add-racks.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatIconModule]
})
export class AddRacksComponent implements OnInit {

  rackForm!: FormGroup;
  editData: any = null;

  constructor(
    private fb: FormBuilder,
    private titleService: TitleService,
    @Inject(PLATFORM_ID) private platformId: any,
    private route: ActivatedRoute,
    private router: Router
  ) { }

  // Static data 
  locations = [
    { id: 1, name: 'Hyderabad Campus' },
    { id: 2, name: 'Bangalore Campus' },
    { id: 3, name: 'Mumbai' },
    { id: 4, name: 'Delhi DC' },
  ];

  buildings = [
    { id: 10, locationId: 1, name: 'Alpha Building' },
    { id: 11, locationId: 2, name: 'Beta Building' },
    { id: 12, locationId: 3, name: 'Main Tower' },
    { id: 13, locationId: 4, name: 'West Block' },
  ];

  wings = [
    { id: 20, buildingId: 10, name: 'Wing A' },
    { id: 21, buildingId: 10, name: 'Wing B' },
    { id: 22, buildingId: 11, name: 'South Wing' },
    { id: 23, buildingId: 12, name: 'North Wing' },
    { id: 24, buildingId: 13, name: 'Wing C' },
  ];

  floors = [
    { id: 30, wingId: 20, name: 'Floor 1' },
    { id: 31, wingId: 20, name: 'Floor 2' },
    { id: 32, wingId: 21, name: 'Ground Floor' },
    { id: 33, wingId: 22, name: 'Level 3' },
    { id: 34, wingId: 23, name: 'Level 5' },
    { id: 35, wingId: 24, name: 'Floor 7' },
  ];

  datacentres = [
    { id: 40, floorId: 30, name: 'DC-1A' },
    { id: 41, floorId: 31, name: 'DC-1B' },
    { id: 42, floorId: 32, name: 'DC-2A' },
    { id: 43, floorId: 33, name: 'DC-3A' },
    { id: 44, floorId: 34, name: 'DC-4A' },
    { id: 45, floorId: 35, name: 'DC-4B' },
  ];

  filteredBuildings: any[] = [];
  filteredWings: any[] = [];
  filteredFloors: any[] = [];
  filteredDCs: any[] = [];

  rackNameExists = false;
  rackNameInvalid = false;

  devicesCount = 0;
  spaceInfo = '0 / 40U';

  submit: boolean = true;

  get win(): any {
    return typeof window !== 'undefined' ? window : null;
  }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      const state = this.win.history.state;
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }

    this.titleService.updateTitle(this.editData ? 'EDIT RACK' : 'ADD RACK');

    this.rackForm = this.fb.group({
      location: ['', Validators.required],
      building: ['', Validators.required],
      wing: ['', Validators.required],
      floor: ['', Validators.required],
      datacentre: ['', Validators.required],
      rackName: ['', [
        Validators.required,
        Validators.pattern(/^[A-Za-z0-9_-]+$/)
      ]],
      status: ['', Validators.required],
      height: [{ value: '40U', disabled: true }],
      devices: [{ value: this.devicesCount, disabled: true }],
      space: [{ value: this.spaceInfo, disabled: true }]
    });

    this.handleDependentDropdowns();

    if (this.editData) {
      this.rackForm.patchValue({
        location: this.editData?.location,
        building: this.editData?.building,
        wing: this.editData?.wing, 
        floor: this.editData?.floor,
        datacentre: this.editData?.dataCentre,
        rackName: this.editData?.name,
        
      });
    }




  }


  handleDependentDropdowns() {
    this.rackForm.get('location')?.valueChanges
      .pipe(distinctUntilChanged())
      .subscribe(locId => {
        const id = Number(locId);
        this.filteredBuildings = this.buildings.filter(b => b.locationId === id);
        this.filteredWings = [];
        this.filteredFloors = [];
        this.filteredDCs = [];
        this.resetLowerFields('building');
      });

    this.rackForm.get('building')?.valueChanges
      .pipe(distinctUntilChanged())
      .subscribe(bId => {
        const id = Number(bId);
        this.filteredWings = this.wings.filter(w => w.buildingId === id);
        this.filteredFloors = [];
        this.filteredDCs = [];
        this.resetLowerFields('wing');
      });

    this.rackForm.get('wing')?.valueChanges
      .pipe(distinctUntilChanged())
      .subscribe(wId => {
        const id = Number(wId);
        this.filteredFloors = this.floors.filter(f => f.wingId === id);
        this.filteredDCs = [];
        this.resetLowerFields('floor');
      });

    this.rackForm.get('floor')?.valueChanges
      .pipe(distinctUntilChanged())
      .subscribe(fId => {
        const id = Number(fId);
        this.filteredDCs = this.datacentres.filter(dc => dc.floorId === id);
      });
  }

  resetLowerFields(except?: string) {
    const obj: any = {};
    if (except !== 'building') obj.building = '';
    if (except !== 'wing') obj.wing = '';
    if (except !== 'floor') obj.floor = '';
    if (except !== 'datacentre') obj.datacentre = '';

    this.rackForm.patchValue(obj, { emitEvent: false });
  }

  saveRack() {
    this.submit = true;

    if (this.rackForm.invalid) {
      this.submit = false;
      if (this.editData) {

      } else {

      }
    }
  }
}
