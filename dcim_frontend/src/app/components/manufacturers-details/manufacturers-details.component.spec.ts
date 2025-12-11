import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ManufacturersDetailsComponent } from './manufacturers-details.component';

describe('ManufacturersDetailsComponent', () => {
  let component: ManufacturersDetailsComponent;
  let fixture: ComponentFixture<ManufacturersDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ManufacturersDetailsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ManufacturersDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
