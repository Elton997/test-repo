import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RacksListComponent } from './racks-list.component';

describe('RacksListComponent', () => {
  let component: RacksListComponent;
  let fixture: ComponentFixture<RacksListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RacksListComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(RacksListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
