/**
 * Overview: Monaco Editor wrapper — standalone Angular component for code editing with syntax highlighting.
 * Architecture: Shared component for code editing (Section 11)
 * Dependencies: @angular/core, monaco-editor (CDN)
 * Concepts: Wraps the Monaco Editor with Angular signals, supports TypeScript and Python,
 *   light theme, configurable height, two-way code binding via input/output.
 */
import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  AfterViewInit,
  Output,
  SimpleChanges,
  ViewChild,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  inject,
  NgZone,
} from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'nimbus-monaco-editor',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="editor-container" [style.height]="height">
      <div #editorHost class="editor-host"></div>
      @if (!editorReady) {
        <div class="editor-loading">Loading editor...</div>
      }
    </div>
  `,
  styles: [`
    .editor-container {
      position: relative;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      overflow: hidden;
      background: #fff;
    }
    .editor-host {
      width: 100%;
      height: 100%;
    }
    .editor-loading {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #64748b;
      font-size: 0.875rem;
      background: #f8fafc;
    }
  `],
})
export class MonacoEditorComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() code = '';
  @Input() language: 'typescript' | 'python' | 'json' | 'shell' = 'typescript';
  @Input() readOnly = false;
  @Input() height = '400px';
  @Output() codeChange = new EventEmitter<string>();

  @ViewChild('editorHost', { static: true }) editorHost!: ElementRef<HTMLDivElement>;

  editorReady = false;
  private editor: any = null;
  private ignoreChange = false;
  private cdr = inject(ChangeDetectorRef);
  private ngZone = inject(NgZone);

  ngAfterViewInit(): void {
    this.initEditor();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.editor) return;

    if (changes['code'] && !this.ignoreChange) {
      const current = this.editor.getValue();
      if (current !== this.code) {
        this.ignoreChange = true;
        this.editor.setValue(this.code);
        this.ignoreChange = false;
      }
    }
    if (changes['language']) {
      const m = (window as any).monaco;
      if (m) {
        const model = this.editor.getModel();
        if (model) {
          m.editor.setModelLanguage(model, this.language);
        }
      }
    }
    if (changes['readOnly']) {
      this.editor.updateOptions({ readOnly: this.readOnly });
    }
  }

  ngOnDestroy(): void {
    if (this.editor) {
      this.editor.dispose();
      this.editor = null;
    }
  }

  private async initEditor(): Promise<void> {
    try {
      const m = await this.ensureMonacoLoaded();

      this.ngZone.runOutsideAngular(() => {
        this.editor = m.editor.create(this.editorHost.nativeElement, {
          value: this.code,
          language: this.language,
          readOnly: this.readOnly,
          theme: 'vs',
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          renderWhitespace: 'selection',
          padding: { top: 8 },
        });

        this.editor.onDidChangeModelContent(() => {
          if (this.ignoreChange) return;
          const value = this.editor.getValue();
          this.ignoreChange = true;
          this.ngZone.run(() => this.codeChange.emit(value));
          this.ignoreChange = false;
        });
      });

      this.editorReady = true;
      this.cdr.markForCheck();
    } catch (err) {
      console.error('Failed to initialize Monaco editor:', err);
    }
  }

  private ensureMonacoLoaded(): Promise<any> {
    const w = window as any;

    // Already loaded
    if (w.monaco?.editor) {
      return Promise.resolve(w.monaco);
    }

    return new Promise<any>((resolve, reject) => {
      // If the loader script is already in the DOM, wait for monaco to appear
      if (document.getElementById('monaco-loader-script')) {
        const check = setInterval(() => {
          if (w.monaco?.editor) {
            clearInterval(check);
            resolve(w.monaco);
          }
        }, 100);
        // Timeout after 15s
        setTimeout(() => { clearInterval(check); reject(new Error('Monaco load timeout')); }, 15000);
        return;
      }

      // Save any existing AMD require before Monaco's loader overwrites it
      const existingRequire = w.require;

      const loaderScript = document.createElement('script');
      loaderScript.id = 'monaco-loader-script';
      loaderScript.src = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js';
      loaderScript.onload = () => {
        // Monaco's loader.js sets window.require to its AMD require
        const amdRequire = w.require;
        // Restore original require if it existed (e.g. webpack)
        if (existingRequire) {
          w.require = existingRequire;
        }

        amdRequire.config({
          paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' },
        });
        amdRequire(['vs/editor/editor.main'], () => {
          resolve(w.monaco);
        });
      };
      loaderScript.onerror = () => reject(new Error('Failed to load Monaco loader script'));
      document.head.appendChild(loaderScript);
    });
  }
}
