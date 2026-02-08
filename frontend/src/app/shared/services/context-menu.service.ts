/**
 * Overview: Service for opening and managing global context menus.
 * Architecture: Shared service for context menu coordination (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Context menu, global overlay, viewport clamping
 */
import { Injectable, signal } from '@angular/core';

export interface ContextMenuItem {
  label: string;
  icon?: string;
  action: () => void;
  separator?: boolean;
  disabled?: boolean;
}

export interface ContextMenuState {
  x: number;
  y: number;
  items: ContextMenuItem[];
}

@Injectable({ providedIn: 'root' })
export class ContextMenuService {
  state = signal<ContextMenuState | null>(null);

  open(event: MouseEvent, items: ContextMenuItem[]): void {
    event.preventDefault();
    event.stopPropagation();
    const x = event.clientX;
    const y = event.clientY;
    this.state.set({ x, y, items });
  }

  close(): void {
    this.state.set(null);
  }
}
