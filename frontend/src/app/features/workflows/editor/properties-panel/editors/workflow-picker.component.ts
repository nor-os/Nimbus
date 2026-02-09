/**
 * Overview: Workflow picker — dropdown of active workflow definitions for subworkflow selection.
 * Architecture: Reusable sub-component for properties panel editors (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, WorkflowService
 * Concepts: Workflow definition selection, lazy loading, dropdown picker
 */
import { Component, EventEmitter, inject, Input, OnInit, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WorkflowService } from '@core/services/workflow.service';

interface WorkflowOption {
  id: string;
  name: string;
}

@Component({
  selector: 'nimbus-workflow-picker',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="workflow-picker">
      @if (loading()) {
        <select class="picker-select" disabled>
          <option>Loading...</option>
        </select>
      } @else {
        <select
          class="picker-select"
          [ngModel]="selected()"
          (ngModelChange)="onSelect($event)"
        >
          <option value="">-- Select Workflow --</option>
          @for (wf of workflows(); track wf.id) {
            <option [value]="wf.id">{{ wf.name }}</option>
          }
        </select>
      }
    </div>
  `,
  styles: [`
    .workflow-picker { width: 100%; }
    .picker-select {
      width: 100%; padding: 6px 8px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 6px; color: #1e293b; font-size: 0.8125rem; outline: none;
      appearance: auto;
    }
    .picker-select:focus { border-color: #3b82f6; }
  `],
})
export class WorkflowPickerComponent implements OnInit {
  private workflowService = inject(WorkflowService);

  @Input() set value(val: string) {
    this.selected.set(val || '');
  }
  @Output() valueChange = new EventEmitter<string>();

  selected = signal('');
  workflows = signal<WorkflowOption[]>([]);
  loading = signal(true);

  ngOnInit(): void {
    this.workflowService.listDefinitions().subscribe({
      next: (defs) => {
        this.workflows.set(
          defs
            .filter((d: any) => d.status === 'PUBLISHED' || d.status === 'DRAFT')
            .map((d: any) => ({ id: d.id, name: d.name }))
        );
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  onSelect(id: string): void {
    this.selected.set(id);
    this.valueChange.emit(id);
  }
}
