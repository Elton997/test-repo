import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TitleService } from '../../shared/Services/title.service';

@Component({
  selector: 'app-add-manufacturer',
  standalone: true,
  templateUrl: './add-manufacturer.component.html',
  styleUrls: ['./add-manufacturer.component.scss'],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule
  ]
})
export class AddManufacturerComponent implements OnInit {

  manufacturerForm!: FormGroup;
  editData: any = null;
  isEditMode = false;

  constructor(private titleService: TitleService,private fb: FormBuilder, private router: Router) {}

  ngOnInit(): void {
    this.titleService.updateTitle('ADD MAKE');
    this.buildForm();

    // SSR-safe state detection
    if (typeof window !== 'undefined') {
      const st = window.history.state;
      if (st && Object.keys(st).length) {
        this.editData = st;
        this.isEditMode = true;
        this.patchEditForm();
      }
    }
  }

  private buildForm() {
    this.manufacturerForm = this.fb.group({
      id: ['', Validators.required],
      manu_name: ['', Validators.required]
    });
  }

  private patchEditForm() {
    if (!this.editData) return;

    this.manufacturerForm.patchValue({
      id: this.editData.id,
      manu_name: this.editData.manu_name
    });
  }

  saveManufacturer() {
    if (this.manufacturerForm.invalid) {
      this.manufacturerForm.markAllAsTouched();
      return;
    }

    const payload = this.manufacturerForm.value;

    this.router.navigate(['/device-management/manufacturers']);
  }

  cancel() {
    this.router.navigate(['/device-management/manufacturers']);
  }
}
