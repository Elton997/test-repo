import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TitleService } from '../../shared/Services/title.service';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { ListService } from '../../services/list.service';

@Component({
  selector: 'app-models-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './models-details.component.html',
  styleUrl: './models-details.component.scss'
})
export class ModelsDetailsComponent implements OnInit, OnDestroy {

  private subscriptions = new Subscription();
  loading: boolean = false;

  model: any = null;

  constructor(
    private titleService: TitleService,
    private route: ActivatedRoute,
    private listService: ListService
  ) { }

  ngOnInit(): void {
    this.titleService.updateTitle('MODEL DETAILS');

    const modelName = this.route.snapshot.params['model_name'];
    if (modelName) {
      this.fetchModelDetails(modelName);
    }
  }

  fetchModelDetails(name: string): void {
    this.loading = true;

    this.subscriptions.add(
      this.listService.getDetails('models', name).subscribe({
        next: (res: any) => {
          try {
            const data = res?.data;

            this.model = {
              id: data?.id,
              name: data?.name,
              u_height: data?.height,
              description: data?.description,
              manufacturer: data?.make?.name,
              device_type: data?.device_type?.name
            };

          } catch (err) {
            console.error('Error mapping model details: ', err);
          } finally {
            this.loading = false;
          }
        },
        error: (err: any) => {
          console.error('API Error:', err);
          this.loading = false;
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}
