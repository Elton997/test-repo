import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DynamicRackComponent } from './dynamic-rack.component';

describe('DynamicRackComponent', () => {
  let component: DynamicRackComponent;
  let fixture: ComponentFixture<DynamicRackComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DynamicRackComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DynamicRackComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should generate correct slot numbers', () => {
    component.units = 42;
    const slots = component.getSlots();
    expect(slots[0]).toBe(42);
    expect(slots[slots.length - 1]).toBe(1);
    expect(slots.length).toBe(42);
  });

  it('should correctly identify occupied slots', () => {
    component.occupied = [{ start: 10, height: 4, label: 'Device1' }];
    expect(component.isOccupied(10)).toBeTruthy();
    expect(component.isOccupied(11)).toBeTruthy();
    expect(component.isOccupied(13)).toBeTruthy();
    expect(component.isOccupied(14)).toBeFalsy();
  });

  it('should render block only at topmost occupied slot', () => {
    const occ = { start: 10, height: 4, label: 'Device1' };
    expect(component.shouldRenderBlock(13, occ)).toBe(true);
    expect(component.shouldRenderBlock(12, occ)).toBe(false);
    expect(component.shouldRenderBlock(10, occ)).toBe(false);
  });

  it('should emit device click event', (done) => {
    const testDevice = { start: 10, height: 4, label: 'Device1' };
    component.deviceClick.subscribe((device) => {
      expect(device).toEqual(testDevice);
      done();
    });
    component.onDeviceClick(testDevice);
  });
});
