import { Component, Inject, OnDestroy, OnInit, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators, FormControl } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { TitleService } from '../../shared/Services/title.service';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatInputModule } from '@angular/material/input';
import { Subscription, distinctUntilChanged } from 'rxjs';
import { ListService } from '../../services/list.service';

@Component({
  selector: 'app-add-device',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatIconModule, MatAutocompleteModule, MatInputModule],
  templateUrl: './add-device.component.html',
  styleUrls: ['./add-device.component.scss']
})
export class AddDeviceComponent implements OnInit, OnDestroy {

  deviceForm!: FormGroup;
  editData: any = null;
  submitAttempted = false;
  private subscriptions = new Subscription();

  statuses = ['active', 'inactive'];
  assetUsers: string[] = ['in_use', 'not_in_use'];
  faceOptions = ['front', 'back'];

  locations: any[] = [];
  buildings: any[] = [];
  wings: any[] = [];
  floors: any[] = [];
  datacentres: any[] = [];
  racks: any[] = [];
  filteredBuildings: any[] = [];
  filteredWings: any[] = [];
  filteredFloors: any[] = [];
  filteredDatacentres: any[] = [];
  filteredRacks: any[] = [];
  makes: string[] = [];
  deviceTypes: string[] = [];
  models: string[] = [];
  assetOwners: string[] = [];
  applicationNames: string[] = [];
  filteredMakes: string[] = [];
  filteredDeviceTypes: string[] = [];
  filteredModels: string[] = [];
  filteredAssetOwners: string[] = [];
  filteredApplicationNames: string[] = [];
  filteredStatuses: string[] = [];
  filteredFaces: string[] = [];
  filteredAssetUsers: string[] = [];
  initialFormValue: any = null;
  defaultLocation: string | null = null;
  buildingInputControl = new FormControl('');
  wingInputControl = new FormControl('');
  floorInputControl = new FormControl('');
  dcInputControl = new FormControl('');
  rackInputControl = new FormControl('');
  makeInputControl = new FormControl('');
  deviceTypeInputControl = new FormControl('');
  modelInputControl = new FormControl('');
  assetOwnerInputControl = new FormControl('');
  applicationInputControl = new FormControl('');
  statusInputControl = new FormControl('');
  faceInputControl = new FormControl('');
  assetUserInputControl = new FormControl('');

  get win(): any {
    return typeof window !== 'undefined' ? window : null;
  }

