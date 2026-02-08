/**
 * Overview: Global context menu component rendered at mouse position with viewport clamping.
 * Architecture: Shared component hosted in app root (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/shared/services/context-menu.service
 * Concepts: Context menu, overlay, viewport clamping, escape handling
 */
import {
  Component,
  ElementRef,
  HostListener,
  inject,
  signal,
  effect,
  afterNextRender,
  viewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ContextMenuService, ContextMenuItem } from '@shared/services/context-menu.service';

@Component({
  selector: 'nimbus-context-menu',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (menuService.state(); as menu) {
      <div class="ctx-backdrop" (click)="menuService.close()"></div>
      <div
        class="ctx-menu"
        #menuEl
        [style.left.px]="posX()"
        [style.top.px]="posY()"
      >
        @for (item of menu.items; track item.label) {
          @if (item.separator) {
            <div class="ctx-separator"></div>
          }
          <button
            class="ctx-item"
            [class.disabled]="item.disabled"
            [disabled]="item.disabled"
            (click)="onItemClick(item)"
          >
            @if (item.icon) {
              <span class="ctx-icon">{{ item.icon }}</span>
            }
            <span>{{ item.label }}</span>
          </button>
        }
      </div>
    }
  `,
  styles: [`
    .ctx-backdrop {
      position: fixed; inset: 0; z-index: 999;
    }
    .ctx-menu {
      position: fixed; z-index: 1000;
      min-width: 180px; max-width: 280px;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.14);
      padding: 0.25rem 0; overflow: hidden;
    }
    .ctx-item {
      display: flex; align-items: center; gap: 0.5rem;
      width: 100%; padding: 0.5rem 0.75rem; border: none;
      background: none; cursor: pointer; font-size: 0.8125rem;
      font-family: inherit; color: #334155; text-align: left;
    }
    .ctx-item:hover:not(.disabled) { background: #f1f5f9; }
    .ctx-item.disabled { opacity: 0.4; cursor: not-allowed; }
    .ctx-icon { width: 1rem; text-align: center; font-size: 0.875rem; }
    .ctx-separator { height: 1px; background: #f1f5f9; margin: 0.25rem 0; }
  `],
})
export class ContextMenuComponent {
  menuService = inject(ContextMenuService);

  posX = signal(0);
  posY = signal(0);

  menuEl = viewChild<ElementRef>('menuEl');

  constructor() {
    effect(() => {
      const menu = this.menuService.state();
      if (menu) {
        // Initial position, will clamp after render
        this.posX.set(menu.x);
        this.posY.set(menu.y);
        afterNextRender(() => this.clampToViewport());
      }
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.menuService.close();
  }

  onItemClick(item: ContextMenuItem): void {
    if (item.disabled) return;
    item.action();
    this.menuService.close();
  }

  private clampToViewport(): void {
    const el = this.menuEl()?.nativeElement;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let x = this.posX();
    let y = this.posY();
    if (x + rect.width > vw - 8) x = vw - rect.width - 8;
    if (y + rect.height > vh - 8) y = vh - rect.height - 8;
    if (x < 8) x = 8;
    if (y < 8) y = 8;
    this.posX.set(x);
    this.posY.set(y);
  }
}
