import { Component, Input, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTooltipModule } from '@angular/material/tooltip';
import html2canvas from 'html2canvas';

@Component({
  selector: 'app-dynamic-rack',
  standalone: true,
  templateUrl: './dynamic-rack.component.html',
  styleUrls: ['./dynamic-rack.component.scss'],
  imports: [CommonModule, MatTooltipModule]
})
export class DynamicRackComponent implements OnInit {
  /** Total rack units (e.g. 42) */
  @Input() units: number = 42;

  /** Occupied items: each item should have start (bottom-based U position), height (in U), label */
  @Input() occupied: Array<{ start: number; height: number; label?: string; color?: string }> = [];

  /** View type: 'front' or 'back' */
  @Input() viewType: 'front' | 'back' = 'front';

  /** Title for the rack view */
  @Input() title: string = 'Rack View';

  /** Emit when a device block is clicked */
  @Output() deviceClick = new EventEmitter<any>();

  ngOnInit(): void {
    console.log('DynamicRackComponent initialized', { units: this.units, occupied: this.occupied, viewType: this.viewType });
  }

  /**
   * Return slots in visual rendering order: top to bottom (42, 41, 40, ... 2, 1)
   * Rack numbering is bottom-to-top: 1 at bottom, units at top
   */
  getSlots(): number[] {
    return Array.from({ length: this.units }, (_, i) => this.units - i);
  }

  /**
   * Check if a slot is occupied by any device
   * Device at start with height occupies: start, start+1, start+2, ... start+height-1
   */
  isOccupied(slot: number) {
    return this.occupied.find(o => slot >= o.start && slot < (o.start + o.height));
  }

  /**
   * Render device block only at the topmost slot of the occupied range
   * For a device starting at slot 10 with height 4, it occupies 10,11,12,13
   * Topmost slot = 10 + 4 - 1 = 13, so render block there
   */
  shouldRenderBlock(slot: number, occ: any): boolean {
    return slot === occ.start;
  }

  /**
   * Handle device block click
   */
  onDeviceClick(device: any): void {
    this.deviceClick.emit(device);
  }

  onSlotClick(slot: number): void {
    const occ = this.isOccupied(slot);

    if (!occ) {
      // Empty slot → user wants to add a device
      this.deviceClick.emit({ empty: true, slot });
    }
  }

  downloadPng() {
    const rackElement = document.querySelector('.dynamic-rack-container');

    if (!rackElement) {
      console.warn('Rack element not found for download');
      return;
    }

    html2canvas(rackElement as HTMLElement, {
      allowTaint: true,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff'
    } as any)
      .then(canvas => {
        const link = document.createElement('a');
        link.download = `${this.title}-${this.viewType}-${new Date().getTime()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
      })
      .catch(error => {
        console.error('Error generating PNG:', error);
      });
  }


}
