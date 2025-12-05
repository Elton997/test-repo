import { Component, Inject, OnInit, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { TitleService } from '../../shared/Services/title.service';

@Component({
  selector: 'app-add-building',
  templateUrl: './add-building.component.html',
  styleUrls: ['./add-building.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule]
})
export class AddBuildingComponent implements OnInit {

  buildingForm!: FormGroup;
  editData: any = null;

  statuses = ['Active', 'Inactive', 'Maintenance'];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private titleService: TitleService,
    @Inject(PLATFORM_ID) private platformId: any
  ) { }

  get win(): any {
    return typeof window !== 'undefined' ? window : null;
  }

  ngOnInit(): void {

    // detect edit mode
    if (isPlatformBrowser(this.platformId)) {
      const state = this.win.history.state;
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }

    this.titleService.updateTitle(this.editData ? 'EDIT BUILDING' : 'ADD BUILDING');

    this.buildingForm = this.fb.group({
      building_id: ['', Validators.required],
      name: ['', Validators.required],
      status: ['', Validators.required],
      location_id: ['', Validators.required]
    });

    // patch values in edit mode
    if (this.editData) {
      this.buildingForm.patchValue({
        building_id: this.editData.building_id,
        name: this.editData.name,
        status: this.editData.status,
        location_id: this.editData.location_id
      });
    }
  }

  saveBuilding() {
    if (this.buildingForm.invalid) return;

    console.log("Saving Building →", this.buildingForm.getRawValue());

    this.router.navigate(['BuildingManagement/Buildings']);
  }

  saveAndAddAnother() {
    if (this.buildingForm.invalid) return;

    console.log("Saving & Adding Another →", this.buildingForm.getRawValue());
    this.buildingForm.reset();
  }

  onCancel() {
    this.router.navigate(['Organization/Buildings']);
  }
}
