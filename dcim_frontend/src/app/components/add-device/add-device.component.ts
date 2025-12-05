import { Component, Inject, OnInit, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { TitleService } from '../../shared/Services/title.service';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-add-device',
  templateUrl: './add-device.component.html',
  styleUrls: ['./add-device.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatIconModule]
})
export class AddDeviceComponent implements OnInit {

  deviceForm!: FormGroup;
  editData: any = null;
  submit: boolean = true;
  selectedFiles: File[] = [];

  // sample one row data
  masterRow: any = {
    Device_name: "Core Switch 01",
    status: "Active",
    location: "Mumbai",
    building: "DC Building 1",
    wing: "West Wing",
    floor: "Ground Floor",
    room_no: "R101",
    data_center: "Primary DC",
    rack_no: "RACK-A1",
    Height: 1,
    Device_type: "Switch",
    Model_name: "Cisco Catalyst 9300",
    serial_number: "CSW9300-001",
    manufacturer: "Cisco",
    ip_address: "10.10.1.10",
    PO_number: "PO-5001",
    warranty_start_date: "2023-01-10",
    warranty_end_date: "2026-01-10",
    AMC_start_date: "2024-01-10",
    AMC_end_date: "2025-01-10",
    asset_owner: "IT-Network",
    asset_user: "In Use",
    application_mapping: "Core Network"
  };

  // setting up dropdowns
  locations = [this.masterRow.location];
  buildings = [this.masterRow.building];
  wings = [this.masterRow.wing];
  floors = [this.masterRow.floor];
  rooms = [this.masterRow.room_no];
  datacentres = [this.masterRow.data_center];
  racks = [this.masterRow.rack_no];
  deviceTypes = [this.masterRow.Device_type];
  manufacturers = [this.masterRow.manufacturer];
  statuses = ["Active", "Inactive", "Maintenance"];

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
    console.log("This is the edit data: ", this.editData);
    this.titleService.updateTitle(this.editData ? 'EDIT DEVICE' : 'ADD DEVICE');

    
    this.deviceForm = this.fb.group({
      deviceName: ['', Validators.required],
      status: ['', Validators.required],
      location: ['', Validators.required],
      building: ['', Validators.required],
      wing: ['', Validators.required],
      floor: ['', Validators.required],
      roomNo: ['', Validators.required],
      datacentre: ['', Validators.required],
      rackNo: ['', Validators.required],
      height: ['', Validators.required],
      deviceType: ['', Validators.required],
      modelName: ['', Validators.required],
      serialNumber: ['', Validators.required],
      manufacturer: ['', Validators.required],
      ipAddress: [''],
      poNumber: [''],
      warrantyStartDate: [''],
      warrantyEndDate: [''],
      amcStartDate: [''],
      amcEndDate: [''],
      assetOwner: [''],
      assetUser: [''],
      applicationMapping: [''],
      attachments: [null]
    });

    // patch if it isedit mode
    if (this.editData) {
      this.deviceForm.patchValue({
        deviceName: this.editData.Device_name,
        status: this.editData.status,
        location: this.editData.location,
        building: this.editData.building,
        wing: this.editData.wing,
        floor: this.editData.floor,
        roomNo: this.editData.room_no,
        datacentre: this.editData.data_center,
        rackNo: this.editData.rack_no,
        height: this.editData.Height,
        deviceType: this.editData.Device_type,
        modelName: this.editData.Model_name,
        serialNumber: this.editData.serial_number,
        manufacturer: this.editData.manufacturer,
        ipAddress: this.editData.ip_address,
        poNumber: this.editData.PO_number,
        warrantyStartDate: this.editData.warranty_start_date,
        warrantyEndDate: this.editData.warranty_end_date,
        amcStartDate: this.editData.AMC_start_date,
        amcEndDate: this.editData.AMC_end_date,
        assetOwner: this.editData.asset_owner,
        assetUser: this.editData.asset_user,
        applicationMapping: this.editData.application_mapping
      });
    }
  }

  onFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files) return;

    // convert FileList to array and append to selectedFiles
    const filesArray = Array.from(input.files);
    this.selectedFiles = this.selectedFiles.concat(filesArray);

    // clear the input so the same file can be re-selected if needed
    input.value = '';
  }

  removeFile(index: number) {
    if (index >= 0 && index < this.selectedFiles.length) {
      this.selectedFiles.splice(index, 1);
    }
  }

  saveDevice() {
    this.submit = true;

    if (this.deviceForm.invalid) {
      this.submit = false;
      return;
    }

    const payload = this.deviceForm.getRawValue();
    // attach basic file metadata (actual File objects cannot be JSON-stringified)
    payload.attachments = this.selectedFiles.map(f => ({ name: f.name, size: f.size, type: f.type }));
    console.log("SAVING DEVICE → ", payload);

    this.router.navigate(['DeviceManagement/Devices']);
  }

  saveAndAddAnother() {
    if (this.deviceForm.invalid) return;

    console.log("SAVE & ADD ANOTHER → ", this.deviceForm.getRawValue());

    this.deviceForm.reset();
    this.selectedFiles = [];
  }

  onCancel() {
    this.router.navigate(['DeviceManagement/Devices']);
  }

}
