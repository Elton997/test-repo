import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ListService } from '../../services/list.service';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { MatButtonModule } from '@angular/material/button';
import { TitleService } from '../../shared/Services/title.service';
import { Menu, SubMenu } from '../../menu.enum';
import { Router } from '@angular/router';

@Component({
  selector: 'app-add-manufacturer',
  standalone: true,
  templateUrl: './add-manufacturer.component.html',
  styleUrls: ['./add-manufacturer.component.scss'],
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule]
})
export class AddManufacturerComponent implements OnInit {

  makeForm!: FormGroup;
  submit = false;
  editData: any = null;

  baseUrl = `${environment.apiUrl}/api/dcim`;

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private listService: ListService,
    @Inject(PLATFORM_ID) private platformId: any,
    private titleService: TitleService,
    private router: Router,
  ) { }

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      const state = window.history.state;
      this.editData = state && Object.keys(state).some(k => k !== 'navigationId') ? state : null;
    }

    this.titleService.updateTitle(this.editData ? 'EDIT MAKE' : 'ADD MAKE');
    this.makeForm = this.fb.group({
      makeName: [
        this.editData?.make_name || '',
        [
          Validators.required,
          Validators.maxLength(100),
          Validators.pattern(/^[A-Za-z0-9 _.\-\/]+$/)
        ]
      ],
      description: [
        this.editData?.description || '',
        Validators.maxLength(200)
      ]
    });

  }

  get f() {
    return this.makeForm.controls;
  }

  resetAllFields() {
    this.submit = false;
    this.makeForm.reset({
      makeName: '',
      description: ''
    });
  }

  saveMake(val: any) {
    this.submit = true;

    if (this.makeForm.invalid) return;

    const payload: MakePayload = {
      name: this.makeForm.value.makeName,
      description: this.makeForm.value.description
    };
    if (this.editData) {
      this.listService.updateMake(this.editData.make_name, payload).subscribe({
        next: () => {
          this.submit = false;
          alert("Make updated successfully!");
        },
        error: (err) => {
          this.submit = false;
          alert(err.error?.message || "Failed to update Make");
        }
      });

      return;
    }

    this.listService.addMake(payload).subscribe({
      next: () => {
        this.submit = false;
        if (val === 'save') {
          alert("Make saved successfully!");
          this.router.navigate([Menu.Device_Management + '/' + SubMenu.Manufacturers]);
        }

        else if (val === 'addAnother') {
          alert("Make saved successfully!");
          this.resetAllFields();
        }
      },
      error: (err) => {
        this.submit = false;
        alert(err.error?.message || "Failed to save Make");
      }
    });
  }
}

export interface MakePayload {
  name: string;
  description?: string;
}
