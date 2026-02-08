/**
 * Overview: Root application component that restores auth session on startup.
 * Architecture: Top-level component with router outlet (Section 3.2)
 * Dependencies: @angular/core, @angular/router, app/core/auth/auth.service
 * Concepts: Application shell, session restore
 */
import { Component, inject, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth/auth.service';
import { DialogHostComponent } from '@shared/components/dialog-host/dialog-host.component';
import { ToastHostComponent } from '@shared/components/toast-host/toast-host.component';
import { ContextMenuComponent } from '@shared/components/context-menu/context-menu.component';

@Component({
  selector: 'nimbus-root',
  standalone: true,
  imports: [RouterOutlet, DialogHostComponent, ToastHostComponent, ContextMenuComponent],
  template: `
    <router-outlet />
    <nimbus-dialog-host />
    <nimbus-toast-host />
    <nimbus-context-menu />
  `,
})
export class AppComponent implements OnInit {
  private authService = inject(AuthService);

  ngOnInit(): void {
    this.authService.tryRestoreSession();
  }
}
