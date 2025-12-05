# Dynamic Rack Component

A reusable, flexible rack visualization component for displaying rack layouts with device occupancy, similar to NetBox rack views.

## Features

- **Responsive Design**: Works on desktop and mobile devices
- **Customizable**: Support for multiple rack sizes, custom colors, and device labels
- **Interactive**: Click events on device blocks for further actions
- **Accessibility**: Tooltips and proper semantic HTML
- **Legend**: Visual legend showing available vs. occupied slots
- **Front/Back Views**: Support for front and back rack perspectives

## Usage

### Basic Example

```typescript
import { DynamicRackComponent } from './dynamic-rack/dynamic-rack.component';

@Component({
  imports: [DynamicRackComponent],
  template: `
    <app-dynamic-rack
      [units]="42"
      [occupied]="occupiedSlots"
      [viewType]="'front'"
      [title]="'Data Center Rack A42'"
      (deviceClick)="onDeviceClick($event)">
    </app-dynamic-rack>
  `
})
export class MyComponent {
  occupiedSlots = [
    { start: 10, height: 4, label: 'Server-01', color: '#ff9800' },
    { start: 20, height: 2, label: 'Switch-02' },
    { start: 5, height: 1, label: 'Router-03' }
  ];

  onDeviceClick(device: any) {
    console.log('Device clicked:', device);
  }
}
```

## Component API

### Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `units` | `number` | `42` | Total rack units (height of the rack) |
| `occupied` | `Array<{start, height, label?, color?}>` | `[]` | Array of occupied devices |
| `viewType` | `'front' \| 'back'` | `'front'` | Rack view perspective |
| `title` | `string` | `'Rack View'` | Display title for the rack |

### Outputs

| Output | Type | Description |
|--------|------|-------------|
| `deviceClick` | `EventEmitter<any>` | Emits when a device block is clicked |

### Occupied Object Format

```typescript
{
  start: number;        // Starting U position (bottom-based, 1-42)
  height: number;       // Height in U units (e.g., 4 for 4U device)
  label?: string;       // Device name/label
  color?: string;       // Custom color (optional, defaults to orange)
}
```

## Slot Numbering

- **Bottom-to-Top**: Slot 1 is at the bottom, slot 42 is at the top
- **Occupancy**: Device at `start: 10` with `height: 4` occupies slots 10, 11, 12, 13

## Styling

The component uses CSS variables for theming (defined in your global styles):

- `--dcim-navy`: Primary color
- `--dcim-border`: Border color
- `--shadow-sm`: Small shadow
- `--ease-out-expo`: Easing function

## Examples

### Multiple Devices

```typescript
occupiedSlots = [
  { start: 38, height: 2, label: 'PDU-A' },
  { start: 34, height: 3, label: 'Switch-Core' },
  { start: 28, height: 4, label: 'Server-Web-1' },
  { start: 24, height: 2, label: 'Server-DB-1' },
  { start: 10, height: 4, label: 'Server-App-1' },
  { start: 5, height: 2, label: 'Router-Edge' }
];
```

### Front and Back Views

```typescript
<div class="rack-views">
  <app-dynamic-rack
    [units]="42"
    [occupied]="occupiedSlots"
    viewType="front"
    title="Rack A42 - Front">
  </app-dynamic-rack>

  <app-dynamic-rack
    [units]="42"
    [occupied]="occupiedSlots"
    viewType="back"
    title="Rack A42 - Back">
  </app-dynamic-rack>
</div>
```

## Testing

Unit tests are included in `dynamic-rack.component.spec.ts`:

```bash
ng test --include='**/dynamic-rack.component.spec.ts'
```

Tests cover:
- Slot number generation
- Occupied slot detection
- Device block rendering logic
- Event emission

## Accessibility

- Tooltip on hover showing device name
- Semantic HTML structure
- ARIA-friendly with proper labeling
- Keyboard navigable

## Performance

- Uses `*ngFor` with trackBy optimization available
- Efficient change detection
- Minimal re-renders with OnPush strategy (optional enhancement)

## Future Enhancements

- [ ] Drag-and-drop device placement
- [ ] Custom color schemes
- [ ] Power consumption display
- [ ] Device details modal
- [ ] Export rack layout as image
- [ ] Bulk device operations
