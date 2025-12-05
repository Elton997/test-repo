import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeviceTypeDetailsComponent } from './device-type-details.component';

describe('DeviceTypeDetailsComponent', () => {
  let component: DeviceTypeDetailsComponent;
  let fixture: ComponentFixture<DeviceTypeDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeviceTypeDetailsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DeviceTypeDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
