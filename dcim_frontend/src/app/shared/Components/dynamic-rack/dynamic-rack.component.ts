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
   * Get complete style object for device block based on occupied item
   */
  getDeviceBlockStyle(occ: any): any {
    const style: any = {
      height: (occ.height * 28) + 'px'
    };
    
    if (!occ.color) {
      style.background = 'linear-gradient(135deg, #ffcb69 0%, #ffd89b 100%)';
      style.borderColor = '#ffb84d';
      return style;
    }
    
    // For gray color, use a gradient for better visual effect with reduced opacity
    if (occ.color === '#b0b0b0' || occ.color.toLowerCase().includes('grey')) {
      style.background = `linear-gradient(135deg, ${occ.color} 0%, ${this.darkenColor(occ.color, 10)} 100%)`;
      style.borderColor = this.darkenColor(occ.color, 20);
      style.opacity = '0.7';
      return style;
    }
    
    // For other colors (like green for selected device), use gradient
    style.background = `linear-gradient(135deg, ${occ.color} 0%, ${this.darkenColor(occ.color, 10)} 100%)`;
    style.borderColor = this.darkenColor(occ.color, 20);
    return style;
  }

  /**
   * Darken a hex color by a percentage
   */
  private darkenColor(color: string, percent: number): string {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.max(0, Math.min(255, (num >> 16) - amt));
    const G = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) - amt));
    const B = Math.max(0, Math.min(255, (num & 0x0000FF) - amt));
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
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
