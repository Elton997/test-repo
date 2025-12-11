import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TitleService } from '../../shared/Services/title.service';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';

@Component({
  selector: 'app-manufacturers-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './manufacturers-details.component.html',
  styleUrls: ['./manufacturers-details.component.scss']
})
export class ManufacturersDetailsComponent implements OnInit, OnDestroy {

  private subscriptions = new Subscription();
  loading: boolean = false;

  make: any = null;

  constructor(
    private titleService: TitleService,
    private route: ActivatedRoute,
    private listService: ListService
  ) { }

  ngOnInit(): void {
    this.titleService.updateTitle('MANUFACTURER DETAILS');

    const makeName = this.route.snapshot.params['manufacturerName'];
    if (makeName) {
      this.fetchMakeDetails(makeName);
    }
  }

  fetchMakeDetails(name: string): void {
    this.loading = true;

    this.subscriptions.add(
      this.listService.getDetails('makes', name).subscribe({
        next: (res: any) => {
          try {
            const data = res?.data;

            this.make = {
              name: data?.name,
              description: data?.description,
              total_models: data?.stats?.total_models,
              total_device_types: data?.stats?.total_device_types,
              total_racks: data?.stats?.total_racks,

              models: data?.models ?? [],
              device_types: data?.device_types ?? []
            };

          } catch (err) {
            console.error("Error mapping manufacturer details:", err);
          } finally {
            this.loading = false;
          }
        },
        error: (err: any) => {
          console.error("API error:", err);
          this.loading = false;
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}
