import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-rack-view',
  standalone: true,
  templateUrl: './rack-view.component.html',
  styleUrls: ['./rack-view.component.scss'],
  imports: [CommonModule]
})
export class RackViewComponent implements OnInit {
  /** Total rack units (e.g. 42) */
  @Input() units: number = 42;

  /** Occupied items: each item should have start (bottom-based U position), height (in U), label */
  @Input() occupied: Array<{ start: number; height: number; label?: string; color?: string }> = [];

  /** View type: 'front' or 'back' */
  @Input() viewType: 'front' | 'back' = 'front';

  ngOnInit(): void {
    console.log('RackViewComponent initialized', { units: this.units, occupied: this.occupied, viewType: this.viewType });
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
    return slot === (occ.start + occ.height - 1);
  }
}