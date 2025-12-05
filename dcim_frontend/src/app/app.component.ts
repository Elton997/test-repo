import { Component, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from './services/auth.service';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `<router-outlet></router-outlet>`
})

export class AppComponent {

  constructor(
    private auth: AuthService,
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: any
  ) { }

  ngOnInit() {
    // run only in browser
    // if (isPlatformBrowser(this.platformId)) {

    //   // Detect refresh once
    //   if (performance?.navigation?.type === performance?.navigation?.TYPE_RELOAD) {
    //     this.auth.logout();
    //     this.router.navigate(['/login']);
    //   }
    // }
  }
}
