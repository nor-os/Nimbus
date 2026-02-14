/**
 * Overview: Standalone OS Image Catalog page — browse, search, and manage OS images with provider mappings.
 * Architecture: Feature component extracted from Semantic Explorer (Section 5)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/semantic.service
 * Concepts: OS image catalog, provider mappings, family-grouped image list, detail panel
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SemanticService } from '@core/services/semantic.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';
import { DialogService } from '@shared/services/dialog.service';
import { ConfirmService } from '@shared/services/confirm.service';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { SemanticProvider } from '@shared/models/semantic.model';
import { OsImage, OsImageProviderMapping } from '@shared/models/os-image.model';
import { ImageDialogComponent } from '../../semantic/dialogs/image-dialog.component';
import { ImageProviderMappingDialogComponent, ImageProviderMappingDialogData } from '../../semantic/dialogs/image-provider-mapping-dialog.component';
import { TenantAssignmentDialogComponent, TenantAssignmentDialogData } from './tenant-assignment-dialog.component';

@Component({
  selector: 'nimbus-os-image-catalog',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  template: `
    <nimbus-layout>
    <div class="explorer">
      <div class="page-header">
        <h1>OS Image Catalog</h1>
        <div class="header-actions" *nimbusHasPermission="'semantic:image:manage'">
          <button class="btn btn-primary" (click)="openImageDialog()">Add Image</button>
          @if (selectedImage()) {
            <button class="btn btn-secondary" (click)="openImageProviderMappingDialog()">Add Mapping</button>
          }
        </div>
      </div>
      <div class="filter-area">
        <input type="text" class="search-input" placeholder="Search images..." [ngModel]="imageSearch()" (ngModelChange)="imageSearch.set($event)" />
        <select [ngModel]="imageFamilyFilter()" (ngModelChange)="imageFamilyFilter.set($event)">
          <option value="">All families</option>
          <option value="linux">Linux</option>
          <option value="windows">Windows</option>
          <option value="macos">macOS</option>
          <option value="bsd">BSD</option>
          <option value="other">Other</option>
        </select>
      </div>

      @if (loading()) {
        <div class="loading">Loading images...</div>
      }

      @if (!loading()) {
        <div class="images-layout">
          <!-- Left: image list grouped by os_family -->
          <div class="image-list-panel">
            @for (group of filteredImageGroups(); track group.family) {
              <div class="img-family-section">
                <div class="img-family-header">
                  <span class="img-family-name">{{ group.familyLabel }}</span>
                  <span class="cat-count">{{ group.images.length }}</span>
                </div>
                @for (img of group.images; track img.id) {
                  <div class="image-item" [class.selected]="selectedImage()?.id === img.id" (click)="selectImage(img)">
                    <div class="image-item-top">
                      <span class="image-item-name">{{ img.displayName }}</span>
                      @if (img.isSystem) { <span class="badge system">System</span> }
                    </div>
                    <div class="image-item-meta">
                      <span class="mono">{{ img.architecture }}</span>
                      <span class="muted">{{ img.providerMappings.length }} mappings</span>
                    </div>
                  </div>
                }
              </div>
            }
            @if (filteredImageGroups().length === 0) {
              <div class="empty-state">No images match your filters.</div>
            }
          </div>

          <!-- Right: selected image detail + provider mappings -->
          @if (selectedImage(); as img) {
            <div class="image-detail-panel">
              <div class="panel-header">
                <h3>{{ img.displayName }}</h3>
                <button class="icon-btn" (click)="selectedImage.set(null)" title="Close">&times;</button>
              </div>
              <div class="panel-badges">
                <span class="badge img-family">{{ img.osFamily }}</span>
                <span class="badge type-badge">{{ img.architecture }}</span>
                @if (img.isSystem) { <span class="badge system">System</span> }
              </div>
              <div class="image-detail-info">
                <div class="detail-row">
                  <span class="detail-label">Name</span>
                  <span class="mono">{{ img.name }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Version</span>
                  <span>{{ img.version }}</span>
                </div>
                @if (img.description) {
                  <div class="detail-row">
                    <span class="detail-label">Description</span>
                    <span>{{ img.description }}</span>
                  </div>
                }
              </div>

              <div class="panel-actions" *nimbusHasPermission="'semantic:image:manage'">
                <button class="btn btn-sm btn-outline" (click)="editImage(img)">Edit Image</button>
                @if (!img.isSystem) {
                  <button class="btn btn-sm btn-danger" (click)="deleteImage(img)">Delete Image</button>
                }
              </div>

              <!-- Provider Mappings -->
              <div class="panel-section">
                <h4>Provider Mappings ({{ img.providerMappings.length }})</h4>
                @if (img.providerMappings.length > 0) {
                  <div class="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Provider</th>
                          <th>Image Reference</th>
                          <th>Notes</th>
                          <th *nimbusHasPermission="'semantic:image:manage'">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (m of img.providerMappings; track m.id) {
                          <tr>
                            <td class="provider-name">{{ m.providerDisplayName }}</td>
                            <td class="mono">{{ m.imageReference }}</td>
                            <td class="muted">{{ m.notes || '\u2014' }}</td>
                            <td *nimbusHasPermission="'semantic:image:manage'">
                              <button class="icon-btn" (click)="editImageProviderMapping(m)" title="Edit">&#9998;</button>
                              @if (!m.isSystem) {
                                <button class="icon-btn danger" (click)="deleteImageProviderMapping(m)" title="Delete">&#10005;</button>
                              }
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                } @else {
                  <div class="empty-state-sm">No provider mappings yet.</div>
                }
              </div>

              <!-- Tenant Availability -->
              <div class="panel-section" *nimbusHasPermission="'semantic:image:assign'">
                <h4>Tenant Availability ({{ img.tenantAssignments.length }})</h4>
                <div class="tenant-actions-row">
                  <button class="btn btn-sm btn-outline" (click)="openTenantAssignmentDialog(img)">Manage Tenants</button>
                </div>
                @if (img.tenantAssignments.length > 0) {
                  <div class="tenant-chips">
                    @for (a of img.tenantAssignments; track a.id) {
                      <span class="tenant-chip">
                        {{ a.tenantName }}
                        <button class="chip-remove" (click)="removeTenantAssignment(img, a.tenantId)" title="Remove">&times;</button>
                      </span>
                    }
                  </div>
                } @else {
                  <div class="empty-state-sm">No tenants assigned. This image is not visible to any tenant.</div>
                }
              </div>
            </div>
          }
        </div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .explorer { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .header-actions { display: flex; gap: 0.5rem; }

    .filter-area { display: flex; gap: 0.5rem; }
    .search-input, .filter-area select {
      padding: 0.4375rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit; color: #374151; background: #fff; outline: none;
    }
    .search-input { width: 240px; }
    .search-input:focus, .filter-area select:focus { border-color: #3b82f6; }

    .loading, .empty-state { padding: 3rem; text-align: center; color: #64748b; }

    /* Images layout */
    .images-layout { display: flex; gap: 1.25rem; min-height: 400px; }
    .image-list-panel {
      width: 320px; min-width: 320px; overflow-y: auto; max-height: calc(100vh - 240px);
    }
    .img-family-section { margin-bottom: 1rem; }
    .img-family-header {
      display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;
      padding-bottom: 0.25rem; border-bottom: 1px solid #e2e8f0;
    }
    .img-family-name { font-weight: 600; color: #1d4ed8; font-size: 0.8125rem; text-transform: capitalize; }
    .cat-count { font-size: 0.75rem; color: #94a3b8; background: #f1f5f9; padding: 0.0625rem 0.5rem; border-radius: 999px; }
    .image-item {
      padding: 0.625rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      margin-bottom: 0.375rem; cursor: pointer; transition: border-color 0.15s, background 0.15s;
      background: #fff;
    }
    .image-item:hover { border-color: #3b82f6; background: #f8fafc; }
    .image-item.selected { border-color: #3b82f6; background: #eff6ff; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
    .image-item-top { display: flex; align-items: center; gap: 0.375rem; }
    .image-item-name { font-weight: 500; font-size: 0.8125rem; color: #1e293b; }
    .image-item-meta { display: flex; gap: 0.75rem; font-size: 0.6875rem; color: #94a3b8; margin-top: 0.125rem; }
    .image-detail-panel {
      flex: 1; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem; overflow-y: auto; max-height: calc(100vh - 240px);
    }
    .image-detail-info { margin-bottom: 1rem; }
    .detail-row { display: flex; gap: 0.75rem; font-size: 0.8125rem; padding: 0.25rem 0; }
    .detail-label { font-weight: 500; color: #64748b; min-width: 90px; }

    /* Shared styles */
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.8125rem; }
    .muted { color: #94a3b8; }
    .badge {
      font-size: 0.625rem; padding: 0.0625rem 0.375rem; border-radius: 3px;
      text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em; white-space: nowrap;
    }
    .badge.system { background: #f1f5f9; color: #64748b; }
    .badge.type-badge { background: #dcfce7; color: #16a34a; font-size: 0.5625rem; text-transform: lowercase; }
    .badge.img-family { background: #dbeafe; color: #1d4ed8; text-transform: capitalize; }

    .icon-btn {
      background: none; border: none; cursor: pointer; color: #94a3b8; font-size: 0.875rem;
      padding: 0.125rem 0.25rem; border-radius: 4px; transition: color 0.15s, background 0.15s;
    }
    .icon-btn:hover { color: #3b82f6; background: rgba(59,130,246,0.08); }
    .icon-btn.danger:hover { color: #dc2626; background: rgba(220,38,38,0.08); }

    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem; transition: all 0.15s; border: none; }
    .btn-sm { font-size: 0.75rem; padding: 0.375rem 0.875rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-outline { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-danger { background: #dc2626; color: #fff; }
    .btn-danger:hover { background: #b91c1c; }

    .panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.375rem; }
    .panel-header h3 { margin: 0; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .panel-badges { display: flex; gap: 0.375rem; margin-bottom: 0.5rem; }
    .panel-actions { display: flex; gap: 0.5rem; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid #f1f5f9; }
    .panel-section { margin-bottom: 1rem; }
    .panel-section h4 {
      font-size: 0.8125rem; font-weight: 600; color: #475569; margin: 0 0 0.5rem;
      padding-bottom: 0.25rem; border-bottom: 1px solid #f1f5f9;
    }
    .provider-name { text-transform: capitalize; font-weight: 500; min-width: 70px; }
    .empty-state-sm { padding: 1rem; text-align: center; color: #94a3b8; font-size: 0.8125rem; }

    .table-wrapper {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    th {
      text-align: left; padding: 0.5rem 0.75rem; color: #64748b; font-weight: 600;
      font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
      border-bottom: 2px solid #e2e8f0; position: sticky; top: 0; background: #fff; z-index: 1;
    }
    td { padding: 0.5rem 0.75rem; color: #374151; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
    tr:hover td { background: #f8fafc; }

    .tenant-actions-row { margin-bottom: 0.5rem; }
    .tenant-chips { display: flex; flex-wrap: wrap; gap: 0.375rem; }
    .tenant-chip {
      display: inline-flex; align-items: center; gap: 0.25rem;
      padding: 0.25rem 0.5rem; background: #eff6ff; border: 1px solid #bfdbfe;
      border-radius: 999px; font-size: 0.75rem; color: #1e40af;
    }
    .chip-remove {
      background: none; border: none; cursor: pointer; color: #93c5fd; font-size: 0.875rem;
      padding: 0; line-height: 1; transition: color 0.15s;
    }
    .chip-remove:hover { color: #dc2626; }
  `],
})
export class OsImageCatalogComponent implements OnInit {
  private semanticService = inject(SemanticService);
  private toast = inject(ToastService);
  private dialogService = inject(DialogService);
  private confirmService = inject(ConfirmService);

  loading = signal(true);
  osImages = signal<OsImage[]>([]);
  selectedImage = signal<OsImage | null>(null);
  imageSearch = signal('');
  imageFamilyFilter = signal('');
  providers = signal<SemanticProvider[]>([]);

  filteredImageGroups = computed(() => {
    const images = this.osImages();
    const term = this.imageSearch().toLowerCase().trim();
    const family = this.imageFamilyFilter();

    const filtered = images.filter((img) => {
      if (family && img.osFamily !== family) return false;
      if (term && !img.displayName.toLowerCase().includes(term) && !img.name.toLowerCase().includes(term)) return false;
      return true;
    });

    const familyLabels: Record<string, string> = { linux: 'Linux', windows: 'Windows', macos: 'macOS', bsd: 'BSD', other: 'Other' };
    const familyOrder = ['linux', 'windows', 'macos', 'bsd', 'other'];
    const grouped = new Map<string, OsImage[]>();
    for (const img of filtered) {
      const fam = img.osFamily || 'other';
      if (!grouped.has(fam)) grouped.set(fam, []);
      grouped.get(fam)!.push(img);
    }

    return familyOrder
      .filter((f) => grouped.has(f))
      .map((f) => ({ family: f, familyLabel: familyLabels[f] || f, images: grouped.get(f)! }));
  });

  ngOnInit(): void {
    this.loadOsImages();
    this.loadProviders();
  }

  selectImage(img: OsImage): void {
    this.selectedImage.set(img);
  }

  async openImageDialog(image?: OsImage): Promise<void> {
    const result = await this.dialogService.open<Record<string, unknown>>(
      ImageDialogComponent,
      image ?? null,
    );
    if (!result) return;

    if (image) {
      this.semanticService.updateOsImage(image.id, result as any).subscribe({
        next: () => { this.toast.success('Image updated'); this.loadOsImages(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    } else {
      this.semanticService.createOsImage(result as any).subscribe({
        next: () => { this.toast.success('Image created'); this.loadOsImages(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    }
  }

  editImage(img: OsImage): void {
    this.openImageDialog(img);
  }

  async deleteImage(img: OsImage): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Image',
      message: `Delete image "${img.displayName}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.semanticService.deleteOsImage(img.id).subscribe({
      next: () => {
        this.toast.success('Image deleted');
        if (this.selectedImage()?.id === img.id) this.selectedImage.set(null);
        this.loadOsImages();
      },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  async openImageProviderMappingDialog(mapping?: OsImageProviderMapping): Promise<void> {
    const img = this.selectedImage();
    if (!img) return;

    const data: ImageProviderMappingDialogData = {
      mapping: mapping ?? null,
      osImageId: img.id,
      providers: this.providers(),
    };
    const result = await this.dialogService.open<Record<string, unknown>>(
      ImageProviderMappingDialogComponent,
      data,
    );
    if (!result) return;

    if (mapping) {
      this.semanticService.updateOsImageProviderMapping(mapping.id, result as any).subscribe({
        next: () => { this.toast.success('Mapping updated'); this.loadOsImages(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    } else {
      this.semanticService.createOsImageProviderMapping(result as any).subscribe({
        next: () => { this.toast.success('Mapping created'); this.loadOsImages(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    }
  }

  editImageProviderMapping(m: OsImageProviderMapping): void {
    this.openImageProviderMappingDialog(m);
  }

  async deleteImageProviderMapping(m: OsImageProviderMapping): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Provider Mapping',
      message: `Delete mapping for "${m.providerDisplayName}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.semanticService.deleteOsImageProviderMapping(m.id).subscribe({
      next: () => { this.toast.success('Mapping deleted'); this.loadOsImages(); },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  async openTenantAssignmentDialog(img: OsImage): Promise<void> {
    const data: TenantAssignmentDialogData = {
      currentTenantIds: img.tenantAssignments.map((a) => a.tenantId),
    };
    const result = await this.dialogService.open<string[] | undefined>(
      TenantAssignmentDialogComponent,
      data,
    );
    if (!result) return;

    this.semanticService.setOsImageTenants(img.id, result).subscribe({
      next: () => { this.toast.success('Tenant assignments updated'); this.loadOsImages(); },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  removeTenantAssignment(img: OsImage, tenantId: string): void {
    const remaining = img.tenantAssignments
      .filter((a) => a.tenantId !== tenantId)
      .map((a) => a.tenantId);
    this.semanticService.setOsImageTenants(img.id, remaining).subscribe({
      next: () => { this.toast.success('Tenant removed'); this.loadOsImages(); },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  private loadOsImages(): void {
    this.loading.set(true);
    this.semanticService.listOsImages().subscribe({
      next: (list) => {
        this.osImages.set(list.items);
        this.loading.set(false);
        const sel = this.selectedImage();
        if (sel) {
          const updated = list.items.find((i) => i.id === sel.id);
          this.selectedImage.set(updated ?? null);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  private loadProviders(): void {
    this.semanticService.listProviders().subscribe({
      next: (providers) => this.providers.set(providers),
    });
  }
}
