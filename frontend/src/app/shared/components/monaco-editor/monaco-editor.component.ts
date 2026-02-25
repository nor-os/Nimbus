/**
 * Overview: Reusable Monaco Editor component — standalone code editor with language support.
 * Architecture: Shared UI component for code editing (Section 11.5)
 * Dependencies: @angular/core, monaco-editor
 * Concepts: Monaco integration, Signal inputs, light theme, multi-language support
 */
import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  afterNextRender,
  effect,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';

declare const monaco: any;

@Component({
  selector: 'nimbus-monaco-editor',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="editor-wrapper" [style.height]="height()">
      <div #editorContainer class="editor-container"></div>
      <div *ngIf="loading" class="editor-loading">
        <span>Loading editor...</span>
      </div>
    </div>
  `,
  styles: [`
    .editor-wrapper {
      position: relative;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      overflow: hidden;
      background: #fff;
    }
    .editor-container {
      width: 100%;
      height: 100%;
    }
    .editor-loading {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f9fafb;
      color: #6b7280;
      font-size: 14px;
    }
  `],
})
export class MonacoEditorComponent implements OnInit, OnDestroy {
  /** Programming language (python, json, yaml, shell, typescript) */
  language = input<string>('python');
  /** Editor content */
  value = input<string>('');
  /** Read-only mode */
  readOnly = input<boolean>(false);
  /** Editor height (CSS value) */
  height = input<string>('400px');
  /** Minimap enabled */
  minimap = input<boolean>(false);

  /** Emits when content changes */
  valueChange = output<string>();

  @ViewChild('editorContainer', { static: true })
  editorContainer!: ElementRef<HTMLDivElement>;

  loading = true;
  private editor: any = null;
  private preventEmit = false;

  constructor() {
    // React to input changes
    effect(() => {
      const lang = this.language();
      if (this.editor && lang) {
        const model = this.editor.getModel();
        if (model) {
          monaco.editor.setModelLanguage(model, lang);
        }
      }
    });

    effect(() => {
      const val = this.value();
      if (this.editor && val !== undefined) {
        const current = this.editor.getValue();
        if (val !== current) {
          this.preventEmit = true;
          this.editor.setValue(val);
          this.preventEmit = false;
        }
      }
    });

    effect(() => {
      const ro = this.readOnly();
      if (this.editor) {
        this.editor.updateOptions({ readOnly: ro });
      }
    });
  }

  ngOnInit(): void {
    this.loadMonaco();
  }

  ngOnDestroy(): void {
    if (this.editor) {
      this.editor.dispose();
      this.editor = null;
    }
  }

  private loadMonaco(): void {
    if (typeof monaco !== 'undefined') {
      this.initEditor();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js';
    script.onload = () => {
      (window as any).require.config({
        paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' },
      });
      (window as any).require(['vs/editor/editor.main'], () => {
        this.initEditor();
      });
    };
    document.head.appendChild(script);
  }

  private initEditor(): void {
    this.loading = false;
    this.editor = monaco.editor.create(this.editorContainer.nativeElement, {
      value: this.value() || '',
      language: this.language(),
      theme: 'vs', // Light theme ONLY
      readOnly: this.readOnly(),
      minimap: { enabled: this.minimap() },
      automaticLayout: true,
      fontSize: 13,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      tabSize: 4,
      insertSpaces: true,
      wordWrap: 'on',
      padding: { top: 8, bottom: 8 },
      renderLineHighlight: 'line',
      scrollbar: {
        verticalScrollbarSize: 10,
        horizontalScrollbarSize: 10,
      },
    });

    this.editor.onDidChangeModelContent(() => {
      if (!this.preventEmit) {
        this.valueChange.emit(this.editor.getValue());
      }
    });
  }

  /** Programmatically focus the editor */
  focus(): void {
    this.editor?.focus();
  }

  /** Format the document */
  format(): void {
    this.editor?.getAction('editor.action.formatDocument')?.run();
  }
}