  get f() {
    return this.deviceForm.controls;
  }

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private titleService: TitleService,
    private listService: ListService,
    @Inject(PLATFORM_ID) private platformId: any
  ) {}

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      const state = this.win.history.state;
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }
    const routeDeviceId = this.route.snapshot.paramMap.get('deviceID');
    if (!this.editData && routeDeviceId) {
      this.listService.getDeviceDetails(routeDeviceId).subscribe({
        next: (res) => {
          const r: any = res || {};
          this.editData = r ? { ...r, name: r?.name || routeDeviceId } : { name: routeDeviceId };
          this.applyEditDataToForm();
          this.prefetchDependentData();
        },
        error: () => {
          // proceed with blank form if details not found
        }
      });
    }

    this.titleService.updateTitle(this.editData ? 'EDIT DEVICE' : 'ADD DEVICE');
    this.defaultLocation = localStorage.getItem('dashboard_location_name');

    const initialFace = this.editData?.face || this.editData?.device_face || '';
    const initialAssetUser = this.normalizeAssetUser(this.editData?.asset_user || this.editData?.assetUser || '');

    this.deviceForm = this.fb.group({
      deviceName: [this.editData?.name || this.editData?.Device_name || '', Validators.required],
      ipAddress: [this.editData?.ip || this.editData?.ip_address || '', Validators.required],
      status: [this.editData?.status || this.editData?.device_status || 'active', Validators.required],
      location: [this.editData?.location_name || this.editData?.location || this.defaultLocation || '', Validators.required],
      building: [this.editData?.building_name || this.editData?.building || '', Validators.required],
      wing: [this.editData?.wing_name || this.editData?.wing || '', Validators.required],
      floor: [this.editData?.floor_name || this.editData?.floor || '', Validators.required],
      datacentre: [this.editData?.datacenter_name || this.editData?.datacentre || this.editData?.data_center || '', Validators.required],
      rackNo: [this.editData?.rack_name || this.editData?.rackNo || '', Validators.required],
      make: [this.editData?.make_name || this.editData?.make || '', Validators.required],
      deviceType: [this.editData?.devicetype_name || this.editData?.deviceType || this.editData?.device_type || '', Validators.required],
      modelName: [this.editData?.model_name || this.editData?.modelName || '', Validators.required],
      rackSlot: [this.editData?.position || this.editData?.rackSlot || 1, Validators.required],
      face: [initialFace, Validators.required],
      assetOwner: [this.editData?.asset_owner_name || this.editData?.assetOwner || this.editData?.asset_owner || '', Validators.required],
      assetUser: [initialAssetUser, Validators.required],
      serialNumber: [this.editData?.serial_no || this.editData?.serial_number || this.editData?.serialNumber || '', Validators.required],
      poNumber: [this.editData?.po_number || this.editData?.PO_number || '', Validators.required],
      applicationName: [this.editData?.application_name || this.editData?.applications_mapped_name || '', Validators.required],
      warrantyStartDate: [this.editData?.warranty_start_date || '', Validators.required],
      warrantyEndDate: [this.editData?.warranty_end_date || '', Validators.required],
      amcStartDate: [this.editData?.amc_start_date || this.editData?.AMC_start_date || '', Validators.required],
      amcEndDate: [this.editData?.amc_end_date || this.editData?.AMC_end_date || '', Validators.required],
      description: [this.editData?.description || '', Validators.required]
    });

    this.filteredStatuses = this.statuses;
    this.filteredFaces = this.faceOptions;
    this.filteredAssetUsers = this.assetUsers;

    this.loadMakes();
    this.loadApplications();
    this.loadAssetOwners();
    this.loadBuildings();

    if (this.editData) {
      this.applyEditDataToForm();
      this.prefetchDependentData();
      this.initialFormValue = this.deviceForm.getRawValue();
    } else {
      this.initialFormValue = this.createBlankFormValues();
    }

    this.setupDropdownDependencies();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  saveDevice() {
    this.submitForm(false);
  }

  saveAndAddAnother() {
    this.submitForm(true);
  }

  private submitForm(addAnother: boolean) {
    this.submitAttempted = true;
    if (this.deviceForm.invalid) {
      return;
    }

    const payload = this.deviceForm.getRawValue();
    const apiPayload = {
      name: payload.deviceName,
      ip: payload.ipAddress,
      status: payload.status,
      location_name: payload.location,
      building_name: payload.building,
      wing_name: payload.wing,
      floor_name: payload.floor,
      datacenter_name: payload.datacentre,
      rack_name: payload.rackNo,
      make_name: payload.make,
      devicetype_name: payload.deviceType,
      model_name: payload.modelName,
      position: payload.rackSlot || 1,
      face: payload.face,
      asset_user: payload.assetUser,
      asset_owner_name: payload.assetOwner,
      serial_no: payload.serialNumber,
      po_number: payload.poNumber,
      application_name: payload.applicationName,
      warranty_start_date: payload.warrantyStartDate || null,
      warranty_end_date: payload.warrantyEndDate || null,
      amc_start_date: payload.amcStartDate || null,
      amc_end_date: payload.amcEndDate || null,
      description: payload.description || ''
    };

    const isEdit = !!this.editData;
    const deviceName = this.editData?.name || this.editData?.Device_name || payload.deviceName;

    const request$ = isEdit
      ? this.listService.updateDevice(deviceName, apiPayload)
      : this.listService.createDevice(apiPayload);

    request$.subscribe({
      next: () => {
        this.submitAttempted = false;
        if (addAnother && !isEdit) {
          this.deviceForm.reset({
            rackSlot: 1,
            face: 'front'
          });
          this.buildingInputControl.reset('');
          this.wingInputControl.reset('');
          this.floorInputControl.reset('');
          this.dcInputControl.reset('');
          this.rackInputControl.reset('');
          this.makeInputControl.reset('');
          this.deviceTypeInputControl.reset('');
          this.modelInputControl.reset('');
          this.assetOwnerInputControl.reset('');
          this.applicationInputControl.reset('');
          this.statusInputControl.reset('');
          this.faceInputControl.reset('');
          this.assetUserInputControl.reset('');
          this.filteredBuildings = [];
          this.filteredWings = [];
          this.filteredFloors = [];
          this.filteredDatacentres = [];
          this.filteredRacks = [];
          this.filteredMakes = [];
          this.filteredDeviceTypes = [];
          this.filteredModels = [];
          this.filteredAssetOwners = [];
          this.filteredApplicationNames = [];
          this.filteredStatuses = [];
          this.filteredFaces = [];
          this.filteredAssetUsers = [];
          this.buildings = [];
          this.wings = [];
          this.floors = [];
          this.datacentres = [];
          this.racks = [];
          this.deviceTypes = [];
          this.models = [];
          this.filteredStatuses = this.statuses;
          this.filteredFaces = this.faceOptions;
          this.filteredAssetUsers = this.assetUsers;
          this.loadBuildings();
          this.loadMakes();
          this.loadApplications();
          this.loadAssetOwners();
        } else {
          this.router.navigate(['StockRoom/Devices']);
        }
      },
      error: (err) => {
        this.submitAttempted = false;
        console.error('Failed to save device', err);
      }
    });
  }

  private setupDropdownDependencies() {
    this.subscriptions.add(
      this.deviceForm.get('location')?.valueChanges
        .pipe(distinctUntilChanged((a, b) => this.sameValue(a, b)))
        .subscribe(() => {
          this.resetLowerFields(['building']);
          this.loadBuildings();
        }) || new Subscription()
    );

    this.subscriptions.add(
      this.deviceForm.get('building')?.valueChanges
        .pipe(distinctUntilChanged((a, b) => this.sameValue(a, b)))
        .subscribe(() => {
          this.resetLowerFields(['wing']);
          this.wings = [];
          this.filteredWings = [];
          this.floors = [];
          this.filteredFloors = [];
          this.datacentres = [];
          this.filteredDatacentres = [];
          this.racks = [];
          this.filteredRacks = [];
          this.wingInputControl.setValue('');
          this.floorInputControl.setValue('');
          this.dcInputControl.setValue('');
          this.rackInputControl.setValue('');
          if (this.deviceForm.value.building) {
            this.getData('wings');
          }
        }) || new Subscription()
    );

    this.subscriptions.add(
      this.deviceForm.get('wing')?.valueChanges
        .pipe(distinctUntilChanged((a, b) => this.sameValue(a, b)))
        .subscribe(() => {
          this.resetLowerFields(['floor']);
          this.floors = [];
          this.filteredFloors = [];
          this.datacentres = [];
          this.filteredDatacentres = [];
          this.racks = [];
          this.filteredRacks = [];
          this.floorInputControl.setValue('');
          this.dcInputControl.setValue('');
          this.rackInputControl.setValue('');
          if (this.deviceForm.value.wing) {
            this.getData('floors');
          }
        }) || new Subscription()
    );

    this.subscriptions.add(
      this.deviceForm.get('floor')?.valueChanges
        .pipe(distinctUntilChanged((a, b) => this.sameValue(a, b)))
        .subscribe(() => {
          this.resetLowerFields(['datacentre']);
          this.datacentres = [];
          this.filteredDatacentres = [];
          this.racks = [];
          this.filteredRacks = [];
          this.dcInputControl.setValue('');
          this.rackInputControl.setValue('');
          if (this.deviceForm.value.floor) {
            this.getData('datacenters');
          }
        }) || new Subscription()
    );

    this.subscriptions.add(
      this.deviceForm.get('datacentre')?.valueChanges
        .pipe(distinctUntilChanged((a, b) => this.sameValue(a, b)))
        .subscribe(() => {
          this.resetLowerFields(['rackNo']);
          this.racks = [];
          this.filteredRacks = [];
          this.rackInputControl.setValue('');
          if (this.deviceForm.value.datacentre) {
            this.getData('racks');
          }
        }) || new Subscription()
    );

    this.subscriptions.add(
      this.deviceForm.get('make')?.valueChanges
        .pipe(distinctUntilChanged((a, b) => this.sameValue(a, b)))
        .subscribe((make: string) => {
          this.resetLowerFields(['deviceType', 'modelName']);
          this.deviceTypes = [];
          this.filteredDeviceTypes = [];
          this.models = [];
          this.filteredModels = [];
          this.deviceTypeInputControl.setValue('');
          this.modelInputControl.setValue('');
          if (make) {
            this.loadDeviceTypes(make);
          }
        }) || new Subscription()
    );

    this.subscriptions.add(
      this.deviceForm.get('deviceType')?.valueChanges
        .pipe(distinctUntilChanged((a, b) => this.sameValue(a, b)))
        .subscribe((deviceType: string) => {
          this.resetLowerFields(['modelName']);
          this.models = [];
          this.filteredModels = [];
          this.modelInputControl.setValue('');
          const make = this.deviceForm.value.make;
          if (make && deviceType) {
            this.loadModels(make, deviceType);
          }
        }) || new Subscription()
    );

    this.subscriptions.add(
      this.deviceForm.get('modelName')?.valueChanges
        .pipe(distinctUntilChanged())
        .subscribe((model: string) => {
          // height removed; no action on model change
        }) || new Subscription()
    );

    // asset owner is static for now; no API-driven effects
  }


  private loadBuildings() {
    this.buildings = [];
    this.filteredBuildings = [];
    this.wings = [];
    this.filteredWings = [];
    this.floors = [];
    this.filteredFloors = [];
    this.datacentres = [];
    this.filteredDatacentres = [];
    this.racks = [];
    this.filteredRacks = [];
    if (this.deviceForm.value.location) {
      this.subscriptions.add(
        this.listService.listItems({ entity: 'buildings', location_name: this.deviceForm.value.location })
          .subscribe({
            next: (res: any) => {
              this.buildings = res?.results || [];
              this.filteredBuildings = this.buildings;
            },
            error: (err: any) => {
              console.error("API error fetching buildings:", err);
            }
          })
      );
    }
  }

  onSearch(event: any, key: string) {
    if (event.target.value) {
      const search = event.target.value.toLowerCase();
      if (key === 'building') {
        this.filteredBuildings = this.buildings.filter((b: any) =>
          b.name.toLowerCase().includes(search)
        );
      }
      if (key === 'wing') {
        this.filteredWings = this.wings.filter((w: any) =>
          w.name.toLowerCase().includes(search)
        );
      }
      if (key === 'floor') {
        this.filteredFloors = this.floors.filter((f: any) =>
          f.name.toLowerCase().includes(search)
        );
      }
      if (key === 'datacenter') {
        this.filteredDatacentres = this.datacentres.filter((d: any) =>
          d.name.toLowerCase().includes(search)
        );
      }
      if (key === 'rack') {
        this.filteredRacks = this.racks.filter((r: any) =>
          r.name.toLowerCase().includes(search)
        );
      }
      if (key === 'make') {
        this.filteredMakes = this.makes.filter((m: string) =>
          m.toLowerCase().includes(search)
        );
      }
      if (key === 'deviceType') {
        this.filteredDeviceTypes = this.deviceTypes.filter((d: string) =>
          d.toLowerCase().includes(search)
        );
      }
      if (key === 'model') {
        this.filteredModels = this.models.filter((m: string) =>
          m.toLowerCase().includes(search)
        );
      }
      if (key === 'assetOwner') {
        this.filteredAssetOwners = this.assetOwners.filter((a: string) =>
          a.toLowerCase().includes(search)
        );
      }
      if (key === 'application') {
        this.filteredApplicationNames = this.applicationNames.filter((a: string) =>
          a.toLowerCase().includes(search)
        );
      }
      if (key === 'status') {
        this.filteredStatuses = this.statuses.filter((s: string) =>
          s.toLowerCase().includes(search)
        );
      }
      if (key === 'face') {
        this.filteredFaces = this.faceOptions.filter((f: string) =>
          f.toLowerCase().includes(search)
        );
      }
      if (key === 'assetUser') {
        this.filteredAssetUsers = this.assetUsers.filter((a: string) =>
          a.toLowerCase().includes(search)
        );
      }
    } else {
      if (key === 'building') this.filteredBuildings = this.buildings;
      if (key === 'wing') this.filteredWings = this.wings;
      if (key === 'floor') this.filteredFloors = this.floors;
      if (key === 'datacenter') this.filteredDatacentres = this.datacentres;
      if (key === 'rack') this.filteredRacks = this.racks;
      if (key === 'make') this.filteredMakes = this.makes;
      if (key === 'deviceType') this.filteredDeviceTypes = this.deviceTypes;
      if (key === 'model') this.filteredModels = this.models;
      if (key === 'assetOwner') this.filteredAssetOwners = this.assetOwners;
      if (key === 'application') this.filteredApplicationNames = this.applicationNames;
      if (key === 'status') this.filteredStatuses = this.statuses;
      if (key === 'face') this.filteredFaces = this.faceOptions;
      if (key === 'assetUser') this.filteredAssetUsers = this.assetUsers;
    }
  }

  getWings(event: any) {
    if ((event?.option?.value || '').toString().trim().toLowerCase() === (this.deviceForm.value.building || '').toString().trim().toLowerCase()) {
      return;
    }
    this.deviceForm.get('building')?.setValue(event.option.value);
    this.deviceForm.patchValue({
      wing: '',
      floor: '',
      datacentre: '',
      rackNo: ''
    });
    this.wingInputControl.setValue('');
    this.floorInputControl.setValue('');
    this.dcInputControl.setValue('');
    this.rackInputControl.setValue('');
    this.wings = [];
    this.filteredWings = [];
    this.floors = [];
    this.filteredFloors = [];
    this.datacentres = [];
    this.filteredDatacentres = [];
    this.racks = [];
    this.filteredRacks = [];
    this.getData('wings');
  }

  getFloors(event: any) {
    if ((event?.option?.value || '').toString().trim().toLowerCase() === (this.deviceForm.value.wing || '').toString().trim().toLowerCase()) {
      return;
    }
    this.deviceForm.get('wing')?.setValue(event.option.value);
    this.deviceForm.patchValue({
      floor: '',
      datacentre: '',
      rackNo: ''
    });
    this.floorInputControl.setValue('');
    this.dcInputControl.setValue('');
    this.rackInputControl.setValue('');
    this.floors = [];
    this.filteredFloors = [];
    this.datacentres = [];
    this.filteredDatacentres = [];
    this.racks = [];
    this.filteredRacks = [];
    this.getData('floors');
  }

  getDataCenters(event: any) {
    if ((event?.option?.value || '').toString().trim().toLowerCase() === (this.deviceForm.value.floor || '').toString().trim().toLowerCase()) {
      return;
    }
    this.deviceForm.get('floor')?.setValue(event.option.value);
    this.deviceForm.patchValue({
      datacentre: '',
      rackNo: ''
    });
    this.dcInputControl.setValue('');
    this.rackInputControl.setValue('');
    this.datacentres = [];
    this.filteredDatacentres = [];
    this.racks = [];
    this.filteredRacks = [];
    this.getData('datacenters');
  }

  getRacks(event: any) {
    if ((event?.option?.value || '').toString().trim().toLowerCase() === (this.deviceForm.value.datacentre || '').toString().trim().toLowerCase()) {
      return;
    }
    this.deviceForm.get('datacentre')?.setValue(event.option.value);
    this.deviceForm.patchValue({
      rackNo: ''
    });
    this.rackInputControl.setValue('');
    this.racks = [];
    this.filteredRacks = [];
    this.getData('racks');
  }

  setRack(event: any) {
    this.deviceForm.get('rackNo')?.setValue(event.option.value);
  }

  getMake(event: any) {
    if ((event?.option?.value || '').toString().trim().toLowerCase() === (this.deviceForm.value.make || '').toString().trim().toLowerCase()) {
      return;
    }
    const selectedValue = event.option.value;
    this.deviceForm.get('make')?.setValue(selectedValue);
    this.makeInputControl.setValue(selectedValue);
    this.deviceForm.patchValue({
      deviceType: '',
      modelName: ''
    });
    this.deviceTypeInputControl.setValue('');
    this.modelInputControl.setValue('');
    this.deviceTypes = [];
    this.filteredDeviceTypes = [];
    this.models = [];
    this.filteredModels = [];
    if (selectedValue) {
      this.loadDeviceTypes(selectedValue);
    }
  }

  getDeviceType(event: any) {
    if ((event?.option?.value || '').toString().trim().toLowerCase() === (this.deviceForm.value.deviceType || '').toString().trim().toLowerCase()) {
      return;
    }
    const selectedValue = event.option.value;
    this.deviceForm.get('deviceType')?.setValue(selectedValue);
    this.deviceTypeInputControl.setValue(selectedValue);
    this.deviceForm.patchValue({
      modelName: ''
    });
    this.modelInputControl.setValue('');
    this.models = [];
    this.filteredModels = [];
    if (selectedValue && this.deviceForm.value.make) {
      this.loadModels(this.deviceForm.value.make, selectedValue);
    }
  }

  getModel(event: any) {
    const selectedValue = event.option.value;
    this.deviceForm.get('modelName')?.setValue(selectedValue);
    this.modelInputControl.setValue(selectedValue);
  }

  getAssetOwner(event: any) {
    const selectedValue = event.option.value;
    this.deviceForm.get('assetOwner')?.setValue(selectedValue);
    this.assetOwnerInputControl.setValue(selectedValue);
  }

  getApplication(event: any) {
    const selectedValue = event.option.value;
    this.deviceForm.get('applicationName')?.setValue(selectedValue);
    this.applicationInputControl.setValue(selectedValue);
  }

  /**
   * Keep the visible input text in sync with the form control when the field loses focus.
   * Prevents accidental clearing when clicking outside the autocomplete.
   */
  onFieldBlur(key: string) {
    const formControlMap: Record<string, string> = {
      building: 'building',
      wing: 'wing',
      floor: 'floor',
      datacentre: 'datacentre',
      rackNo: 'rackNo',
      make: 'make',
      deviceType: 'deviceType',
      modelName: 'modelName',
      assetOwner: 'assetOwner',
      applicationName: 'applicationName',
      status: 'status',
      face: 'face',
      assetUser: 'assetUser'
    };
    const inputControlMap: Record<string, FormControl> = {
      building: this.buildingInputControl,
      wing: this.wingInputControl,
      floor: this.floorInputControl,
      datacentre: this.dcInputControl,
      rackNo: this.rackInputControl,
      make: this.makeInputControl,
      deviceType: this.deviceTypeInputControl,
      modelName: this.modelInputControl,
      assetOwner: this.assetOwnerInputControl,
      applicationName: this.applicationInputControl,
      status: this.statusInputControl,
      face: this.faceInputControl,
      assetUser: this.assetUserInputControl
    };

    const formKey = formControlMap[key];
    const inputControl = inputControlMap[key];
    const formValue = this.deviceForm.get(formKey)?.value ?? '';
    if (inputControl) {
      inputControl.setValue(formValue, { emitEvent: false });
    }
  }

  resetForm() {
    if (this.editData) {
      // Restore to initial edit values
      this.deviceForm.reset(this.initialFormValue || {});
      this.syncInputsFromForm();
      this.filteredStatuses = this.statuses;
      this.filteredFaces = this.faceOptions;
      this.filteredAssetUsers = this.assetUsers;
      this.filteredMakes = this.makes;
      this.filteredDeviceTypes = this.deviceTypes;
      this.filteredModels = this.models;
      this.filteredAssetOwners = this.assetOwners;
      this.filteredApplicationNames = this.applicationNames;
      this.loadBuildings();
      this.prefetchDependentData();
    } else {
      // Clear everything in add mode
      this.deviceForm.reset(this.initialFormValue || this.createBlankFormValues());
      // Ensure location restores to default after reset in add mode
      this.deviceForm.patchValue({ location: this.defaultLocation || '' });
      this.clearOptionLists();
      this.syncInputsFromForm();
      this.loadMakes();
      this.loadApplications();
      this.loadAssetOwners();
      this.loadBuildings();
    }
  }

  private createBlankFormValues() {
    return {
      deviceName: '',
      ipAddress: '',
      status: '',
      location: this.defaultLocation || '',
      building: '',
      wing: '',
      floor: '',
      datacentre: '',
      rackNo: '',
      make: '',
      deviceType: '',
      modelName: '',
      rackSlot: null,
      face: '',
      assetOwner: '',
      assetUser: '',
      serialNumber: '',
      poNumber: '',
      applicationName: '',
      warrantyStartDate: '',
      warrantyEndDate: '',
      amcStartDate: '',
      amcEndDate: '',
      description: ''
    };
  }

  private clearOptionLists() {
    this.buildings = [];
    this.wings = [];
    this.floors = [];
    this.datacentres = [];
    this.racks = [];
    this.deviceTypes = [];
    this.models = [];
    this.filteredBuildings = [];
    this.filteredWings = [];
    this.filteredFloors = [];
    this.filteredDatacentres = [];
    this.filteredRacks = [];
    this.filteredMakes = [];
    this.filteredDeviceTypes = [];
    this.filteredModels = [];
    this.filteredAssetOwners = [];
    this.filteredApplicationNames = [];
    this.filteredStatuses = this.statuses;
    this.filteredFaces = this.faceOptions;
    this.filteredAssetUsers = this.assetUsers;
  }

  private syncInputsFromForm() {
    const val = this.deviceForm.getRawValue();
    this.buildingInputControl.setValue(val.building || '', { emitEvent: false });
    this.wingInputControl.setValue(val.wing || '', { emitEvent: false });
    this.floorInputControl.setValue(val.floor || '', { emitEvent: false });
    this.dcInputControl.setValue(val.datacentre || '', { emitEvent: false });
    this.rackInputControl.setValue(val.rackNo || '', { emitEvent: false });
    this.makeInputControl.setValue(val.make || '', { emitEvent: false });
    this.deviceTypeInputControl.setValue(val.deviceType || '', { emitEvent: false });
    this.modelInputControl.setValue(val.modelName || '', { emitEvent: false });
    this.assetOwnerInputControl.setValue(val.assetOwner || '', { emitEvent: false });
    this.applicationInputControl.setValue(val.applicationName || '', { emitEvent: false });
    this.statusInputControl.setValue(val.status || '', { emitEvent: false });
    this.faceInputControl.setValue(val.face || '', { emitEvent: false });
    this.assetUserInputControl.setValue(val.assetUser || '', { emitEvent: false });
  }

  getStatus(event: any) {
    const selectedValue = event.option.value;
    this.deviceForm.get('status')?.setValue(selectedValue);
    this.statusInputControl.setValue(selectedValue);
  }

  getFace(event: any) {
    const selectedValue = event.option.value;
    this.deviceForm.get('face')?.setValue(selectedValue);
    this.faceInputControl.setValue(selectedValue);
  }

  getAssetUserSelection(event: any) {
    const selectedValue = event.option.value;
    this.deviceForm.get('assetUser')?.setValue(selectedValue);
    this.assetUserInputControl.setValue(selectedValue);
  }

  getData(val: string) {
    if (val === 'wings') {
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'wings',
          location_name: this.deviceForm.value.location,
          building_name: this.deviceForm.value.building
        })
          .subscribe({
            next: (res: any) => {
              this.wings = res?.results || [];
              this.filteredWings = this.wings;
            },
            error: (err: any) => {
              console.error("API error fetching wings:", err);
            }
          })
      );
    }
    if (val === 'floors') {
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'floors',
          location_name: this.deviceForm.value.location,
          building_name: this.deviceForm.value.building,
          wing_name: this.deviceForm.value.wing
        })
          .subscribe({
            next: (res: any) => {
              this.floors = res?.results || [];
              this.filteredFloors = this.floors;
            },
            error: (err: any) => {
              console.error("API error fetching floors:", err);
            }
          })
      );
    }
    if (val === 'datacenters') {
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'datacenters',
          location_name: this.deviceForm.value.location,
          building_name: this.deviceForm.value.building,
          wing_name: this.deviceForm.value.wing,
          floor_name: this.deviceForm.value.floor
        })
          .subscribe({
            next: (res: any) => {
              this.datacentres = res?.results || [];
              this.filteredDatacentres = this.datacentres;
            },
            error: (err: any) => {
              console.error("API error fetching datacenters:", err);
            }
          })
      );
    }
    if (val === 'racks') {
      this.subscriptions.add(
        this.listService.listItems({
          entity: 'racks',
          location_name: this.deviceForm.value.location,
          building_name: this.deviceForm.value.building,
          wing_name: this.deviceForm.value.wing,
          floor_name: this.deviceForm.value.floor,
          datacenter_name: this.deviceForm.value.datacentre
        })
          .subscribe({
            next: (res: any) => {
              this.racks = res?.results || [];
              this.filteredRacks = this.racks;
            },
            error: (err: any) => {
              console.error("API error fetching racks:", err);
            }
          })
      );
    }
  }

  private loadMakes() {
    this.listService.listItems({ entity: 'makes', offset: 0, page_size: 100 })
      .subscribe((res: any) => {
        this.makes = this.mapNames(res?.results, ['name', 'make', 'make_name', 'manufacturer']);
        this.filteredMakes = this.makes;
      });
  }

  private loadApplications() {
    this.listService.listItems({ entity: 'applications', offset: 0, page_size: 100 })
      .subscribe((res: any) => {
        this.applicationNames = this.mapNames(res?.results, ['name', 'application_name', 'applications_mapped_name']);
        this.filteredApplicationNames = this.applicationNames;
      });
  }

  private loadDeviceTypes(makeName?: string) {
    const filters: any = { entity: 'device_types', offset: 0, page_size: 100 };
    if (makeName) filters.make_name = makeName;
    this.listService.listItems(filters)
      .subscribe((res: any) => {
        this.deviceTypes = this.mapNames(res?.results, ['name', 'device_type', 'devicetype_name']);
        this.filteredDeviceTypes = this.deviceTypes;
      });
  }

  private loadModels(makeName?: string, deviceTypeName?: string) {
    const filters: any = { entity: 'models', offset: 0, page_size: 100 };
    if (makeName) filters.make_name = makeName;
    if (deviceTypeName) filters.devicetype_name = deviceTypeName;
    this.listService.listItems(filters)
      .subscribe((res: any) => {
        this.models = this.mapNames(res?.results, ['name', 'model_name']);
        this.filteredModels = this.models;
      });
  }

  private loadAssetOwners() {
    this.listService.listItems({ entity: 'asset_owner', offset: 0, page_size: 10 })
      .subscribe((res: any) => {
        this.assetOwners = this.mapNames(res?.results, ['name', 'asset_owner_name', 'asset_owner']);
        const current = this.deviceForm?.value?.assetOwner;
        if (current && !this.assetOwners.includes(current)) {
          this.assetOwners.unshift(current);
        }
        this.filteredAssetOwners = this.assetOwners;
      });
  }

  private mapNames(items: any[], keys: string[]): string[] {
    if (!Array.isArray(items)) return [];
    return items
      .map(item => {
        const key = keys.find(k => item?.[k]);
        return key ? item[key] : (item?.name || item);
      })
      .filter((val: any) => !!val);
  }

  private normalizeAssetUser(value: string | undefined): string {
    if (!value) return '';
    const v = value.toLowerCase();
    if (v === 'in use') return 'in_use';
    if (v === 'not in use') return 'not_in_use';
    if (v === 'in_use' || v === 'not_in_use') return v;
    return value;
  }

  private ensureOption(list: any[], value: any) {
    if (value === null || value === undefined || value === '') return;
    if (!list.some((v: any) => v === value)) {
      list.push(value);
    }
  }

  private resetLowerFields(names: string[]) {
    const patch: any = {};
    names.forEach(n => patch[n] = '');
    this.deviceForm.patchValue(patch, { emitEvent: false });
  }

  private sameValue(a: any, b: any): boolean {
    return (a ?? '').toString().trim().toLowerCase() === (b ?? '').toString().trim().toLowerCase();
  }

  private applyEditDataToForm() {
    if (!this.editData) return;
    this.deviceForm.patchValue({
      deviceName: this.editData.name || this.editData.Device_name,
      ipAddress: this.editData.ip || this.editData.ip_address,
      status: this.editData.status || this.editData.device_status || 'active',
      location: this.editData.location || this.editData.location_name,
      building: this.editData.building || this.editData.building_name,
      wing: this.editData.wing || this.editData.wing_name,
      floor: this.editData.floor || this.editData.floor_name,
      datacentre: this.editData.datacentre || this.editData.datacenter_name || this.editData.data_center,
      rackNo: this.editData.rack || this.editData.rack_name,
      make: this.editData.make || this.editData.make_name,
      deviceType: this.editData.deviceType || this.editData.devicetype_name || this.editData.device_type,
      modelName: this.editData.model || this.editData.model_name,
      rackSlot: this.editData.position || this.editData.rackSlot || 1,
      face: this.editData.face || this.editData.device_face || '',
      assetOwner: this.editData.asset_owner_name || this.editData.asset_owner || this.editData.assetOwner,
      assetUser: this.normalizeAssetUser(this.editData.asset_user || this.editData.assetUser),
      serialNumber: this.editData.serial_no || this.editData.serial_number || this.editData.serialNumber,
      poNumber: this.editData.po_number || this.editData.PO_number,
      applicationName: this.editData.application_name || this.editData.applications_mapped_name,
      warrantyStartDate: this.editData.warranty_start_date,
      warrantyEndDate: this.editData.warranty_end_date,
      amcStartDate: this.editData.amc_start_date || this.editData.AMC_start_date,
      amcEndDate: this.editData.amc_end_date || this.editData.AMC_end_date,
      description: this.editData.description
    });

    this.buildingInputControl.setValue(this.editData.building_name || this.editData.building || '');
    this.wingInputControl.setValue(this.editData.wing_name || this.editData.wing || '');
    this.floorInputControl.setValue(this.editData.floor_name || this.editData.floor || '');
    this.dcInputControl.setValue(this.editData.datacenter_name || this.editData.datacentre || '');
    this.rackInputControl.setValue(this.editData.rack_name || this.editData.rackNo || '');
    this.makeInputControl.setValue(this.editData.make_name || this.editData.make || '');
    this.deviceTypeInputControl.setValue(this.editData.devicetype_name || this.editData.deviceType || this.editData.device_type || '');
    this.modelInputControl.setValue(this.editData.model_name || this.editData.modelName || '');
    this.assetOwnerInputControl.setValue(this.editData.asset_owner_name || this.editData.asset_owner || this.editData.assetOwner || '');
    this.applicationInputControl.setValue(this.editData.application_name || this.editData.applications_mapped_name || '');
    this.statusInputControl.setValue(this.editData.status || this.editData.device_status || 'active');
    this.faceInputControl.setValue(this.editData.face || this.editData.device_face || '');
    this.assetUserInputControl.setValue(this.normalizeAssetUser(this.editData.asset_user || this.editData.assetUser || ''));
  }

  private prefetchDependentData() {
    if (!this.editData) return;

    if (this.deviceForm.value.make) {
      this.loadDeviceTypes(this.deviceForm.value.make);
      if (this.deviceForm.value.deviceType) {
        this.loadModels(this.deviceForm.value.make, this.deviceForm.value.deviceType);
      }
    }

    if (this.deviceForm.value.building) this.getData('wings');
    if (this.deviceForm.value.wing) this.getData('floors');
    if (this.deviceForm.value.floor) this.getData('datacenters');
    if (this.deviceForm.value.datacentre) this.getData('racks');
  }

}

// Payload shape for device creation
export interface DevicePayload {
  name: string;
  ip: string | null;
  status: string;
  location_name: string;
  building_name: string;
  wing_name: string;
  floor_name: string;
  datacenter_name: string;
  rack_name: string;
  make_name: string;
  devicetype_name: string;
  model_name: string;
  position: number;
  face: string;
  asset_user: string | null;
  asset_owner_name: string | null;
  serial_no: string;
  po_number: string | null;
  application_name: string;
  warranty_start_date: string | null;
  warranty_end_date: string | null;
  amc_start_date: string | null;
  amc_end_date: string | null;
  description: string;
}