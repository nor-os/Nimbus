/**
 * Overview: Root-level dialog renderer using NgComponentOutlet with dynamic injector.
 * Architecture: Shared layout component for modal dialogs (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/shared/services/dialog.service
 * Concepts: Dynamic component rendering, focus trap, overlay backdrop, injection tokens
 */
import {
  Component,
  inject,
  computed,
  ElementRef,
  Injector,
  Type,
  ViewChild,
  AfterViewChecked,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgComponentOutlet } from '@angular/common';
import { DialogService, DIALOG_DATA } from '@shared/services/dialog.service';

@Component({
  selector: 'nimbus-dialog-host',
  standalone: true,
  imports: [CommonModule, NgComponentOutlet],
  template: `
    @if (dialogService.activeDialog()) {
      <div class="dialog-backdrop" (click)="onBackdropClick($event)" (keydown)="onKeydown($event)">
        <div class="dialog-card" #dialogCard role="dialog" aria-modal="true">
          <ng-container
            *ngComponentOutlet="activeComponent(); injector: dialogInjector()"
          />
        </div>
      </div>
    }
  `,
  styles: [`
    .dialog-backdrop {
      position: fixed; inset: 0; z-index: 100;
      background: rgba(0, 0, 0, 0.4);
      display: flex; align-items: center; justify-content: center;
      animation: fadeIn 0.15s ease-out;
    }
    .dialog-card {
      background: #fff; border-radius: 8px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
      max-width: 680px; width: 90vw; max-height: 85vh;
      overflow-y: auto; animation: slideUp 0.15s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    @keyframes slideUp {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `],
})
export class DialogHostComponent implements AfterViewChecked {
  dialogService = inject(DialogService);
  private parentInjector = inject(Injector);

  @ViewChild('dialogCard') dialogCard?: ElementRef<HTMLElement>;
  private focusedDialogComponent: Type<unknown> | null = null;

  activeComponent = computed(() => this.dialogService.activeDialog()?.component ?? null);

  dialogInjector = computed(() => {
    const dialog = this.dialogService.activeDialog();
    if (!dialog) return this.parentInjector;
    return Injector.create({
      parent: this.parentInjector,
      providers: [{ provide: DIALOG_DATA, useValue: dialog.data }],
    });
  });

  ngAfterViewChecked(): void {
    const dialog = this.dialogService.activeDialog();
    if (!dialog) {
      this.focusedDialogComponent = null;
      return;
    }
    if (this.dialogCard && this.focusedDialogComponent !== dialog.component) {
      this.focusedDialogComponent = dialog.component;
      setTimeout(() => this.focusFirst());
    }
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.dialogService.close(undefined);
    }
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.dialogService.close(undefined);
      return;
    }
    if (event.key === 'Tab') {
      this.trapFocus(event);
    }
  }

  private focusFirst(): void {
    const el = this.dialogCard?.nativeElement;
    if (!el) return;
    const focusable = el.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    focusable[0]?.focus();
  }

  private trapFocus(event: KeyboardEvent): void {
    const el = this.dialogCard?.nativeElement;
    if (!el) return;
    const focusable = el.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    if (focusable.length === 0) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
}
