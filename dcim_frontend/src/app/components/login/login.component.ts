import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { InputRestrictionDirective } from '../../shared/Directives/input-restrictions.directive';
import { TitleService } from '../../shared/Services/title.service';
import { LoaderComponent } from '../../shared/Components/loader/loader.component';
import { Subscription } from 'rxjs';
import bcrypt from 'bcryptjs';
import { ErrorService } from '../../services/error.service';

@Component({
  selector: 'app-login',
  standalone: true,
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
  imports: [CommonModule, FormsModule, ReactiveFormsModule, InputRestrictionDirective, LoaderComponent]
})
export class LoginComponent implements OnInit {
  private subscriptions = new Subscription();
  loginForm: FormGroup = new FormGroup({});;
  showPassword = false;
  loading: boolean = false;

  constructor(
    private fb: FormBuilder,
    private auth: AuthService,
    private router: Router, private titleService: TitleService,
    private errorService: ErrorService
  ) {

  }

  ngOnInit(): void {
    this.titleService.updateTitle('LOGIN');
    this.loginForm = this.fb.group({
      username: ['', [Validators.required]],
      password: ['', [Validators.required]]
    });
  }

  get f() {
    return this.loginForm.controls;
  }

  onLogin() {
    if (this.loginForm.valid) {
      const fixedSalt = "$2a$10$EIXCrVhRc0J9wJ62nqmzxe";
      const hashedPassword = bcrypt.hashSync(this.loginForm.value.password, fixedSalt);

      this.subscriptions.add(
        this.auth.login({
          username: this.loginForm.value.username,
          password: hashedPassword
        })
          .subscribe({
            next: (res: any) => {

              if (!res || !res.access_token || !res.refresh_token) {
                this.errorService.showError("Invalid username or password");
                this.loading = false;
                return;
              }

              this.auth.saveTokens(res.access_token, res.refresh_token);
              localStorage.setItem('config', JSON.stringify(res?.configure));
              localStorage.setItem('user', JSON.stringify(res?.user));
              localStorage.setItem('menu', JSON.stringify(res?.menuList));

              this.router.navigate(['/dashboard']);
              this.loading = false;
            },

            error: (err: any) => {
              this.errorService.showError("Invalid username or password");
              this.loading = false;
            }
          })
      );
    }
  }


  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }
}
