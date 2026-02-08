/**
 * Overview: Notification preferences page — category x channel toggle matrix.
 * Architecture: Feature component at /settings/notifications (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/core/services/notification.service
 * Concepts: Preference matrix, category-channel toggles, bulk update
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService } from '@core/services/notification.service';
import {
  NotificationCategory,
  NotificationChannel,
  NotificationPreferenceUpdate,
} from '@shared/models/notification.model';

const CATEGORIES: NotificationCategory[] = [
  'APPROVAL', 'SECURITY', 'SYSTEM', 'AUDIT', 'DRIFT', 'WORKFLOW', 'USER',
];
const CHANNELS: NotificationChannel[] = ['EMAIL', 'IN_APP'];

@Component({
  selector: 'nimbus-notification-preferences',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page">
      <div class="page-header">
        <h1 class="page-title">Notification Preferences</h1>
        @if (dirty()) {
          <button class="btn btn-primary" (click)="save()">Save</button>
        }
      </div>
      <p class="page-description">
        Choose which notification channels are enabled for each category.
        Webhooks are managed at the tenant level in Settings &gt; Webhooks.
      </p>

      <table class="pref-table">
        <thead>
          <tr>
            <th>Category</th>
            @for (channel of channels; track channel) {
              <th>{{ channel }}</th>
            }
          </tr>
        </thead>
        <tbody>
          @for (cat of categories; track cat) {
            <tr>
              <td class="cat-label">{{ cat }}</td>
              @for (channel of channels; track channel) {
                <td>
                  <label class="toggle">
                    <input
                      type="checkbox"
                      [checked]="isEnabled(cat, channel)"
                      (change)="toggle(cat, channel)"
                    />
                    <span class="toggle-slider"></span>
                  </label>
                </td>
              }
            </tr>
          }
        </tbody>
      </table>

      @if (saving()) {
        <div class="status">Saving...</div>
      }
      @if (saved()) {
        <div class="status success">Preferences saved.</div>
      }
    </div>
  `,
  styles: [`
    .page { padding: 1.5rem; max-width: 40rem; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
    .page-title { font-size: 1.25rem; font-weight: 700; color: #e0e0e0; margin: 0; }
    .page-description { font-size: 0.75rem; color: #9ca3af; margin-bottom: 1rem; }
    .pref-table { width: 100%; border-collapse: collapse; }
    .pref-table th {
      padding: 0.5rem 0.75rem; text-align: center; font-size: 0.6875rem;
      font-weight: 600; color: #9ca3af; text-transform: uppercase;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .pref-table th:first-child { text-align: left; }
    .pref-table td {
      padding: 0.625rem 0.75rem; text-align: center;
      border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .cat-label { text-align: left; font-size: 0.8125rem; color: #e0e0e0; font-weight: 500; }
    .toggle { position: relative; display: inline-block; width: 2rem; height: 1.125rem; }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .toggle-slider {
      position: absolute; cursor: pointer; inset: 0;
      background: rgba(255,255,255,0.1); border-radius: 0.5625rem;
      transition: background 0.2s;
    }
    .toggle-slider::before {
      content: ''; position: absolute; height: 0.875rem; width: 0.875rem;
      left: 0.125rem; bottom: 0.125rem; background: #fff; border-radius: 50%;
      transition: transform 0.2s;
    }
    .toggle input:checked + .toggle-slider { background: #3b82f6; }
    .toggle input:checked + .toggle-slider::before { transform: translateX(0.875rem); }
    .btn { padding: 0.375rem 0.75rem; border-radius: 4px; font-size: 0.75rem; cursor: pointer; border: none; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .status { margin-top: 0.75rem; font-size: 0.75rem; color: #9ca3af; }
    .status.success { color: #22c55e; }
  `],
})
export class NotificationPreferencesComponent implements OnInit {
  private notificationService = inject(NotificationService);

  categories = CATEGORIES;
  channels = CHANNELS;

  private prefMap = signal<Record<string, boolean>>({});
  private pendingChanges = signal<Record<string, boolean>>({});
  dirty = signal(false);
  saving = signal(false);
  saved = signal(false);

  ngOnInit(): void {
    this.notificationService.getPreferences().subscribe((prefs) => {
      const map: Record<string, boolean> = {};
      for (const p of prefs) {
        map[`${p.category}:${p.channel}`] = p.enabled;
      }
      this.prefMap.set(map);
    });
  }

  isEnabled(category: NotificationCategory, channel: NotificationChannel): boolean {
    const key = `${category}:${channel}`;
    const pending = this.pendingChanges();
    if (key in pending) return pending[key];
    const saved = this.prefMap();
    if (key in saved) return saved[key];
    return true; // Default enabled
  }

  toggle(category: NotificationCategory, channel: NotificationChannel): void {
    const key = `${category}:${channel}`;
    const current = this.isEnabled(category, channel);
    this.pendingChanges.update((c) => ({ ...c, [key]: !current }));
    this.dirty.set(true);
    this.saved.set(false);
  }

  save(): void {
    const changes = this.pendingChanges();
    const updates: NotificationPreferenceUpdate[] = Object.entries(changes).map(
      ([key, enabled]) => {
        const [category, channel] = key.split(':') as [NotificationCategory, NotificationChannel];
        return { category, channel, enabled };
      },
    );

    if (updates.length === 0) return;

    this.saving.set(true);
    this.notificationService.updatePreferences(updates).subscribe({
      next: (prefs) => {
        const map = { ...this.prefMap() };
        for (const p of prefs) {
          map[`${p.category}:${p.channel}`] = p.enabled;
        }
        this.prefMap.set(map);
        this.pendingChanges.set({});
        this.dirty.set(false);
        this.saving.set(false);
        this.saved.set(true);
      },
      error: () => this.saving.set(false),
    });
  }
}
