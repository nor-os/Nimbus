/**
 * Overview: Landing zone organizational strategy selector — isolation, topology, and shared services decisions with hierarchy generation.
 * Architecture: Feature component for LZ strategy selection (Section 7.2)
 * Dependencies: @angular/core, @angular/common, EnvConfiguratorComponent, ConfirmService
 * Concepts: Wraps EnvConfiguratorComponent with catalogSource='lz' for the organization domain.
 *   When an isolation strategy tile is selected, hierarchy_implications generate an initial hierarchy tree.
 */
import {
  Component,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  OnChanges,
  SimpleChanges,
  signal,
  computed,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { LandingZoneService } from '@core/services/landing-zone.service';
import { ConfirmService } from '@shared/services/confirm.service';
import { ConfigOption } from '@shared/models/env-config-option.model';
import { LandingZoneHierarchy, HierarchyNode } from '@shared/models/landing-zone.model';
import { EnvConfiguratorComponent } from '../../environments/env-configurator/env-configurator.component';

@Component({
  selector: 'nimbus-lz-strategy',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, EnvConfiguratorComponent],
  template: `
    <div class="lz-strategy">
      <h3 class="section-title">Organizational Strategy</h3>
      <p class="section-desc">Define how tenants and environments are isolated, network topology, and shared services.</p>
      <nimbus-env-configurator
        domain="organization"
        [providerName]="providerName"
        [currentValues]="orgValues()"
        [schema]="null"
        catalogSource="lz"
        (valuesChange)="onOrgChange($event)"
      />
      @if (generatedHierarchyDesc()) {
        <div class="hierarchy-preview">
          <span class="preview-icon">&#9656;</span>
          <span class="preview-label">Generated hierarchy:</span>
          <span class="preview-text">{{ generatedHierarchyDesc() }}</span>
        </div>
      }
    </div>
  `,
  styles: [`
    .lz-strategy { }
    .section-title {
      font-size: 0.875rem; font-weight: 600; color: #1e293b; margin: 0 0 4px;
    }
    .section-desc {
      font-size: 0.75rem; color: #64748b; margin: 0 0 12px; line-height: 1.4;
    }
    .hierarchy-preview {
      display: flex; align-items: center; gap: 6px;
      padding: 8px 12px; margin-top: 12px;
      background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;
    }
    .preview-icon { color: #16a34a; font-size: 0.875rem; }
    .preview-label { font-size: 0.75rem; font-weight: 600; color: #166534; }
    .preview-text { font-size: 0.75rem; color: #374151; }
  `],
})
export class LzStrategyComponent implements OnChanges {
  @Input() providerName = '';
  @Input() currentSettings: Record<string, unknown> = {};
  @Input() currentHierarchy: LandingZoneHierarchy | null = null;

  @Output() settingsChange = new EventEmitter<Record<string, unknown>>();
  @Output() hierarchyChange = new EventEmitter<LandingZoneHierarchy>();

  private lzService = inject(LandingZoneService);
  private confirmService = inject(ConfirmService);

  private loadedOptions = signal<ConfigOption[]>([]);
  generatedHierarchyDesc = signal<string>('');

  orgValues = computed(() => {
    const strat = this.currentSettings?.['strategySelections'] as Record<string, unknown> | undefined;
    return (strat?.['organization'] as Record<string, unknown>) ?? {};
  });

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['providerName'] && this.providerName) {
      this.loadOptions();
    }
  }

  private loadOptions(): void {
    this.lzService.getLzConfigOptions(this.providerName, 'organization').subscribe({
      next: opts => this.loadedOptions.set(opts),
    });
  }

  async onOrgChange(values: Record<string, unknown>): Promise<void> {
    // Emit the settings update
    const updatedSettings = {
      ...this.currentSettings,
      strategySelections: {
        ...((this.currentSettings?.['strategySelections'] as Record<string, unknown>) ?? {}),
        organization: values,
      },
    };
    this.settingsChange.emit(updatedSettings);

    // Check if any selected option has hierarchy_implications
    const opts = this.loadedOptions();
    let matchedOption: ConfigOption | null = null;
    for (const opt of opts) {
      if (this.optionMatchesValues(opt, values) && opt.hierarchyImplications) {
        matchedOption = opt;
        break;
      }
    }

    if (matchedOption?.hierarchyImplications) {
      const implications = matchedOption.hierarchyImplications;
      const hasExisting = this.currentHierarchy && (this.currentHierarchy.nodes?.length ?? 0) > 0;

      if (hasExisting) {
        const ok = await this.confirmService.confirm({
          title: 'Generate Hierarchy',
          message: `The "${matchedOption.displayName}" strategy will generate a new hierarchy: ${implications.description}. This will replace the current hierarchy. Continue?`,
          confirmLabel: 'Generate',
        });
        if (!ok) return;
      }

      const hierarchy = this.generateHierarchy(implications);
      this.generatedHierarchyDesc.set(implications.description);
      this.hierarchyChange.emit(hierarchy);
    }
  }

  private generateHierarchy(implications: { description: string; nodes: { typeId: string; label: string; parentId: string | null }[] }): LandingZoneHierarchy {
    const nodeIds: string[] = [];
    const nodes: HierarchyNode[] = [];

    for (let i = 0; i < implications.nodes.length; i++) {
      const template = implications.nodes[i];
      const id = crypto.randomUUID();
      nodeIds.push(id);

      let parentId: string | null = null;
      if (template.parentId) {
        const match = template.parentId.match(/^__idx_(\d+)$/);
        if (match) {
          const idx = parseInt(match[1], 10);
          parentId = nodeIds[idx] ?? null;
        }
      }

      nodes.push({
        id,
        parentId,
        typeId: template.typeId,
        label: template.label,
        properties: {},
      });
    }

    return { nodes };
  }

  private optionMatchesValues(opt: ConfigOption, values: Record<string, unknown>): boolean {
    for (const [key, val] of Object.entries(opt.configValues)) {
      if (values[key] === undefined) return false;
      if (JSON.stringify(values[key]) !== JSON.stringify(val)) return false;
    }
    return Object.keys(opt.configValues).length > 0;
  }
}
