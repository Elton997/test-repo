import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AddRacksComponent } from './add-racks.component';

describe('AddRacksComponent', () => {
  let component: AddRacksComponent;
  let fixture: ComponentFixture<AddRacksComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddRacksComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AddRacksComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
