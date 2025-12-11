import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { ReactiveFormsModule, FormGroup, FormBuilder, Validators, FormControl } from '@angular/forms';
import { Subscription } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { ListService } from '../../services/list.service';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatInputModule } from '@angular/material/input';
import { Router } from '@angular/router';
import { Menu, SubMenu } from '../../menu.enum';
import { TitleService } from '../../shared/Services/title.service';

@Component({
  selector: 'app-add-model',
  templateUrl: './add-model.component.html',
  styleUrls: ['./add-model.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatIconModule, MatAutocompleteModule, MatInputModule]
})
export class AddModelComponent implements OnInit, OnDestroy {

  modelForm!: FormGroup;
  editData: any = null;
  private subscriptions = new Subscription();

  makes: any[] = [];
  filteredMakes: any[] = [];
  deviceTypes: any[] = [];
  filteredDeviceTypes: any[] = [];

  makeInputControl = new FormControl('');
  deviceTypeInputControl = new FormControl('');

  private baseUrl = `${environment.apiUrl}/api/dcim`;

  submit = false;

  constructor(
    private fb: FormBuilder,
    private listService: ListService,
    private http: HttpClient,
    @Inject(PLATFORM_ID) private platformId: any,
    private router: Router,
    private titleService: TitleService,
  ) { }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      const state = (typeof window !== 'undefined') ? window.history.state : {};
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }

    this.titleService.updateTitle(this.editData ? 'EDIT MODEL' : 'ADD MODEL');

    this.modelForm = this.fb.group({
      modelName: [this.editData?.name ? this.editData?.name : '', [Validators.required, Validators.maxLength(100), Validators.pattern(/^[A-Za-z0-9_-]+$/)]],
      make: [this.editData?.make_name ? this.editData?.make_name : '', Validators.required],
      deviceType: [this.editData?.device_type ? this.editData?.device_type : '', Validators.required],
      height: [this.editData?.height ? this.editData?.height : '', [Validators.required, Validators.pattern(/^\d+$/)]],
      description: [this.editData?.description ? this.editData?.description : '', Validators.maxLength(200)]
    });

    this.getMakes();

    if (this.editData) {
      this.makeInputControl.setValue(this.editData?.make_name);
      this.deviceTypeInputControl.setValue(this.editData?.device_type);
      this.getData("Makes");
    }

    this.subscriptions.add(
      this.modelForm.get('make')!.valueChanges.subscribe(() => {
        this.getData("DeviceTypes");
      })
    );
  }

  get f() {
    return this.modelForm.controls;
  }


  getMakes() {
    this.filteredMakes = [];
    this.makes = [];
    this.filteredDeviceTypes = [];
    this.deviceTypes = [];
    this.makeInputControl.setValue('');
    this.deviceTypeInputControl.setValue('');
    this.modelForm.patchValue({
      deviceType: ''
    });
    this.getData("Makes");
  }

  getDeviceTypes(event: any) {
    if (this.modelForm.value.make != event.option.value) {
      this.modelForm.get('make')?.setValue(event.option.value)
      this.filteredDeviceTypes = [];
      this.deviceTypes = [];
      this.deviceTypeInputControl.setValue('');
      this.modelForm.patchValue({
        deviceType: ''
      });

      this.getData("DeviceTypes");
    }


  }

  getData(val: any) {
    if (val == "Makes") {
      this.subscriptions.add(
        this.listService.listItems({ entity: 'makes' }).subscribe({
          next: (res: any) => {
            this.makes = res?.results || [];
            this.filteredMakes = this.makes;
          },
          error: (err: any) => {
            console.error('Error fetching makes:', err);
            this.makes = [];
            this.filteredMakes = [];
          }
        })
      );
    } else if (val == "DeviceTypes") {
      this.subscriptions.add(
        this.listService.listItems({ entity: 'device_types', make_name: this.modelForm.value.make }).subscribe({
          next: (res: any) => {
            this.deviceTypes = res?.results || [];
            this.filteredDeviceTypes = this.deviceTypes;
          },
          error: (err: any) => {
            console.error('Error fetching device types:', err);
            this.deviceTypes = [];
            this.filteredDeviceTypes = [];
          }
        })
      );
    }
  }

  onSearch(event: any, key: 'make' | 'deviceType') {
    if (event.target.value) {
      const search = event.target.value.toLowerCase();
      if (key === 'make') {
        this.filteredMakes = this.makes.filter(m => (m.name || '').toLowerCase().includes(search));
      } else {
        this.filteredDeviceTypes = this.deviceTypes.filter(d => (d.name || '').toLowerCase().includes(search));
      }
    }
  }

  resetAllFields() {
    this.modelForm.reset({
      modelName: '',
      make: '',
      deviceType: '',
      height: '',
      description: ''
    });

    this.makeInputControl.reset('');
    this.deviceTypeInputControl.reset('');

    this.makes = [];
    this.filteredMakes = [];
    this.deviceTypes = [];
    this.filteredDeviceTypes = [];

    this.getMakes();
  }

  saveModel(val: any) {
    this.submit = true;
    if (this.modelForm.invalid) {
      return;
    }

    this.submit = false;
    const form = this.modelForm.value;

    const payload: ModelPayload = {
      name: form.modelName,
      make_name: form.make,
      devicetype_name: form.deviceType,
      height: Math.floor(Number(form.height)),
      description: form.description || ''
    };

    if (this.editData) {
      this.listService.updateModel(this.editData?.model_name, payload).subscribe({
        next: () => {
          this.submit = false;
          alert("Model updated successfully!");
          this.router.navigate([Menu.Device_Management + '/' + SubMenu.Models]);
        },
        error: () => this.submit = false
      });
    } else {
      this.listService.addModel(payload).subscribe({
        next: () => {
          this.submit = false;

          if (val === 'save') {
            alert("Model saved successfully!");
            this.router.navigate([Menu.Device_Management + '/' + SubMenu.Models]);
          }

          else if (val === 'addAnother') {
            alert("Model saved successfully!");
            this.resetAllFields();
          }
        },
        error: () => this.submit = false
      });
    }
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}

export interface ModelPayload {
  name: string;
  make_name: string;
  devicetype_name: string;
  height: number;
  description?: string;
}
