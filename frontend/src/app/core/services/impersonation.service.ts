/**
 * Overview: Impersonation service managing session state, countdown, and API calls.
 * Architecture: Core service for impersonation lifecycle (Section 3.2)
 * Dependencies: @angular/core, app/core/services/api.service
 * Concepts: Impersonation, signals-based state, countdown timer
 */
import { Injectable, inject, signal, computed, OnDestroy } from '@angular/core';
import { Observable, tap, catchError, of } from 'rxjs';
import { ApiService } from './api.service';
import {
  ImpersonationSession,
  ImpersonationSessionList,
  ImpersonationConfig,
  ImpersonationRequest,
  ImpersonationApproval,
  ImpersonationStatusInfo,
} from '../models/impersonation.model';

const BASE = '/api/v1/impersonation';

@Injectable({ providedIn: 'root' })
export class ImpersonationService implements OnDestroy {
  private api = inject(ApiService);

  private currentImpersonationSignal = signal<ImpersonationStatusInfo | null>(null);
  private countdownInterval: ReturnType<typeof setInterval> | null = null;
  private remainingSecondsSignal = signal(0);

  readonly currentImpersonation = this.currentImpersonationSignal.asReadonly();
  readonly isImpersonating = computed(() => this.currentImpersonationSignal()?.is_impersonating ?? false);
  readonly remainingSeconds = this.remainingSecondsSignal.asReadonly();
  readonly remainingTime = computed(() => {
    const secs = this.remainingSecondsSignal();
    if (secs <= 0) return '00:00';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  });

  ngOnDestroy(): void {
    this.stopCountdown();
  }

  checkStatus(): Observable<ImpersonationStatusInfo | null> {
    return this.api.get<ImpersonationStatusInfo>(`${BASE}/me`).pipe(
      tap((status) => {
        this.currentImpersonationSignal.set(status);
        if (status.is_impersonating && status.expires_at) {
          this.startCountdown(status.expires_at);
        } else {
          this.stopCountdown();
        }
      }),
      catchError(() => {
        this.clearState();
        return of(null);
      }),
    );
  }

  requestImpersonation(request: ImpersonationRequest): Observable<ImpersonationSession> {
    return this.api.post<ImpersonationSession>(`${BASE}/request`, request);
  }

  approveRequest(sessionId: string, approval: ImpersonationApproval): Observable<ImpersonationSession> {
    return this.api.post<ImpersonationSession>(`${BASE}/${sessionId}/approve`, approval);
  }

  endSession(sessionId: string): Observable<void> {
    return this.api.post<void>(`${BASE}/${sessionId}/end`, {}).pipe(
      tap(() => {
        this.currentImpersonationSignal.set(null);
        this.stopCountdown();
      }),
    );
  }

  extendSession(sessionId: string, minutes: number): Observable<ImpersonationSession> {
    return this.api.post<ImpersonationSession>(`${BASE}/${sessionId}/extend`, { minutes });
  }

  getActiveSessions(offset = 0, limit = 50): Observable<ImpersonationSessionList> {
    return this.api.get<ImpersonationSessionList>(`${BASE}/sessions?offset=${offset}&limit=${limit}`);
  }

  getSession(sessionId: string): Observable<ImpersonationSession> {
    return this.api.get<ImpersonationSession>(`${BASE}/sessions/${sessionId}`);
  }

  getConfig(): Observable<ImpersonationConfig> {
    return this.api.get<ImpersonationConfig>(`${BASE}/config`);
  }

  updateConfig(config: Partial<ImpersonationConfig>): Observable<ImpersonationConfig> {
    return this.api.put<ImpersonationConfig>(`${BASE}/config`, config);
  }

  clearState(): void {
    this.currentImpersonationSignal.set(null);
    this.stopCountdown();
  }

  private startCountdown(expiresAt: string): void {
    this.stopCountdown();
    const update = () => {
      const remaining = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
      this.remainingSecondsSignal.set(remaining);
      if (remaining <= 0) {
        this.stopCountdown();
      }
    };
    update();
    this.countdownInterval = setInterval(update, 1000);
  }

  private stopCountdown(): void {
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }
    this.remainingSecondsSignal.set(0);
  }
}
