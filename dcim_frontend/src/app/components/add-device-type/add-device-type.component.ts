import { Component, Inject, OnInit, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { TitleService } from '../../shared/Services/title.service';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

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
  submit: boolean = true;

  
  // sample row
  masterRow = {
    id: 1,
    device_name: 'Switch',
    predefined_height: 1,
    manufactures_id: 1,
    models_name: 'OEMR XL R210'
  };

  
  deviceNames = [this.masterRow.device_name];
  predefinedHeights = [this.masterRow.predefined_height, 1, 2, 4, 6]; // you may extend
  manufacturerIDs = [this.masterRow.manufactures_id, 1, 2, 3, 4, 5];
  modelNames = [this.masterRow.models_name];

  get win(): any {
    return typeof window !== 'undefined' ? window : null;
  }

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private titleService: TitleService,
    @Inject(PLATFORM_ID) private platformId: any
  ) {}

  ngOnInit(): void {

    // detect edit mode
    if (isPlatformBrowser(this.platformId)) {
      const state = this.win.history.state;
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }

    console.log("Device Type Edit Data:", this.editData);

    this.titleService.updateTitle(this.editData ? 'EDIT DEVICE TYPE' : 'ADD DEVICE TYPE');

    this.deviceTypeForm = this.fb.group({
      deviceName: ['', Validators.required],
      predefinedHeight: ['', Validators.required],
      manufacturerID: ['', Validators.required],
      modelName: ['', Validators.required]
    });

    if (this.editData) {
      this.deviceTypeForm.patchValue({
        deviceName: this.editData.device_name,
        predefinedHeight: this.editData.predefined_height,
        manufacturerID: this.editData.manufactures_id,
        modelName: this.editData.models_name
      });
    }
  }

  saveDeviceType() {
    this.submit = true;

    if (this.deviceTypeForm.invalid) {
      this.submit = false;
      return;
    }

    console.log("Device Type Saved:", this.deviceTypeForm.getRawValue());

    this.router.navigate(['/device-types']);
  }

  saveAndAddAnother() {
    if (this.deviceTypeForm.invalid) return;

    console.log("Save & Add Another:", this.deviceTypeForm.getRawValue());

    this.deviceTypeForm.reset();
  }

  onCancel() {
    this.router.navigate(['/device-types']);
  }

}
