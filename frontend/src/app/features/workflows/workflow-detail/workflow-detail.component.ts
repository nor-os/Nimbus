/**
 * Overview: Workflow detail — read-only graph view, metadata, and version history.
 * Architecture: Detail page for workflow definitions (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, workflow.service
 * Concepts: Read-only view, version history, definition metadata
 */
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { WorkflowService } from '@core/services/workflow.service';
import { WorkflowDefinition } from '@shared/models/workflow.model';
import { WorkflowCanvasComponent } from '../editor/workflow-canvas.component';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-workflow-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, WorkflowCanvasComponent, LayoutComponent],
  template: `
    <nimbus-layout>
    <div class="page-container">
      @if (definition()) {
        <div class="page-header">
          <div class="header-left">
            <a routerLink="/workflows/definitions" class="back-link">&larr; Back</a>
            <h1>{{ definition()!.name }}</h1>
            <span class="status-badge" [class]="'status-' + definition()!.status">
              {{ definition()!.status }}
            </span>
            <span class="version">v{{ definition()!.version }}</span>
          </div>
          <div class="header-actions">
            @if (definition()!.status === 'DRAFT') {
              <button class="btn" [routerLink]="['/workflows/definitions', definition()!.id, 'edit']">Edit</button>
            }
          </div>
        </div>

        @if (definition()!.description) {
          <p class="description">{{ definition()!.description }}</p>
        }

        <div class="detail-grid">
          <div class="detail-item">
            <label>Timeout</label>
            <span>{{ definition()!.timeoutSeconds }}s</span>
          </div>
          <div class="detail-item">
            <label>Max Concurrent</label>
            <span>{{ definition()!.maxConcurrent }}</span>
          </div>
          <div class="detail-item">
            <label>Created</label>
            <span>{{ definition()!.createdAt | date:'medium' }}</span>
          </div>
          <div class="detail-item">
            <label>Updated</label>
            <span>{{ definition()!.updatedAt | date:'medium' }}</span>
          </div>
        </div>

        @if (definition()!.graph) {
          <div class="canvas-wrapper">
            <nimbus-workflow-canvas
              [graph]="definition()!.graph!"
              [nodeTypes]="nodeTypes()"
              [readOnly]="true"
            />
          </div>
        }
      } @else {
        <div class="loading">Loading...</div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; display: flex; flex-direction: column; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem;
    }
    .header-left { display: flex; align-items: center; gap: 12px; }
    .back-link { color: #64748b; text-decoration: none; font-size: 0.8125rem; }
    .back-link:hover { color: #3b82f6; }
    h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .status-badge { padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600; }
    .status-DRAFT { background: #f1f5f9; color: #64748b; }
    .status-ACTIVE { background: #dcfce7; color: #16a34a; }
    .status-ARCHIVED { background: #fefce8; color: #ca8a04; }
    .version { color: #64748b; font-size: 0.8125rem; }
    .btn {
      padding: 0.5rem 1rem; border: 1px solid #e2e8f0; background: #fff;
      color: #1e293b; border-radius: 6px; cursor: pointer; font-size: 0.8125rem;
      text-decoration: none; transition: background 0.15s;
    }
    .btn:hover { background: #f8fafc; }
    .description { color: #64748b; font-size: 0.8125rem; margin: 0 0 1rem; }
    .detail-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-bottom: 1rem; }
    .detail-item { background: #fff; padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid #e2e8f0; }
    .detail-item label { display: block; font-size: 0.6875rem; color: #64748b; margin-bottom: 2px; }
    .detail-item span { color: #1e293b; font-size: 0.8125rem; }
    .canvas-wrapper { flex: 1; min-height: 400px; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
    .loading { color: #94a3b8; text-align: center; padding: 3rem; }
  `],
})
export class WorkflowDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private workflowService = inject(WorkflowService);

  definition = signal<WorkflowDefinition | null>(null);
  nodeTypes = signal<any[]>([]);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.workflowService.getDefinition(id).subscribe(d => this.definition.set(d));
      this.workflowService.getNodeTypes().subscribe(t => this.nodeTypes.set(t));
    }
  }
}
