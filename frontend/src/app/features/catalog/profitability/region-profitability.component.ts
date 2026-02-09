/**
 * Overview: Region profitability breakdown — table showing per-region financial metrics.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core
 * Concepts: Region profitability, delivery region analysis
 */
import {
  Component,
  Input,
  signal,
  computed,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProfitabilityByEntity } from '@shared/models/delivery.model';

type SortColumn = 'entityName' | 'totalRevenue' | 'totalCost' | 'marginAmount' | 'marginPercent' | 'estimationCount';
type SortDirection = 'asc' | 'desc';

@Component({
  selector: 'nimbus-region-profitability',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="table-container">
      <table class="table">
        <thead>
          <tr>
            <th class="sortable" (click)="onSort('entityName')">
              Region Name <span class="sort-icon">{{ getSortIcon('entityName') }}</span>
            </th>
            <th class="sortable num" (click)="onSort('totalRevenue')">
              Revenue <span class="sort-icon">{{ getSortIcon('totalRevenue') }}</span>
            </th>
            <th class="sortable num" (click)="onSort('totalCost')">
              Cost <span class="sort-icon">{{ getSortIcon('totalCost') }}</span>
            </th>
            <th class="sortable num" (click)="onSort('marginAmount')">
              Margin <span class="sort-icon">{{ getSortIcon('marginAmount') }}</span>
            </th>
            <th class="sortable num" (click)="onSort('marginPercent')">
              Margin % <span class="sort-icon">{{ getSortIcon('marginPercent') }}</span>
            </th>
            <th class="sortable num" (click)="onSort('estimationCount')">
              # Estimations <span class="sort-icon">{{ getSortIcon('estimationCount') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          @for (row of sortedData(); track row.entityId) {
            <tr>
              <td class="name-cell">{{ row.entityName }}</td>
              <td class="num">{{ row.totalRevenue | number:'1.2-2' }}</td>
              <td class="num">{{ row.totalCost | number:'1.2-2' }}</td>
              <td class="num">{{ row.marginAmount | number:'1.2-2' }}</td>
              <td class="num" [class.positive]="row.marginPercent >= 0" [class.negative]="row.marginPercent < 0">
                {{ row.marginPercent | number:'1.1-1' }}%
              </td>
              <td class="num">{{ row.estimationCount }}</td>
            </tr>
          } @empty {
            <tr>
              <td colspan="6" class="empty-state">No region profitability data available</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: [`
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table th.sortable { cursor: pointer; user-select: none; }
    .table th.sortable:hover { color: #3b82f6; }
    .sort-icon { font-size: 0.625rem; margin-left: 0.25rem; }
    .table th.num, .table td.num { text-align: right; }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .positive { color: #16a34a; font-weight: 600; }
    .negative { color: #dc2626; font-weight: 600; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
  `],
})
export class RegionProfitabilityComponent {
  @Input() data: ProfitabilityByEntity[] = [];

  sortColumn = signal<SortColumn>('marginPercent');
  sortDirection = signal<SortDirection>('desc');

  sortedData = computed(() => {
    const items = [...this.data];
    const col = this.sortColumn();
    const dir = this.sortDirection();
    return items.sort((a, b) => {
      const valA = this.getSortValue(a, col);
      const valB = this.getSortValue(b, col);
      const cmp = typeof valA === 'string'
        ? valA.localeCompare(valB as string)
        : (valA as number) - (valB as number);
      return dir === 'asc' ? cmp : -cmp;
    });
  });

  onSort(column: SortColumn): void {
    if (this.sortColumn() === column) {
      this.sortDirection.update((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      this.sortColumn.set(column);
      this.sortDirection.set(column === 'entityName' ? 'asc' : 'desc');
    }
  }

  getSortIcon(column: SortColumn): string {
    if (this.sortColumn() !== column) return '\u2195';
    return this.sortDirection() === 'asc' ? '\u2191' : '\u2193';
  }

  private getSortValue(row: ProfitabilityByEntity, col: SortColumn): string | number {
    switch (col) {
      case 'entityName':
        return row.entityName.toLowerCase();
      case 'totalRevenue':
        return row.totalRevenue;
      case 'totalCost':
        return row.totalCost;
      case 'marginAmount':
        return row.marginAmount;
      case 'marginPercent':
        return row.marginPercent;
      case 'estimationCount':
        return row.estimationCount;
    }
  }
}
