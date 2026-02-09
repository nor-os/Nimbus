/**
 * Overview: Searchable icon picker dropdown for selecting Feather/Lucide-style icon names.
 * Architecture: Shared form component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Custom form control, icon grid, search filter, inline SVG previews
 */
import { Component, Input, Output, EventEmitter, signal, inject, ElementRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface IconEntry {
  name: string;
  path: string;
}

/** Feather-icon SVG path data (24x24 viewBox, stroke-based). */
const ICON_ENTRIES: IconEntry[] = [
  { name: 'activity', path: 'M22 12h-4l-3 9L9 3l-3 9H2' },
  { name: 'archive', path: 'M21 8v13H3V8M1 3h22v5H1zM10 12h4' },
  { name: 'at-sign', path: 'M12 16a4 4 0 100-8 4 4 0 000 8zm0 0c0 1.66 1.34 4 4 4 2.76 0 4-2.24 4-4V12a8 8 0 10-3.2 6.4' },
  { name: 'award', path: 'M12 15a7 7 0 100-14 7 7 0 000 14zM8.21 13.89L7 23l5-3 5 3-1.21-9.12' },
  { name: 'bar-chart-2', path: 'M18 20V10M12 20V4M6 20v-6' },
  { name: 'bell', path: 'M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0' },
  { name: 'box', path: 'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16zM3.27 6.96L12 12.01l8.73-5.05M12 22.08V12' },
  { name: 'check-circle', path: 'M22 11.08V12a10 10 0 11-5.93-9.14M22 4L12 14.01l-3-3' },
  { name: 'cloud', path: 'M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z' },
  { name: 'code', path: 'M16 18l6-6-6-6M8 6l-6 6 6 6' },
  { name: 'cpu', path: 'M9 9h6v6H9zM5 3v4M19 3v4M5 17v4M19 17v4M3 5h4M3 19h4M17 5h4M17 19h4M18 9V5H6v14h12v-4' },
  { name: 'database', path: 'M12 2C6.48 2 2 3.79 2 6v12c0 2.21 4.48 4 10 4s10-1.79 10-4V6c0-2.21-4.48-4-10-4zM2 6c0 2.21 4.48 4 10 4s10-1.79 10-4M2 12c0 2.21 4.48 4 10 4s10-1.79 10-4' },
  { name: 'download', path: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3' },
  { name: 'eye', path: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 15a3 3 0 100-6 3 3 0 000 6z' },
  { name: 'file-text', path: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8' },
  { name: 'folder', path: 'M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z' },
  { name: 'git-branch', path: 'M6 3v12M18 9a3 3 0 100-6 3 3 0 000 6zM6 21a3 3 0 100-6 3 3 0 000 6zM18 9a9 9 0 01-9 9' },
  { name: 'globe', path: 'M12 22a10 10 0 100-20 10 10 0 000 20zM2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z' },
  { name: 'hard-drive', path: 'M22 12H2M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11zM6 16h.01M10 16h.01' },
  { name: 'heart', path: 'M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z' },
  { name: 'home', path: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2zM9 22V12h6v10' },
  { name: 'inbox', path: 'M22 12h-6l-2 3H10l-2-3H2M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z' },
  { name: 'key', path: 'M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4' },
  { name: 'layers', path: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5' },
  { name: 'layout', path: 'M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zM3 9h18M9 21V9' },
  { name: 'link', path: 'M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71' },
  { name: 'list', path: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01' },
  { name: 'lock', path: 'M19 11H5a2 2 0 00-2 2v7a2 2 0 002 2h14a2 2 0 002-2v-7a2 2 0 00-2-2zM7 11V7a5 5 0 0110 0v4' },
  { name: 'map', path: 'M1 6v16l7-4 8 4 7-4V2l-7 4-8-4-7 4zM8 2v16M16 6v16' },
  { name: 'monitor', path: 'M20 3H4a2 2 0 00-2 2v10a2 2 0 002 2h16a2 2 0 002-2V5a2 2 0 00-2-2zM8 21h8M12 17v4' },
  { name: 'network', path: 'M12 2a3 3 0 100 6 3 3 0 000-6zM19 16a3 3 0 100 6 3 3 0 000-6zM5 16a3 3 0 100 6 3 3 0 000-6zM12 8v4m-5 2l3-2m4 0l3 2' },
  { name: 'package', path: 'M16.5 9.4l-9-5.19M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16zM3.27 6.96L12 12.01l8.73-5.05M12 22.08V12' },
  { name: 'save', path: 'M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2zM17 21v-8H7v8M7 3v5h8' },
  { name: 'server', path: 'M20 4H4a2 2 0 00-2 2v2a2 2 0 002 2h16a2 2 0 002-2V6a2 2 0 00-2-2zM20 14H4a2 2 0 00-2 2v2a2 2 0 002 2h16a2 2 0 002-2v-2a2 2 0 00-2-2zM6 8h.01M6 18h.01' },
  { name: 'settings', path: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z' },
  { name: 'share-2', path: 'M18 8a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100-6 3 3 0 000 6zM18 22a3 3 0 100-6 3 3 0 000 6zM8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98' },
  { name: 'shield', path: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z' },
  { name: 'star', path: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z' },
  { name: 'tag', path: 'M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82zM7 7h.01' },
  { name: 'terminal', path: 'M4 17l6-6-6-6M12 19h8' },
  { name: 'tool', path: 'M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z' },
  { name: 'trending-up', path: 'M23 6l-9.5 9.5-5-5L1 18M17 6h6v6' },
  { name: 'upload', path: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12' },
  { name: 'user-check', path: 'M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M8.5 11a4 4 0 100-8 4 4 0 000 8zM17 11l2 2 4-4' },
  { name: 'users', path: 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75' },
  { name: 'wifi', path: 'M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01' },
  { name: 'zap', path: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z' },
];

@Component({
  selector: 'nimbus-icon-picker',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="icon-picker" [class.open]="open()">
      <button type="button" class="picker-trigger" (click)="toggle()">
        @if (value) {
          <svg class="icon-preview" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path [attr.d]="getPath(value)" />
          </svg>
          <span class="icon-name">{{ value }}</span>
        } @else {
          <span class="placeholder">Select icon...</span>
        }
        <span class="chevron">&#9662;</span>
      </button>

      @if (open()) {
        <div class="dropdown">
          <div class="search-box">
            <input type="text" [(ngModel)]="search" placeholder="Search icons..." (click)="$event.stopPropagation()" />
          </div>
          <div class="icon-grid">
            <button type="button" class="icon-option none" [class.selected]="!value"
                    (click)="select('')" title="None">
              <span class="no-icon">&#8709;</span>
              <span>None</span>
            </button>
            @for (icon of filteredIcons; track icon.name) {
              <button type="button" class="icon-option" [class.selected]="value === icon.name"
                      (click)="select(icon.name)" [title]="icon.name">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path [attr.d]="icon.path" />
                </svg>
                <span>{{ icon.name }}</span>
              </button>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .icon-picker { position: relative; }
    .picker-trigger {
      display: flex; align-items: center; gap: 0.5rem; width: 100%; box-sizing: border-box;
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit; color: #374151; background: #fff;
      cursor: pointer; outline: none; text-align: left;
    }
    .picker-trigger:focus, .open .picker-trigger { border-color: #3b82f6; }
    .icon-preview { width: 16px; height: 16px; flex-shrink: 0; color: #475569; }
    .icon-name { flex: 1; }
    .placeholder { flex: 1; color: #94a3b8; }
    .chevron { font-size: 0.625rem; color: #94a3b8; margin-left: auto; }
    .dropdown {
      position: absolute; top: calc(100% + 4px); left: 0; right: 0;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.12); z-index: 10;
      max-height: 280px; display: flex; flex-direction: column;
    }
    .search-box { padding: 0.5rem; border-bottom: 1px solid #f1f5f9; }
    .search-box input {
      width: 100%; box-sizing: border-box; padding: 0.375rem 0.625rem;
      border: 1px solid #e2e8f0; border-radius: 4px; font-size: 0.75rem;
      font-family: inherit; outline: none;
    }
    .search-box input:focus { border-color: #3b82f6; }
    .icon-grid {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px;
      padding: 0.375rem; overflow-y: auto;
    }
    .icon-option {
      display: flex; align-items: center; gap: 0.375rem; padding: 0.375rem 0.5rem;
      border: none; background: none; border-radius: 4px; cursor: pointer;
      font-size: 0.6875rem; font-family: inherit; color: #475569; text-align: left;
    }
    .icon-option:hover { background: #f1f5f9; }
    .icon-option.selected { background: #eff6ff; color: #2563eb; }
    .icon-option svg { width: 16px; height: 16px; flex-shrink: 0; }
    .icon-option.none .no-icon { font-size: 14px; width: 16px; text-align: center; color: #94a3b8; }
  `],
})
export class IconPickerComponent {
  private elRef = inject(ElementRef);

  @Input() value = '';
  @Output() valueChange = new EventEmitter<string>();

  open = signal(false);
  search = '';

  get filteredIcons(): IconEntry[] {
    const q = this.search.toLowerCase().trim();
    if (!q) return ICON_ENTRIES;
    return ICON_ENTRIES.filter((i) => i.name.includes(q));
  }

  getPath(name: string): string {
    return ICON_ENTRIES.find((i) => i.name === name)?.path ?? '';
  }

  toggle(): void {
    this.open.update((v) => !v);
    if (this.open()) this.search = '';
  }

  select(name: string): void {
    this.value = name;
    this.valueChange.emit(name);
    this.open.set(false);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elRef.nativeElement.contains(event.target as Node)) {
      this.open.set(false);
    }
  }
}
