import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TitleService } from '../../shared/Services/title.service';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';

@Component({
  selector: 'app-device-type-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './device-type-details.component.html',
  styleUrl: './device-type-details.component.scss'
})
export class DeviceTypeDetailsComponent implements OnInit, OnDestroy {

  private subscriptions = new Subscription();
  loading: boolean = false;

  // Holds API response
  deviceType: any = null;

  constructor(
    private titleService: TitleService,
    private route: ActivatedRoute,
    private listService: ListService
  ) { }

  ngOnInit(): void {
    this.titleService.updateTitle('DEVICE TYPE DETAILS');
    const id = this.route.snapshot.params['device_type'];
    if (id) {
      this.fetchDeviceTypeDetails(id);
    }
  }

  /** Fetch device type details */
  fetchDeviceTypeDetails(id: string): void {
    this.loading = true;

    this.subscriptions.add(
      this.listService.getDetails('device_types', id).subscribe({
        next: (res: any) => {
          try {
            this.deviceType = {
              id: res?.data?.id,
              type_name: res?.data?.name,
              description: res?.data?.description,
              manufacturer: res?.data?.make?.name,
              height_u: res?.data?.height || res?.data?.model?.height,
              total_models: res?.data?.stats?.model_count,
              total_devices: res?.data?.stats?.device_count
            };
          } catch (innerErr) {
            console.error("Error processing API result:", innerErr);
          } finally {
            this.loading = false;
          }
        },
        error: (err: any) => {
          console.error("API Error:", err);
          this.loading = false;
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}
