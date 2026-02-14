/**
 * Overview: Dynamic property field renderer — renders form fields based on JSON Schema type.
 * Architecture: Reusable form field component for properties panel (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/semantic.service
 * Concepts: JSON Schema type mapping (string->text, number->number, boolean->checkbox, enum->dropdown,
 *     os_image->searchable image picker)
 */
import { Component, EventEmitter, Input, Output, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SemanticService } from '@core/services/semantic.service';
import { OsImage } from '@shared/models/os-image.model';

export interface PropertyFieldDef {
  name: string;
  type: string;
  label?: string;
  description?: string;
  required?: boolean;
  enum?: string[];
  default?: unknown;
}

@Component({
  selector: 'nimbus-property-field',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="property-field">
      <label class="field-label">
        {{ field.label || field.name }}
        @if (field.required) { <span class="required">*</span> }
      </label>

      @switch (field.type) {
        @case ('boolean') {
          <label class="checkbox-wrap">
            <input
              type="checkbox"
              [ngModel]="value"
              (ngModelChange)="valueChange.emit($event)"
              [disabled]="readOnly"
            />
            <span>{{ field.description || '' }}</span>
          </label>
        }
        @case ('number') {
          <input
            type="number"
            class="field-input"
            [ngModel]="value"
            (ngModelChange)="valueChange.emit($event)"
            [disabled]="readOnly"
            [placeholder]="field.description || ''"
          />
        }
        @case ('integer') {
          <input
            type="number"
            step="1"
            class="field-input"
            [ngModel]="value"
            (ngModelChange)="valueChange.emit($event)"
            [disabled]="readOnly"
            [placeholder]="field.description || ''"
          />
        }
        @case ('os_image') {
          <div class="os-image-picker">
            @if (selectedImageName()) {
              <div class="os-image-selected">
                <span class="os-image-name">{{ selectedImageName() }}</span>
                @if (!readOnly) {
                  <button class="os-image-clear" (click)="clearImage()" title="Clear">&times;</button>
                }
              </div>
            }
            @if (!readOnly) {
              <div class="os-image-search-wrap">
                <input
                  type="text"
                  class="field-input"
                  placeholder="Search OS images..."
                  [ngModel]="imageSearchTerm()"
                  (ngModelChange)="imageSearchTerm.set($event)"
                  (focus)="imageDropdownOpen.set(true)"
                  (blur)="onImageBlur()"
                />
                @if (imageDropdownOpen() && filteredImages().length > 0) {
                  <div class="os-image-dropdown">
                    @for (img of filteredImages(); track img.id) {
                      <button class="os-image-option" (mousedown)="selectImage(img)">
                        <span class="os-image-option-name">{{ img.displayName }}</span>
                        <span class="os-image-option-meta">{{ img.osFamily }} &middot; {{ img.architecture }}</span>
                      </button>
                    }
                  </div>
                }
                @if (imageDropdownOpen() && filteredImages().length === 0 && imageSearchTerm()) {
                  <div class="os-image-dropdown">
                    <div class="os-image-empty">No images found</div>
                  </div>
                }
              </div>
            }
          </div>
        }
        @case ('float') {
          <input
            type="number"
            step="any"
            class="field-input"
            [ngModel]="value"
            (ngModelChange)="valueChange.emit($event)"
            [disabled]="readOnly"
            [placeholder]="field.description || ''"
          />
        }
        @default {
          @if (field.enum?.length) {
            <select
              class="field-input"
              [ngModel]="value"
              (ngModelChange)="valueChange.emit($event)"
              [disabled]="readOnly"
            >
              <option [ngValue]="null">-- Select --</option>
              @for (opt of field.enum; track opt) {
                <option [value]="opt">{{ opt }}</option>
              }
            </select>
          } @else {
            <input
              type="text"
              class="field-input"
              [ngModel]="value"
              (ngModelChange)="valueChange.emit($event)"
              [disabled]="readOnly"
              [placeholder]="field.description || ''"
            />
          }
        }
      }
    </div>
  `,
  styles: [`
    .property-field { margin-bottom: 12px; }
    .field-label {
      display: block;
      font-size: 0.6875rem;
      font-weight: 600;
      color: #64748b;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .required { color: #ef4444; }
    .field-input {
      width: 100%;
      padding: 6px 8px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.8125rem;
      color: #1e293b;
      background: #fff;
      outline: none;
      font-family: inherit;
      box-sizing: border-box;
    }
    .field-input:focus { border-color: #3b82f6; }
    .field-input:disabled { background: #f8fafc; color: #94a3b8; }
    .checkbox-wrap {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8125rem;
      color: #374151;
      cursor: pointer;
    }
    select.field-input { cursor: pointer; }

    /* OS image picker */
    .os-image-picker { position: relative; }
    .os-image-selected {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 8px;
      border: 1px solid #bfdbfe;
      border-radius: 6px;
      background: #eff6ff;
      margin-bottom: 6px;
    }
    .os-image-name { font-size: 0.8125rem; font-weight: 500; color: #1e40af; }
    .os-image-clear {
      background: none; border: none; cursor: pointer; color: #93c5fd;
      font-size: 1rem; line-height: 1; padding: 0 2px;
    }
    .os-image-clear:hover { color: #dc2626; }
    .os-image-search-wrap { position: relative; }
    .os-image-dropdown {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      z-index: 20;
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      max-height: 200px;
      overflow-y: auto;
      margin-top: 2px;
    }
    .os-image-option {
      display: flex;
      flex-direction: column;
      width: 100%;
      padding: 8px 10px;
      border: none;
      background: transparent;
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      transition: background 0.1s;
    }
    .os-image-option:hover { background: #f1f5f9; }
    .os-image-option-name { font-size: 0.8125rem; font-weight: 500; color: #1e293b; }
    .os-image-option-meta { font-size: 0.6875rem; color: #94a3b8; }
    .os-image-empty { padding: 12px; text-align: center; color: #94a3b8; font-size: 0.8125rem; }
  `],
})
export class PropertyFieldComponent implements OnInit {
  @Input() field!: PropertyFieldDef;
  private _value = signal<unknown>(null);
  @Input() set value(v: unknown) { this._value.set(v); }
  get value(): unknown { return this._value(); }
  @Input() readOnly = false;
  @Output() valueChange = new EventEmitter<unknown>();

  private semanticService = inject(SemanticService);

  allImages = signal<OsImage[]>([]);
  imageSearchTerm = signal('');
  imageDropdownOpen = signal(false);

  selectedImageName = computed(() => {
    const val = this._value();
    if (!val) return null;
    const img = this.allImages().find(i => i.id === val);
    return img?.displayName || null;
  });

  filteredImages = computed(() => {
    const term = this.imageSearchTerm().toLowerCase().trim();
    const images = this.allImages();
    if (!term) return images;
    return images.filter(
      i => i.displayName.toLowerCase().includes(term) ||
           i.name.toLowerCase().includes(term) ||
           i.osFamily.toLowerCase().includes(term),
    );
  });

  ngOnInit(): void {
    if (this.field?.type === 'os_image') {
      this.loadImages();
    }
  }

  selectImage(img: OsImage): void {
    this.valueChange.emit(img.id);
    this.imageSearchTerm.set('');
    this.imageDropdownOpen.set(false);
  }

  clearImage(): void {
    this.valueChange.emit(null);
  }

  onImageBlur(): void {
    // Delay close to allow click on dropdown option
    setTimeout(() => this.imageDropdownOpen.set(false), 200);
  }

  private loadImages(): void {
    this.semanticService.listOsImages({ limit: 200 }).subscribe({
      next: (list) => this.allImages.set(list.items),
    });
  }
}
