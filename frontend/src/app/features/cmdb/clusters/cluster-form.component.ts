/**
 * Overview: Stack blueprint create/edit form with inline slot definition using form arrays.
 *     Each slot supports semantic category and type selection via cascading dropdowns.
 * Architecture: Architecture blueprint management UI (Section 8)
 * Dependencies: @angular/core, @angular/forms, @angular/router, cluster.service, semantic.service
 * Concepts: Standalone component, reactive forms, dynamic slot rows, cascading dropdowns, light theme
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ReactiveFormsModule, FormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ClusterService } from '@core/services/cluster.service';
import { SemanticService } from '@core/services/semantic.service';
import { SemanticCategoryWithTypes } from '@shared/models/semantic.model';
import { ServiceClusterSlot, StackBlueprintParameter } from '@shared/models/cluster.model';

@Component({
  selector: 'nimbus-cluster-form',
  standalone: true,
  imports: [CommonModule, RouterLink, ReactiveFormsModule, FormsModule, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="breadcrumb">
          <a routerLink="/architecture/blueprints" class="breadcrumb-link">Stack Blueprints</a>
          <span class="breadcrumb-sep">/</span>
          <span>{{ isEdit() ? 'Edit' : 'New Blueprint' }}</span>
        </div>

        <h1 class="page-title">{{ isEdit() ? 'Edit Blueprint' : 'Create Stack Blueprint' }}</h1>

        @if (loading()) {
          <div class="loading-state">Loading...</div>
        } @else {
          <form [formGroup]="form" (ngSubmit)="onSubmit()">
            @if (error()) {
              <div class="error-banner">{{ error() }}</div>
            }

            <div class="form-card">
              <h2 class="card-title">General</h2>

              <div class="form-group">
                <label class="form-label">Name *</label>
                <input type="text" class="form-input" formControlName="name" placeholder="e.g. Web Tier, HA Database" />
              </div>

              <div class="form-group">
                <label class="form-label">Description</label>
                <textarea class="form-input form-textarea" formControlName="description"
                  placeholder="Optional description..."></textarea>
              </div>

              <div class="form-group">
                <label class="form-label">Stack Tag Key</label>
                <input type="text" class="form-input" formControlName="stackTagKey"
                  placeholder="e.g. nimbus:stack, environment" />
                <span class="form-hint">Tag key on CIs that identifies deployed instances (stacks) of this blueprint.</span>
              </div>
            </div>

            @if (!isEdit()) {
              <div class="form-card">
                <div class="card-header">
                  <h2 class="card-title">Slots</h2>
                  <button type="button" class="btn btn-sm btn-outline" (click)="addSlotRow()">+ Add Slot</button>
                </div>

                @if (slotsArray.length === 0) {
                  <p class="empty-hint">No slots defined. Add slots to define the blueprint's structure.</p>
                }

                <div formArrayName="slots">
                  @for (slot of slotsArray.controls; track $index) {
                    <div class="slot-row" [formGroupName]="$index">
                      <div class="slot-top-row">
                        <div class="form-group slot-name-group">
                          <label class="form-label">Slot Name *</label>
                          <input type="text" class="form-input" formControlName="name" placeholder="e.g. primary-db" />
                        </div>
                        <div class="form-group slot-display-group">
                          <label class="form-label">Display Name</label>
                          <input type="text" class="form-input" formControlName="displayName" placeholder="Primary Database" />
                        </div>
                        <button type="button" class="btn-icon btn-remove" (click)="removeSlotRow($index)" title="Remove slot">
                          &#10005;
                        </button>
                      </div>

                      <div class="slot-semantic-row">
                        <div class="form-group">
                          <label class="form-label">Resource Kind</label>
                          <select class="form-input" formControlName="semanticCategoryId"
                            (change)="onSlotCategoryChange($index)">
                            <option value="">Any</option>
                            @for (cat of categories(); track cat.id) {
                              <option [value]="cat.id">{{ cat.displayName }}</option>
                            }
                          </select>
                        </div>
                        <div class="form-group">
                          <label class="form-label">Resource Type</label>
                          <select class="form-input" formControlName="semanticTypeId"
                            [class.input-disabled]="!getSlotCategoryId($index)">
                            <option value="">{{ getSlotCategoryId($index) ? 'Any' : 'Select a kind first' }}</option>
                            @for (t of getFilteredTypes($index); track t.id) {
                              <option [value]="t.id">{{ t.displayName }}</option>
                            }
                          </select>
                        </div>
                      </div>

                      <div class="slot-bottom-row">
                        <div class="form-group form-group-sm">
                          <label class="form-label">Min</label>
                          <input type="number" class="form-input" formControlName="minCount" />
                        </div>
                        <div class="form-group form-group-sm">
                          <label class="form-label">Max</label>
                          <input type="number" class="form-input" formControlName="maxCount" placeholder="&#8734;" />
                        </div>
                        <div class="form-group form-group-check">
                          <label class="check-label">
                            <input type="checkbox" formControlName="isRequired" />
                            Required
                          </label>
                        </div>
                        <div class="form-group flex-fill">
                          <label class="form-label">Description</label>
                          <input type="text" class="form-input" formControlName="description" placeholder="Optional..." />
                        </div>
                      </div>
                    </div>
                  }
                </div>
              </div>
            }

            @if (isEdit()) {
              <div class="form-card">
                <div class="card-header">
                  <h2 class="card-title">Slots</h2>
                  <button type="button" class="btn btn-sm btn-outline" (click)="showAddSlot()">+ Add Slot</button>
                </div>

                @if (addingSlot()) {
                  <div class="slot-row">
                    <div class="slot-top-row">
                      <div class="form-group slot-name-group">
                        <label class="form-label">Slot Name *</label>
                        <input type="text" class="form-input" [(ngModel)]="newSlotName" [ngModelOptions]="{standalone:true}" placeholder="e.g. primary-db" />
                      </div>
                      <div class="form-group slot-display-group">
                        <label class="form-label">Display Name</label>
                        <input type="text" class="form-input" [(ngModel)]="newSlotDisplayName" [ngModelOptions]="{standalone:true}" placeholder="Primary Database" />
                      </div>
                    </div>
                    <div class="slot-semantic-row">
                      <div class="form-group">
                        <label class="form-label">Resource Kind</label>
                        <select class="form-input" [(ngModel)]="newSlotCategoryId" [ngModelOptions]="{standalone:true}"
                          (change)="newSlotTypeId = ''">
                          <option value="">Any</option>
                          @for (cat of categories(); track cat.id) {
                            <option [value]="cat.id">{{ cat.displayName }}</option>
                          }
                        </select>
                      </div>
                      <div class="form-group">
                        <label class="form-label">Resource Type</label>
                        <select class="form-input" [(ngModel)]="newSlotTypeId" [ngModelOptions]="{standalone:true}"
                          [class.input-disabled]="!newSlotCategoryId">
                          <option value="">{{ newSlotCategoryId ? 'Any' : 'Select a kind first' }}</option>
                          @for (t of getNewSlotFilteredTypes(); track t.id) {
                            <option [value]="t.id">{{ t.displayName }}</option>
                          }
                        </select>
                      </div>
                    </div>
                    <div class="slot-bottom-row">
                      <div class="form-group form-group-sm">
                        <label class="form-label">Min</label>
                        <input type="number" class="form-input" [(ngModel)]="newSlotMin" [ngModelOptions]="{standalone:true}" />
                      </div>
                      <div class="form-group form-group-sm">
                        <label class="form-label">Max</label>
                        <input type="number" class="form-input" [(ngModel)]="newSlotMax" [ngModelOptions]="{standalone:true}" placeholder="&#8734;" />
                      </div>
                      <div class="form-group form-group-check">
                        <label class="check-label">
                          <input type="checkbox" [(ngModel)]="newSlotRequired" [ngModelOptions]="{standalone:true}" />
                          Required
                        </label>
                      </div>
                      <div class="form-group flex-fill">
                        <label class="form-label">Description</label>
                        <input type="text" class="form-input" [(ngModel)]="newSlotDescription" [ngModelOptions]="{standalone:true}" placeholder="Optional..." />
                      </div>
                      <button type="button" class="btn btn-sm btn-primary" style="margin-top:20px" (click)="addSlotToCluster()" [disabled]="!newSlotName">Add</button>
                      <button type="button" class="btn btn-sm btn-outline" style="margin-top:20px" (click)="addingSlot.set(false)">Cancel</button>
                    </div>
                  </div>
                }

                @if (clusterSlots().length === 0 && !addingSlot()) {
                  <p class="empty-hint">No slots defined. Add slots to define the blueprint's structure.</p>
                }

                @for (s of clusterSlots(); track s.id) {
                  <div class="slot-row">
                    <div class="slot-row-actions">
                      <button type="button" class="btn-remove-abs" (click)="startEditSlot(s)" title="Edit slot">&#x270E;</button>
                      <button type="button" class="btn-remove-abs" (click)="removeSlotFromCluster(s.id)" title="Remove slot">&#10005;</button>
                    </div>
                    @if (editingSlotId() === s.id) {
                      <div class="slot-top-row">
                        <div class="form-group slot-name-group">
                          <label class="form-label">Slot Name *</label>
                          <input type="text" class="form-input" [(ngModel)]="editSlotName" [ngModelOptions]="{standalone:true}" />
                        </div>
                        <div class="form-group slot-display-group">
                          <label class="form-label">Display Name</label>
                          <input type="text" class="form-input" [(ngModel)]="editSlotDisplayName" [ngModelOptions]="{standalone:true}" />
                        </div>
                      </div>
                      <div class="slot-semantic-row">
                        <div class="form-group">
                          <label class="form-label">Resource Kind</label>
                          <select class="form-input" [(ngModel)]="editSlotCategoryId" [ngModelOptions]="{standalone:true}"
                            (change)="editSlotTypeId = ''">
                            <option value="">Any</option>
                            @for (cat of categories(); track cat.id) {
                              <option [value]="cat.id">{{ cat.displayName }}</option>
                            }
                          </select>
                        </div>
                        <div class="form-group">
                          <label class="form-label">Resource Type</label>
                          <select class="form-input" [(ngModel)]="editSlotTypeId" [ngModelOptions]="{standalone:true}"
                            [class.input-disabled]="!editSlotCategoryId">
                            <option value="">{{ editSlotCategoryId ? 'Any' : 'Select a kind first' }}</option>
                            @for (t of getEditSlotFilteredTypes(); track t.id) {
                              <option [value]="t.id">{{ t.displayName }}</option>
                            }
                          </select>
                        </div>
                      </div>
                      <div class="slot-bottom-row">
                        <div class="form-group form-group-sm">
                          <label class="form-label">Min</label>
                          <input type="number" class="form-input" [(ngModel)]="editSlotMin" [ngModelOptions]="{standalone:true}" />
                        </div>
                        <div class="form-group form-group-sm">
                          <label class="form-label">Max</label>
                          <input type="number" class="form-input" [(ngModel)]="editSlotMax" [ngModelOptions]="{standalone:true}" placeholder="&#8734;" />
                        </div>
                        <div class="form-group form-group-check">
                          <label class="check-label">
                            <input type="checkbox" [(ngModel)]="editSlotRequired" [ngModelOptions]="{standalone:true}" />
                            Required
                          </label>
                        </div>
                        <div class="form-group flex-fill">
                          <label class="form-label">Description</label>
                          <input type="text" class="form-input" [(ngModel)]="editSlotDescription" [ngModelOptions]="{standalone:true}" />
                        </div>
                        <button type="button" class="btn btn-sm btn-primary" style="margin-top:20px" (click)="saveEditSlot(s.id)" [disabled]="!editSlotName">Save</button>
                        <button type="button" class="btn btn-sm btn-outline" style="margin-top:20px" (click)="editingSlotId.set(null)">Cancel</button>
                      </div>
                    } @else {
                      <div>
                        <span class="param-name">{{ s.name }}</span>
                        @if (s.displayName && s.displayName !== s.name) {
                          <span class="param-detail-label">({{ s.displayName }})</span>
                        }
                        @if (s.isRequired) {
                          <span class="param-badge param-required">Required</span>
                        }
                      </div>
                      <div class="param-detail">
                        @if (s.semanticCategoryName) {
                          <span>Kind: {{ s.semanticCategoryName }}</span>
                        }
                        @if (s.semanticTypeName) {
                          <span>Type: {{ s.semanticTypeName }}</span>
                        }
                        <span>Min: {{ s.minCount }}</span>
                        <span>Max: {{ s.maxCount ?? '&#8734;' }}</span>
                        @if (s.description) {
                          <span>{{ s.description }}</span>
                        }
                      </div>
                    }
                  </div>
                }
              </div>
            }

            @if (isEdit()) {
              <div class="form-card">
                <div class="card-header">
                  <h2 class="card-title">Parameters</h2>
                  <button type="button" class="btn btn-sm btn-outline" (click)="showAddParam()">+ Custom</button>
                </div>

                @if (addingParam()) {
                  <div class="slot-row">
                    <div class="slot-top-row">
                      <div class="form-group slot-name-group">
                        <label class="form-label">Name *</label>
                        <input type="text" class="form-input" [(ngModel)]="newParamName" [ngModelOptions]="{standalone:true}" placeholder="e.g. instance_type" />
                      </div>
                      <div class="form-group slot-display-group">
                        <label class="form-label">Display Name</label>
                        <input type="text" class="form-input" [(ngModel)]="newParamDisplayName" [ngModelOptions]="{standalone:true}" placeholder="Instance Type" />
                      </div>
                    </div>
                    <div class="slot-bottom-row">
                      <div class="form-group form-group-check">
                        <label class="check-label">
                          <input type="checkbox" [(ngModel)]="newParamRequired" [ngModelOptions]="{standalone:true}" />
                          Required
                        </label>
                      </div>
                      <div class="form-group flex-fill">
                        <label class="form-label">Default Value</label>
                        <input type="text" class="form-input" [(ngModel)]="newParamDefault" [ngModelOptions]="{standalone:true}" placeholder="Optional..." />
                      </div>
                      <button type="button" class="btn btn-sm btn-primary" style="margin-top:20px" (click)="addParam()" [disabled]="!newParamName">Add</button>
                      <button type="button" class="btn btn-sm btn-outline" style="margin-top:20px" (click)="addingParam.set(false)">Cancel</button>
                    </div>
                  </div>
                }

                @if (clusterParams().length === 0 && !addingParam()) {
                  <p class="empty-hint">No parameters defined. Add custom parameters.</p>
                }

                @for (p of clusterParams(); track p.id) {
                  <div class="slot-row">
                    <div class="slot-row-actions">
                      <button type="button" class="btn-remove-abs" (click)="removeParam(p.id)" title="Remove">&#10005;</button>
                    </div>
                    <div>
                      <span class="param-name">{{ p.name }}</span>
                      <span class="param-badge" [class.param-derived]="p.sourceType === 'slot_derived'"
                            [class.param-custom]="p.sourceType === 'custom'">
                        {{ p.sourceType === 'slot_derived' ? 'Slot: ' + (p.sourceSlotName || '?') : 'Custom' }}
                      </span>
                      @if (p.isRequired) {
                        <span class="param-badge param-required">Required</span>
                      }
                    </div>
                    <div class="param-detail">
                      <span class="param-detail-label">{{ p.displayName }}</span>
                      @if (p.defaultValue != null) {
                        <span class="param-default">Default: {{ p.defaultValue }}</span>
                      }
                    </div>
                  </div>
                }
              </div>
            }

            <div class="form-actions">
              <button type="submit" class="btn btn-primary" [disabled]="saving() || form.invalid">
                {{ saving() ? 'Saving...' : (isEdit() ? 'Update' : 'Create') }}
              </button>
              <a routerLink="/architecture/blueprints" class="btn btn-outline">Cancel</a>
            </div>
          </form>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 860px; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 8px 0 1.5rem; }
    .breadcrumb { font-size: 0.8rem; color: #64748b; }
    .breadcrumb-link { color: #3b82f6; text-decoration: none; }
    .breadcrumb-link:hover { text-decoration: underline; }
    .breadcrumb-sep { margin: 0 4px; }

    .form-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 20px; margin-bottom: 16px;
    }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .card-title { font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 16px; }
    .card-header .card-title { margin-bottom: 0; }

    .form-group { margin-bottom: 14px; }
    .form-group-sm { max-width: 80px; }
    .form-group-check { display: flex; align-items: flex-end; padding-bottom: 14px; }
    .flex-fill { flex: 1; }
    .form-label { display: block; font-size: 0.8rem; font-weight: 500; color: #475569; margin-bottom: 4px; }
    .form-input {
      width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; background: #fff; color: #1e293b; box-sizing: border-box;
    }
    .form-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
    .form-input:disabled, .form-input[disabled], .input-disabled { background: #f1f5f9; color: #94a3b8; cursor: not-allowed; }
    .form-textarea { min-height: 80px; resize: vertical; }
    .check-label { font-size: 0.85rem; color: #475569; display: flex; align-items: center; gap: 6px; white-space: nowrap; }

    .slot-row {
      position: relative;
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 14px; margin-bottom: 10px;
    }

    .slot-top-row { display: flex; gap: 8px; align-items: flex-start; }
    .slot-top-row .form-group { margin-bottom: 8px; }
    .slot-name-group { flex: 1; }
    .slot-display-group { flex: 1; }

    .slot-semantic-row { display: flex; gap: 8px; }
    .slot-semantic-row .form-group { flex: 1; margin-bottom: 8px; }

    .slot-bottom-row { display: flex; gap: 8px; align-items: flex-start; }
    .slot-bottom-row .form-group { margin-bottom: 0; }

    .btn-icon {
      background: none; border: none; cursor: pointer; font-size: 1rem;
      color: #94a3b8; padding: 6px; margin-top: 20px; flex-shrink: 0;
    }
    .btn-icon:hover { color: #ef4444; }
    .slot-row-actions {
      position: absolute; top: 8px; right: 8px;
      display: flex; gap: 2px; z-index: 1;
    }
    .btn-remove-abs {
      background: none; border: none; cursor: pointer; font-size: 0.875rem;
      color: #94a3b8; padding: 4px; border-radius: 4px; line-height: 1;
    }
    .btn-remove-abs:hover { color: #ef4444; background: rgba(239,68,68,0.08); }
    .btn-remove-abs:first-child:hover { color: #3b82f6; background: rgba(59,130,246,0.08); }

    .form-hint { display: block; font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }
    .empty-hint { font-size: 0.85rem; color: #94a3b8; text-align: center; padding: 16px; }

    .form-actions { display: flex; gap: 8px; padding-top: 8px; }
    .btn { padding: 10px 20px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-sm { padding: 4px 10px; font-size: 0.8rem; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .error-banner {
      background: #fef2f2; border: 1px solid #fecaca; color: #dc2626;
      padding: 10px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 0.85rem;
    }
    .loading-state { padding: 48px; text-align: center; color: #64748b; }
    .param-name { font-weight: 600; color: #1e293b; font-size: 0.875rem; margin-right: 6px; }
    .param-badge {
      font-size: 0.6875rem; padding: 2px 6px; border-radius: 10px; font-weight: 500;
      display: inline-block; margin-right: 4px;
    }
    .param-derived { background: #eff6ff; color: #3b82f6; }
    .param-custom { background: #f0fdf4; color: #16a34a; }
    .param-required { background: #fef3c7; color: #92400e; }
    .param-detail { font-size: 0.8rem; color: #64748b; margin-top: 4px; display: flex; gap: 12px; }
    .param-detail-label { color: #475569; }
    .param-default { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }
    .check-label {
      font-size: 0.85rem; color: #475569; display: flex; align-items: center; gap: 6px; white-space: nowrap;
    }
    .form-group-check { display: flex; align-items: flex-end; padding-bottom: 14px; }
  `],
})
export class ClusterFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private clusterService = inject(ClusterService);
  private semanticService = inject(SemanticService);

  isEdit = signal(false);
  loading = signal(false);
  saving = signal(false);
  error = signal('');
  categories = signal<SemanticCategoryWithTypes[]>([]);
  clusterSlots = signal<ServiceClusterSlot[]>([]);
  clusterParams = signal<StackBlueprintParameter[]>([]);
  addingSlot = signal(false);
  addingParam = signal(false);
  editingSlotId = signal<string | null>(null);
  newSlotName = '';
  newSlotDisplayName = '';
  newSlotDescription = '';
  newSlotCategoryId = '';
  newSlotTypeId = '';
  newSlotMin = 1;
  newSlotMax: number | null = null;
  newSlotRequired = true;
  editSlotName = '';
  editSlotDisplayName = '';
  editSlotDescription = '';
  editSlotCategoryId = '';
  editSlotTypeId = '';
  editSlotMin = 1;
  editSlotMax: number | null = null;
  editSlotRequired = true;
  newParamName = '';
  newParamDisplayName = '';
  newParamDefault = '';
  newParamRequired = false;
  private clusterId = '';

  form: FormGroup = this.fb.group({
    name: ['', Validators.required],
    description: [''],
    stackTagKey: [''],
    slots: this.fb.array([]),
  });

  get slotsArray(): FormArray {
    return this.form.get('slots') as FormArray;
  }

  ngOnInit(): void {
    this.loadCategories();
    this.clusterId = this.route.snapshot.paramMap.get('id') || '';
    if (this.clusterId) {
      this.isEdit.set(true);
      this.loadCluster();
    }
  }

  loadCategories(): void {
    this.semanticService.listCategories().subscribe({
      next: (cats) => this.categories.set(cats),
    });
  }

  loadCluster(): void {
    this.loading.set(true);
    this.clusterService.getCluster(this.clusterId).subscribe({
      next: (cluster) => {
        if (cluster) {
          this.form.patchValue({
            name: cluster.name,
            description: cluster.description || '',
            stackTagKey: cluster.stackTagKey || '',
          });
          this.clusterSlots.set(cluster.slots || []);
          this.clusterParams.set(cluster.parameters || []);
        }
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  addSlotRow(): void {
    this.slotsArray.push(this.fb.group({
      name: ['', Validators.required],
      displayName: [''],
      description: [''],
      semanticCategoryId: [''],
      semanticTypeId: [''],
      minCount: [1],
      maxCount: [null],
      isRequired: [true],
    }));
  }

  removeSlotRow(index: number): void {
    this.slotsArray.removeAt(index);
  }

  onSlotCategoryChange(index: number): void {
    const slotGroup = this.slotsArray.at(index) as FormGroup;
    slotGroup.get('semanticTypeId')?.setValue('');
  }

  getSlotCategoryId(index: number): string {
    const slotGroup = this.slotsArray.at(index) as FormGroup;
    return slotGroup.get('semanticCategoryId')?.value || '';
  }

  getFilteredTypes(index: number): Array<{ id: string; displayName: string }> {
    const categoryId = this.getSlotCategoryId(index);
    if (!categoryId) return [];
    const cat = this.categories().find(c => c.id === categoryId);
    if (!cat || !cat.types) return [];
    return cat.types.map(t => ({ id: t.id, displayName: t.displayName }));
  }

  onSubmit(): void {
    if (this.form.invalid) return;
    this.saving.set(true);
    this.error.set('');

    const val = this.form.value;

    if (this.isEdit()) {
      this.clusterService.updateCluster(this.clusterId, {
        name: val.name,
        description: val.description || undefined,
        stackTagKey: val.stackTagKey || undefined,
      }).subscribe({
        next: (cluster) => {
          this.saving.set(false);
          this.router.navigate(['/architecture/blueprints', cluster.id]);
        },
        error: (err) => {
          this.saving.set(false);
          this.error.set(err?.message || 'Failed to update cluster');
        },
      });
    } else {
      const slots = (val.slots || []).map((s: Record<string, unknown>, i: number) => ({
        name: s['name'],
        displayName: s['displayName'] || s['name'],
        description: s['description'] || undefined,
        semanticCategoryId: s['semanticCategoryId'] || undefined,
        semanticTypeId: s['semanticTypeId'] || undefined,
        minCount: s['minCount'] ?? 1,
        maxCount: s['maxCount'] || undefined,
        isRequired: s['isRequired'] ?? true,
        sortOrder: i,
      }));

      this.clusterService.createCluster({
        name: val.name,
        description: val.description || undefined,
        stackTagKey: val.stackTagKey || undefined,
        slots,
      }).subscribe({
        next: (cluster) => {
          this.saving.set(false);
          this.router.navigate(['/architecture/blueprints', cluster.id]);
        },
        error: (err) => {
          this.saving.set(false);
          this.error.set(err?.message || 'Failed to create cluster');
        },
      });
    }
  }

  // ── Slot Actions (edit mode) ──────────────────────────────────────

  showAddSlot(): void {
    this.addingSlot.set(true);
    this.newSlotName = '';
    this.newSlotDisplayName = '';
    this.newSlotDescription = '';
    this.newSlotCategoryId = '';
    this.newSlotTypeId = '';
    this.newSlotMin = 1;
    this.newSlotMax = null;
    this.newSlotRequired = true;
  }

  getNewSlotFilteredTypes(): Array<{ id: string; displayName: string }> {
    if (!this.newSlotCategoryId) return [];
    const cat = this.categories().find(c => c.id === this.newSlotCategoryId);
    if (!cat || !cat.types) return [];
    return cat.types.map(t => ({ id: t.id, displayName: t.displayName }));
  }

  addSlotToCluster(): void {
    if (!this.newSlotName) return;
    this.clusterService.addSlot(this.clusterId, {
      name: this.newSlotName,
      displayName: this.newSlotDisplayName || this.newSlotName,
      description: this.newSlotDescription || undefined,
      semanticCategoryId: this.newSlotCategoryId || undefined,
      semanticTypeId: this.newSlotTypeId || undefined,
      minCount: this.newSlotMin,
      maxCount: this.newSlotMax || undefined,
      isRequired: this.newSlotRequired,
      sortOrder: this.clusterSlots().length,
    }).subscribe({
      next: (cluster) => {
        this.clusterSlots.set(cluster.slots || []);
        this.addingSlot.set(false);
      },
      error: (err) => this.error.set(err?.message || 'Failed to add slot'),
    });
  }

  startEditSlot(s: ServiceClusterSlot): void {
    this.editingSlotId.set(s.id);
    this.editSlotName = s.name;
    this.editSlotDisplayName = s.displayName || '';
    this.editSlotDescription = s.description || '';
    this.editSlotCategoryId = s.semanticCategoryId || '';
    this.editSlotTypeId = s.semanticTypeId || '';
    this.editSlotMin = s.minCount;
    this.editSlotMax = s.maxCount ?? null;
    this.editSlotRequired = s.isRequired;
  }

  getEditSlotFilteredTypes(): Array<{ id: string; displayName: string }> {
    if (!this.editSlotCategoryId) return [];
    const cat = this.categories().find(c => c.id === this.editSlotCategoryId);
    if (!cat || !cat.types) return [];
    return cat.types.map(t => ({ id: t.id, displayName: t.displayName }));
  }

  saveEditSlot(slotId: string): void {
    if (!this.editSlotName) return;
    this.clusterService.updateSlot(this.clusterId, slotId, {
      displayName: this.editSlotDisplayName || this.editSlotName,
      description: this.editSlotDescription || undefined,
      semanticCategoryId: this.editSlotCategoryId || undefined,
      semanticTypeId: this.editSlotTypeId || undefined,
      minCount: this.editSlotMin,
      maxCount: this.editSlotMax || undefined,
      isRequired: this.editSlotRequired,
    }).subscribe({
      next: (cluster) => {
        this.clusterSlots.set(cluster.slots || []);
        this.editingSlotId.set(null);
      },
      error: (err) => this.error.set(err?.message || 'Failed to update slot'),
    });
  }

  removeSlotFromCluster(slotId: string): void {
    this.clusterService.removeSlot(this.clusterId, slotId).subscribe({
      next: (cluster) => this.clusterSlots.set(cluster.slots || []),
      error: (err) => this.error.set(err?.message || 'Failed to remove slot'),
    });
  }

  // ── Parameter Actions ─────────────────────────────────────────────


  showAddParam(): void {
    this.addingParam.set(true);
    this.newParamName = '';
    this.newParamDisplayName = '';
    this.newParamDefault = '';
    this.newParamRequired = false;
  }

  addParam(): void {
    if (!this.newParamName) return;
    this.clusterService.addParameter(this.clusterId, {
      name: this.newParamName,
      displayName: this.newParamDisplayName || this.newParamName,
      parameterSchema: { type: 'string' },
      defaultValue: this.newParamDefault || undefined,
      isRequired: this.newParamRequired,
    }).subscribe({
      next: (cluster) => {
        this.clusterParams.set(cluster.parameters || []);
        this.addingParam.set(false);
      },
      error: (err) => this.error.set(err?.message || 'Failed to add parameter'),
    });
  }

  removeParam(paramId: string): void {
    this.clusterService.deleteParameter(this.clusterId, paramId).subscribe({
      next: (cluster) => this.clusterParams.set(cluster.parameters || []),
      error: (err) => this.error.set(err?.message || 'Failed to remove parameter'),
    });
  }
}
