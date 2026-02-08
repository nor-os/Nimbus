/**
 * Overview: Signal-based dialog manager for rendering dynamic dialog components.
 * Architecture: Shared service for modal dialog lifecycle (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Dialog management, signal state, dynamic component rendering, injection tokens
 */
import { Injectable, InjectionToken, signal, Type } from '@angular/core';

export const DIALOG_DATA = new InjectionToken<unknown>('DIALOG_DATA');

export interface ActiveDialog {
  component: Type<unknown>;
  data: unknown;
  resolve: (result: unknown) => void;
}

@Injectable({ providedIn: 'root' })
export class DialogService {
  readonly activeDialog = signal<ActiveDialog | null>(null);

  open<T>(component: Type<unknown>, data?: unknown): Promise<T> {
    return new Promise<T>((resolve) => {
      this.activeDialog.set({
        component,
        data: data ?? null,
        resolve: resolve as (result: unknown) => void,
      });
    });
  }

  close(result?: unknown): void {
    const dialog = this.activeDialog();
    if (dialog) {
      dialog.resolve(result);
      this.activeDialog.set(null);
    }
  }
}
