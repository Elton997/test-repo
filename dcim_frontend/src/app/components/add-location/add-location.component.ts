import { Component, Inject, OnInit, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { TitleService } from '../../shared/Services/title.service';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-add-location',
  templateUrl: './add-location.component.html',
  styleUrls: ['./add-location.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatIconModule]
})
export class AddLocationComponent implements OnInit {

  locationForm!: FormGroup;
  editData: any = null;

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
    // Detect edit mode
    if (isPlatformBrowser(this.platformId)) {
      const state = this.win.history.state;
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }

    this.titleService.updateTitle(this.editData ? 'EDIT LOCATION' : 'ADD LOCATION');

    this.locationForm = this.fb.group({
      locationId: ['', Validators.required],
      locationName: ['', Validators.required]
    });

    if (this.editData) {
      this.locationForm.patchValue({
        locationId: this.editData.location_id,
        locationName: this.editData.name
      });
    }
  }

  saveLocation() {
    if (this.locationForm.invalid) return;

    console.log("Saving Location →", this.locationForm.getRawValue());
    this.router.navigate(['Organization/Locations']);
  }

  saveAndAddAnother() {
    if (this.locationForm.invalid) return;
    console.log("Save & Add Another →", this.locationForm.getRawValue());
    this.locationForm.reset();
  }

  onCancel() {
    this.router.navigate(['Organization/Locations']);
  }
}
