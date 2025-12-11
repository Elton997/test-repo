import { Component, Inject, OnInit, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { TitleService } from '../../shared/Services/title.service';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ListService } from '../../services/list.service';
import { Menu, SubMenu } from '../../menu.enum';

@Component({
  selector: 'app-add-device-type',
  templateUrl: './add-device-type.component.html',
  styleUrls: ['./add-device-type.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatIconModule]
})
export class AddDeviceTypeComponent implements OnInit {

  deviceTypeForm!: FormGroup;
  editData: any = null;
  submitAttempted = false;
  makes: string[] = [];

  get win(): any {
    return typeof window !== 'undefined' ? window : null;
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

    // detect edit mode
    if (isPlatformBrowser(this.platformId)) {
      const state = this.win.history.state;
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }
    const routeId = this.route.snapshot.paramMap.get('devicetypeID');
    if (!this.editData && routeId) {
      this.listService.getDetails('device_types', routeId).subscribe({
        next: (res: any) => {
          if (res) {
            this.editData = { ...res, name: res?.name || routeId };
            this.patchFormFromEdit();
          }
        },
        error: () => { /* keep form empty if not found */ }
      });
    }

    console.log("Device Type Edit Data:", this.editData);

    this.titleService.updateTitle(this.editData ? 'EDIT DEVICE TYPE' : 'ADD DEVICE TYPE');

    this.deviceTypeForm = this.fb.group({
      deviceTypeName: [this.editData?.device_type_name || this.editData?.device_name || '', Validators.required],
      makeName: [this.editData?.make_name || this.editData?.manufacturer_name || '', Validators.required],
      description: [this.editData?.description || '', Validators.required]
    });

    this.loadMakes();

    if (this.editData) {
      this.patchFormFromEdit();
    }
  }

  saveDeviceType() {
    this.submitAttempted = true;

    if (this.deviceTypeForm.invalid) {
      return;
    }

    const payload = this.deviceTypeForm.getRawValue();
    const apiPayload = {
      name: payload.deviceTypeName,
      make_name: payload.makeName,
      description: payload.description
    };

    const req$ = this.editData
      ? this.listService.updateDeviceType(this.editData?.device_type_name || this.editData?.device_name || payload.deviceTypeName, apiPayload)
      : this.listService.createDeviceType(apiPayload);

    req$.subscribe({
      next: () => {
        this.submitAttempted = false;
        this.router.navigate([Menu.Device_Management + '/' + SubMenu.DeviceTypes]);
      },
      error: (err) => {
        this.submitAttempted = false;
        console.error('Failed to save device type', err);
      }
    });
  }

  saveAndAddAnother() {
    this.submitAttempted = true;
    if (this.deviceTypeForm.invalid) return;

    const payload = this.deviceTypeForm.getRawValue();
    const apiPayload = {
      name: payload.deviceTypeName,
      make_name: payload.makeName,
      description: payload.description
    };

    this.listService.createDeviceType(apiPayload).subscribe({
      next: () => {
        this.submitAttempted = false;
        this.deviceTypeForm.reset();
      },
      error: (err) => {
        this.submitAttempted = false;
        console.error('Failed to save device type', err);
      }
    });
  }

  onCancel() {
    this.router.navigate([Menu.Device_Management + '/' + SubMenu.DeviceTypes]);
  }

  private loadMakes() {
    this.listService.listItems({ entity: 'makes', offset: 0, page_size: 100 })
      .subscribe((res: any) => {
        this.makes = (res?.results || []).map((m: any) => m.name || m.make_name || m.make || m);
        const current = this.deviceTypeForm.get('makeName')?.value;
        const editMake = this.editData?.make_name || this.editData?.manufacturer_name || this.editData?.make || '';
        const candidate = current || editMake;
        if (candidate && !this.makes.includes(candidate)) {
          this.makes.push(candidate);
        }
      });
  }

  private patchFormFromEdit() {
    if (!this.editData) return;
    this.deviceTypeForm.patchValue({
      deviceTypeName: this.editData.device_type_name || this.editData.device_name || this.editData.name || '',
      makeName: this.editData.make_name || this.editData.manufacturer_name || '',
      description: this.editData.description || ''
    });
    // ensure current make is in list
    const makeVal = this.deviceTypeForm.get('makeName')?.value;
    if (makeVal && !this.makes.includes(makeVal)) {
      this.makes.push(makeVal);
    }
  }

}
