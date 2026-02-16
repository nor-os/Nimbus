/**
 * Overview: CIDR notation input with inline validation and computed network info (network address, broadcast, host count, private/public).
 * Architecture: Shared reusable form component (Section 3)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: CIDR notation, IPv4 subnet math, inline validation, computed network properties
 */
import { Component, ChangeDetectionStrategy, Input, Output, EventEmitter, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface CidrInfo {
  network: string;
  broadcast: string;
  hostCount: number;
  isPrivate: boolean;
  prefix: number;
  subnetMask: string;
}

@Component({
  selector: 'nimbus-cidr-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="cidr-input-wrapper">
      <input
        type="text"
        class="cidr-input"
        [class.invalid]="internalValue() && !isValid()"
        [ngModel]="internalValue()"
        (ngModelChange)="onInput($event)"
        placeholder="e.g. 10.0.0.0/16"
      />
      @if (internalValue() && !isValid()) {
        <div class="error-text">Invalid CIDR notation. Expected format: x.x.x.x/n</div>
      }
      @if (info()) {
        <div class="info-panel">
          <div class="info-row">
            <span class="info-label">Network</span>
            <span class="info-value">{{ info()!.network }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Broadcast</span>
            <span class="info-value">{{ info()!.broadcast }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Subnet Mask</span>
            <span class="info-value">{{ info()!.subnetMask }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Usable Hosts</span>
            <span class="info-value">{{ info()!.hostCount | number }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Scope</span>
            <span class="info-value" [class.private]="info()!.isPrivate" [class.public]="!info()!.isPrivate">
              {{ info()!.isPrivate ? 'Private (RFC 1918)' : 'Public' }}
            </span>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .cidr-input-wrapper {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .cidr-input {
      padding: 7px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 13px;
      font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
      background: #fff;
      color: #1e293b;
      outline: none;
      transition: border-color 0.15s;
    }

    .cidr-input:focus {
      border-color: #3b82f6;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }

    .cidr-input.invalid {
      border-color: #ef4444;
      box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.1);
    }

    .error-text {
      font-size: 12px;
      color: #ef4444;
    }

    .info-panel {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .info-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .info-label {
      font-size: 12px;
      color: #64748b;
      font-weight: 500;
    }

    .info-value {
      font-size: 12px;
      color: #1e293b;
      font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
      font-weight: 500;
    }

    .info-value.private {
      color: #16a34a;
    }

    .info-value.public {
      color: #ea580c;
    }
  `]
})
export class CidrInputComponent {
  @Input() set value(v: string) {
    this.internalValue.set(v || '');
  }
  @Output() valueChange = new EventEmitter<string>();

  internalValue = signal('');

  private static readonly CIDR_REGEX = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}$/;

  info = computed<CidrInfo | null>(() => {
    const val = this.internalValue();
    if (!val || !this.isValid()) return null;
    return this.computeCidr(val);
  });

  isValid(): boolean {
    const val = this.internalValue();
    if (!val) return false;
    if (!CidrInputComponent.CIDR_REGEX.test(val)) return false;
    const [ipStr, prefixStr] = val.split('/');
    const prefix = parseInt(prefixStr, 10);
    if (prefix < 0 || prefix > 32) return false;
    const octets = ipStr.split('.').map(o => parseInt(o, 10));
    return octets.every(o => o >= 0 && o <= 255);
  }

  onInput(val: string): void {
    this.internalValue.set(val);
    this.valueChange.emit(val);
  }

  private computeCidr(cidr: string): CidrInfo {
    const [ipStr, prefixStr] = cidr.split('/');
    const prefix = parseInt(prefixStr, 10);
    const octets = ipStr.split('.').map(o => parseInt(o, 10));

    const ipNum = ((octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]) >>> 0;
    const mask = prefix === 0 ? 0 : (~0 << (32 - prefix)) >>> 0;
    const networkNum = (ipNum & mask) >>> 0;
    const broadcastNum = (networkNum | (~mask >>> 0)) >>> 0;

    const totalHosts = Math.pow(2, 32 - prefix);
    const hostCount = prefix >= 31 ? totalHosts : Math.max(0, totalHosts - 2);

    const firstOctet = octets[0];
    const secondOctet = octets[1];
    const isPrivate =
      firstOctet === 10 ||
      (firstOctet === 172 && secondOctet >= 16 && secondOctet <= 31) ||
      (firstOctet === 192 && secondOctet === 168);

    return {
      network: this.numToIp(networkNum),
      broadcast: this.numToIp(broadcastNum),
      hostCount,
      isPrivate,
      prefix,
      subnetMask: this.numToIp(mask),
    };
  }

  private numToIp(num: number): string {
    return [
      (num >>> 24) & 0xff,
      (num >>> 16) & 0xff,
      (num >>> 8) & 0xff,
      num & 0xff,
    ].join('.');
  }
}
