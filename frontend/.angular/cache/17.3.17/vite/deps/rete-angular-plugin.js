import {
  classicConnectionPath,
  createCustomElement,
  getDOMSocketPosition,
  loopConnectionPath
} from "./chunk-42U4ZGAU.js";
import "./chunk-MTISOBFE.js";
import {
  BaseAreaPlugin
} from "./chunk-FDF2NVCL.js";
import {
  Scope,
  classic,
  getUID
} from "./chunk-PXWGCFSP.js";
import {
  CommonModule
} from "./chunk-AMTCE6GS.js";
import {
  ChangeDetectorRef,
  Component,
  ComponentFactoryResolver$1,
  Directive,
  ElementRef,
  EventEmitter,
  HostBinding,
  HostListener,
  Input,
  NgModule,
  Output,
  Pipe,
  ViewContainerRef
} from "./chunk-QO3ATPKY.js";
import "./chunk-N2Y5LLLL.js";
import "./chunk-S6MU67JM.js";
import {
  __awaiter
} from "./chunk-VHIO24JD.js";
import "./chunk-TXDUYLVM.js";

// node_modules/rete-angular-plugin/fesm2015/rete-angular-plugin.js
var NodeComponent = class {
  constructor(cdr) {
    this.cdr = cdr;
    this.seed = 0;
    this.cdr.detach();
  }
  get width() {
    return this.data.width;
  }
  get height() {
    return this.data.height;
  }
  get selected() {
    return this.data.selected;
  }
  ngOnChanges() {
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
    this.seed++;
  }
  sortByIndex(a, b) {
    var _a, _b;
    const ai = ((_a = a.value) === null || _a === void 0 ? void 0 : _a.index) || 0;
    const bi = ((_b = b.value) === null || _b === void 0 ? void 0 : _b.index) || 0;
    return ai - bi;
  }
};
NodeComponent.decorators = [
  { type: Component, args: [{
    // [component-directive]
    template: `<div class="title" data-testid="title">{{data.label}}</div>
<div class="output" *ngFor="let output of data.outputs | keyvalueimpure: sortByIndex" [attr.data-testid]="'output-'+output.key">
    <div class="output-title" data-testid="output-title">{{output.value?.label}}</div>
    <div
        class="output-socket"
        refComponent
        [data]="{type: 'socket', side: 'output', key: output.key, nodeId: data.id, payload: output.value?.socket, seed: seed }"
        [emit]="emit"
        data-testid="output-socket"
    ></div>
</div>
<div
    class="control"
    *ngFor="let control of data.controls | keyvalueimpure: sortByIndex"
    refComponent
    [data]="{type: 'control', payload: control.value }"
    [emit]="emit"
    [attr.data-testid]="'control-'+control.key"
></div>
<div class="input" *ngFor="let input of data.inputs | keyvalueimpure: sortByIndex" [attr.data-testid]="'input-'+input.key">
    <div
        class="input-socket"
        refComponent
        [data]="{type: 'socket', side: 'input', key: input.key, nodeId: data.id, payload: input.value?.socket, seed: seed }"
        [emit]="emit"
        data-testid="input-socket"
    ></div>
    <div class="input-title" data-testid="input-title" *ngIf="!input.value?.control || !input.value?.showControl">{{input.value?.label}}</div>
    <div
        class="input-control"
        [style.display]="input.value?.control && input.value?.showControl ? '' : 'none'"
        refComponent
        [data]="{type: 'control', payload: input.value?.control }"
        [emit]="emit"
        data-testid="input-control"
    ></div>
</div>
`,
    host: {
      "data-testid": "node"
    },
    styles: [":host{display:block;background:rgba(110,136,255,.8);border:2px solid #4e58bf;border-radius:10px;cursor:pointer;box-sizing:border-box;width:180px;height:auto;padding-bottom:6px;position:relative;-webkit-user-select:none;user-select:none;line-height:initial;font-family:Arial}:host:hover{background:rgba(130,153,255,.8)}:host.selected{background:#ffd92c;border-color:#e3c000}:host .title{color:#fff;font-family:sans-serif;font-size:18px;padding:8px}:host .output{text-align:right}:host .input{text-align:left}:host .input-title,:host .output-title{vertical-align:middle;color:#fff;display:inline-block;font-family:sans-serif;font-size:14px;margin:6px;line-height:24px}:host .input-title[hidden],:host .output-title[hidden]{display:none}:host .output-socket{text-align:right;margin-right:-18px;display:inline-block}:host .input-socket{text-align:left;margin-left:-18px;display:inline-block}:host .input-control{z-index:1;width:calc(100% - 36px);vertical-align:middle;display:inline-block}:host .control{padding:6px 18px}\n"]
  }] }
];
NodeComponent.ctorParameters = () => [
  { type: ChangeDetectorRef }
];
NodeComponent.propDecorators = {
  data: [{ type: Input }],
  emit: [{ type: Input }],
  rendered: [{ type: Input }],
  width: [{ type: HostBinding, args: ["style.width.px"] }],
  height: [{ type: HostBinding, args: ["style.height.px"] }],
  selected: [{ type: HostBinding, args: ["class.selected"] }]
};
var SocketComponent = class {
  constructor(cdr) {
    this.cdr = cdr;
    this.cdr.detach();
  }
  get title() {
    return this.data.name;
  }
  ngOnChanges() {
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
  }
};
SocketComponent.decorators = [
  { type: Component, args: [{
    template: ``,
    styles: [":host{display:inline-block;cursor:pointer;border:1px solid white;border-radius:12px;width:24px;height:24px;margin:6px;vertical-align:middle;background:#96b38a;z-index:2;box-sizing:border-box}:host:hover{border-width:4px}:host.multiple{border-color:#ff0}:host.output{margin-right:-12px}:host.input{margin-left:-12px}\n"]
  }] }
];
SocketComponent.ctorParameters = () => [
  { type: ChangeDetectorRef }
];
SocketComponent.propDecorators = {
  data: [{ type: Input }],
  rendered: [{ type: Input }],
  title: [{ type: HostBinding, args: ["title"] }]
};
var ControlComponent = class {
  constructor(cdr) {
    this.cdr = cdr;
    this.cdr.detach();
  }
  pointerdown(event) {
    event.stopPropagation();
  }
  ngOnChanges(changes) {
    const seed = changes["seed"];
    const data = changes["data"];
    if (seed && seed.currentValue !== seed.previousValue || data && data.currentValue !== data.previousValue) {
      this.cdr.detectChanges();
    }
    requestAnimationFrame(() => this.rendered());
  }
  onChange(e) {
    const target = e.target;
    const value = this.data.type === "number" ? +target.value : target.value;
    this.data.setValue(value);
    this.cdr.detectChanges();
  }
};
ControlComponent.decorators = [
  { type: Component, args: [{
    template: '<input\n  [value]="data.value"\n  [readonly]="data.readonly"\n  [type]="data.type"\n  (input)="onChange($event)"\n/>\n',
    styles: ["input{width:100%;border-radius:30px;background-color:#fff;padding:2px 6px;border:1px solid #999;font-size:110%;box-sizing:border-box}\n"]
  }] }
];
ControlComponent.ctorParameters = () => [
  { type: ChangeDetectorRef }
];
ControlComponent.propDecorators = {
  data: [{ type: Input }],
  rendered: [{ type: Input }],
  pointerdown: [{ type: HostListener, args: ["pointerdown", ["$event"]] }]
};
var ConnectionComponent = class {
};
ConnectionComponent.decorators = [
  { type: Component, args: [{
    selector: "connection",
    template: '<svg data-testid="connection">\n    <path [attr.d]="path" />\n</svg>\n',
    styles: ["svg{overflow:visible!important;position:absolute;pointer-events:none;width:9999px;height:9999px}svg path{fill:none;stroke-width:5px;stroke:#4682b4;pointer-events:auto}\n"]
  }] }
];
ConnectionComponent.propDecorators = {
  data: [{ type: Input }],
  start: [{ type: Input }],
  end: [{ type: Input }],
  path: [{ type: Input }]
};
var ConnectionWrapperComponent = class {
  constructor(cdr, viewContainerRef, componentFactoryResolver) {
    this.cdr = cdr;
    this.viewContainerRef = viewContainerRef;
    this.componentFactoryResolver = componentFactoryResolver;
    this.startOb = null;
    this.endOb = null;
    this.cdr.detach();
  }
  get _start() {
    return "x" in this.start ? this.start : this.startOb;
  }
  get _end() {
    return "x" in this.end ? this.end : this.endOb;
  }
  ngOnChanges() {
    return __awaiter(this, void 0, void 0, function* () {
      yield this.updatePath();
      requestAnimationFrame(() => this.rendered());
      this.cdr.detectChanges();
      this.update();
    });
  }
  updatePath() {
    return __awaiter(this, void 0, void 0, function* () {
      if (this._start && this._end) {
        this._path = yield this.path(this._start, this._end);
      }
    });
  }
  ngOnInit() {
    if (typeof this.start === "function") {
      this.start((value) => __awaiter(this, void 0, void 0, function* () {
        this.startOb = value;
        yield this.updatePath();
        this.cdr.detectChanges();
        this.update();
      }));
    }
    if (typeof this.end === "function") {
      this.end((value) => __awaiter(this, void 0, void 0, function* () {
        this.endOb = value;
        yield this.updatePath();
        this.cdr.detectChanges();
        this.update();
      }));
    }
    const componentFactory = this.componentFactoryResolver.resolveComponentFactory(this.connectionComponent);
    this.viewContainerRef.clear();
    this.ref = this.viewContainerRef.createComponent(componentFactory);
    this.update();
  }
  update() {
    this.ref.instance.data = this.data;
    this.ref.instance.start = this._start;
    this.ref.instance.end = this._end;
    this.ref.instance.path = this._path;
    this.ref.changeDetectorRef.markForCheck();
  }
};
ConnectionWrapperComponent.decorators = [
  { type: Component, args: [{
    template: ""
  }] }
];
ConnectionWrapperComponent.ctorParameters = () => [
  { type: ChangeDetectorRef },
  { type: ViewContainerRef },
  { type: ComponentFactoryResolver$1 }
];
ConnectionWrapperComponent.propDecorators = {
  data: [{ type: Input }],
  start: [{ type: Input }],
  end: [{ type: Input }],
  path: [{ type: Input }],
  rendered: [{ type: Input }],
  connectionComponent: [{ type: Input }]
};
function setup$3(props) {
  const positionWatcher = typeof (props === null || props === void 0 ? void 0 : props.socketPositionWatcher) === "undefined" ? getDOMSocketPosition() : props === null || props === void 0 ? void 0 : props.socketPositionWatcher;
  const { node, connection, socket, control } = (props === null || props === void 0 ? void 0 : props.customize) || {};
  return {
    attach(plugin) {
      positionWatcher.attach(plugin);
    },
    update(context) {
      const data = context.data.payload;
      if (context.data.type === "connection") {
        const { start, end } = context.data;
        return Object.assign(Object.assign({ data }, start ? { start } : {}), end ? { end } : {});
      }
      return { data };
    },
    mount(context, plugin) {
      const parent = plugin.parentScope();
      const emit = parent.emit.bind(parent);
      const rendered = () => {
        emit({ type: "rendered", data: context.data });
      };
      if (context.data.type === "node") {
        const component = node ? node(context.data) : NodeComponent;
        return {
          key: `node-${context.data.payload.id}`,
          component,
          props: {
            data: context.data.payload,
            emit,
            rendered
          }
        };
      }
      if (context.data.type === "connection") {
        const component = connection ? connection(context.data) : ConnectionComponent;
        const id = context.data.payload.id;
        const { sourceOutput, targetInput, source, target } = context.data.payload;
        const { start, end, payload } = context.data;
        return {
          key: `connection-${id}`,
          component: ConnectionWrapperComponent,
          props: {
            connectionComponent: component,
            data: payload,
            start: start || ((change) => positionWatcher.listen(source, "output", sourceOutput, change)),
            end: end || ((change) => positionWatcher.listen(target, "input", targetInput, change)),
            path: (start2, end2) => __awaiter(this, void 0, void 0, function* () {
              const response = yield plugin.emit({ type: "connectionpath", data: { payload, points: [start2, end2] } });
              if (!response)
                return "";
              const { path, points } = response.data;
              const curvature = 0.3;
              if (!path && points.length !== 2)
                throw new Error("cannot render connection with a custom number of points");
              if (!path)
                return payload.isLoop ? loopConnectionPath(points, curvature, 120) : classicConnectionPath(points, curvature);
              return path;
            }),
            rendered
          }
        };
      }
      if (context.data.type === "socket") {
        const component = socket ? socket(context.data) : SocketComponent;
        return {
          key: `socket-${getUID()}`,
          component,
          props: {
            data: context.data.payload,
            rendered
          }
        };
      }
      if (context.data.type === "control") {
        const component = control ? control(context.data) : context.data.payload instanceof classic.InputControl ? ControlComponent : null;
        if (component) {
          return {
            key: `control-${context.data.payload.id}`,
            component,
            props: {
              data: context.data.payload,
              rendered
            }
          };
        }
        return;
      }
      return;
    }
  };
}
var index$4 = Object.freeze({
  __proto__: null,
  setup: setup$3
});
function debounce(cb) {
  return {
    timeout: null,
    cancel() {
      if (this.timeout) {
        window.clearTimeout(this.timeout);
        this.timeout = null;
      }
    },
    call(delay) {
      this.timeout = window.setTimeout(() => {
        cb();
      }, delay);
    }
  };
}
var ContextMenuComponent = class {
  constructor(cdr) {
    this.cdr = cdr;
    this.filter = "";
    this.hide = debounce(() => {
      this.onHide();
      this.cdr.detectChanges();
    });
    this.customAttribute = "";
    this.cdr.detach();
  }
  pointerover() {
    this.hide.cancel();
    this.cdr.detectChanges();
  }
  pointerleave() {
    this.hide.call(this.delay);
    this.cdr.detectChanges();
  }
  ngOnChanges() {
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
  }
  setFilter(value) {
    this.filter = value;
    this.cdr.detectChanges();
  }
  getItems() {
    const filterRegexp = new RegExp(this.filter, "i");
    const filteredList = this.items.filter((item) => item.label.match(filterRegexp));
    return filteredList;
  }
  ngOnDestroy() {
    if (this.hide)
      this.hide.cancel();
  }
};
ContextMenuComponent.decorators = [
  { type: Component, args: [{
    // [component-directive]
    template: '<div class="block" *ngIf="searchBar">\n  <context-menu-search [value]="filter" (update)="setFilter($event)"></context-menu-search>\n</div>\n\n<context-menu-item *ngFor="let item of getItems()" [delay]="delay" (select)="item.handler()" [subitems]="item.subitems"\n  (hide)="onHide()">\n  {{ item.label }}\n</context-menu-item>\n',
    host: {
      "data-testid": "context-menu"
    },
    styles: [":host{display:block;padding:10px;width:120px;margin-top:-20px;margin-left:-60px}\n", ".block{display:block;color:#fff;padding:4px;border-bottom:1px solid rgba(69,103,255,.8);background-color:#6e88ffcc;cursor:pointer;width:100%;position:relative}.block:first-child{border-top-left-radius:5px;border-top-right-radius:5px}.block:last-child{border-bottom-left-radius:5px;border-bottom-right-radius:5px}.block:hover{background-color:#8299ffcc}\n"]
  }] }
];
ContextMenuComponent.ctorParameters = () => [
  { type: ChangeDetectorRef }
];
ContextMenuComponent.propDecorators = {
  items: [{ type: Input }],
  delay: [{ type: Input }],
  searchBar: [{ type: Input }],
  onHide: [{ type: Input }],
  rendered: [{ type: Input }],
  customAttribute: [{ type: HostBinding, args: ["attr.rete-context-menu"] }],
  pointerover: [{ type: HostListener, args: ["mouseover"] }],
  pointerleave: [{ type: HostListener, args: ["mouseleave"] }]
};
function setup$2(props) {
  const delay = typeof (props === null || props === void 0 ? void 0 : props.delay) === "undefined" ? 1e3 : props.delay;
  return {
    update(context) {
      if (context.data.type === "contextmenu") {
        return {
          items: context.data.items,
          delay,
          searchBar: context.data.searchBar,
          onHide: context.data.onHide
        };
      }
    },
    mount(context, plugin) {
      const parent = plugin.parentScope();
      const emit = parent.emit.bind(parent);
      const rendered = () => {
        emit({ type: "rendered", data: context.data });
      };
      if (context.data.type === "contextmenu") {
        return {
          key: "context-menu",
          component: ContextMenuComponent,
          props: {
            items: context.data.items,
            delay,
            searchBar: context.data.searchBar,
            onHide: context.data.onHide,
            rendered
          }
        };
      }
      return null;
    }
  };
}
var index$3 = Object.freeze({
  __proto__: null,
  setup: setup$2
});
var MinimapComponent = class {
  constructor(el, cdr) {
    this.el = el;
    this.cdr = cdr;
    this.cdr.detach();
  }
  get width() {
    return this.px(this.size * this.ratio);
  }
  get height() {
    return this.px(this.size);
  }
  pointerdown(event) {
    event.stopPropagation();
    event.preventDefault();
  }
  dblclick(event) {
    event.stopPropagation();
    event.preventDefault();
    if (!this.el.nativeElement)
      return;
    const box = this.el.nativeElement.getBoundingClientRect();
    const x = (event.clientX - box.left) / (this.size * this.ratio);
    const y = (event.clientY - box.top) / (this.size * this.ratio);
    this.point(x, y);
  }
  ngOnChanges() {
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
  }
  px(value) {
    return `${value}px`;
  }
  scale(value) {
    if (!this.el.nativeElement)
      return 0;
    return value * this.el.nativeElement.clientWidth;
  }
  identifyMiniNode(_, item) {
    return [item.top, item.left].join("_");
  }
};
MinimapComponent.decorators = [
  { type: Component, args: [{
    // [component-directive]
    template: '<minimap-mini-node *ngFor="let node of nodes; trackBy: identifyMiniNode" [left]="scale(node.left)"\n  [top]="scale(node.top)" [width]="scale(node.width)" [height]="scale(node.height)">\n\n</minimap-mini-node>\n<minimap-mini-viewport [left]="viewport.left" [top]="viewport.top" [width]="viewport.width" [height]="viewport.height"\n  [containerWidth]="el.nativeElement?.clientWidth" [translate]="translate"></minimap-mini-viewport>\n',
    host: {
      "data-testid": "minimap"
    },
    styles: [":host{position:absolute;right:24px;bottom:24px;background:rgba(229,234,239,.65);padding:20px;overflow:hidden;border:1px solid #b1b7ff;border-radius:8px;box-sizing:border-box}\n"]
  }] }
];
MinimapComponent.ctorParameters = () => [
  { type: ElementRef },
  { type: ChangeDetectorRef }
];
MinimapComponent.propDecorators = {
  rendered: [{ type: Input }],
  size: [{ type: Input }],
  ratio: [{ type: Input }],
  nodes: [{ type: Input }],
  viewport: [{ type: Input }],
  translate: [{ type: Input }],
  point: [{ type: Input }],
  width: [{ type: HostBinding, args: ["style.width"] }],
  height: [{ type: HostBinding, args: ["style.height"] }],
  pointerdown: [{ type: HostListener, args: ["pointerdown", ["$event"]] }],
  dblclick: [{ type: HostListener, args: ["dblclick", ["$event"]] }]
};
function setup$1(props) {
  return {
    update(context) {
      if (context.data.type === "minimap") {
        return {
          nodes: context.data.nodes,
          size: (props === null || props === void 0 ? void 0 : props.size) || 200,
          ratio: context.data.ratio,
          viewport: context.data.viewport,
          translate: context.data.translate,
          point: context.data.point
        };
      }
      return null;
    },
    mount(context, plugin) {
      const parent = plugin.parentScope();
      const emit = parent.emit.bind(parent);
      const rendered = () => {
        emit({ type: "rendered", data: context.data });
      };
      if (context.data.type === "minimap") {
        return {
          key: "rete-minimap",
          component: MinimapComponent,
          props: {
            nodes: context.data.nodes,
            size: (props === null || props === void 0 ? void 0 : props.size) || 200,
            ratio: context.data.ratio,
            viewport: context.data.viewport,
            translate: context.data.translate,
            point: context.data.point,
            rendered
          }
        };
      }
      return null;
    }
  };
}
var index$2 = Object.freeze({
  __proto__: null,
  setup: setup$1
});
var PinsComponent = class {
  constructor(cdr) {
    this.cdr = cdr;
    this.cdr.detach();
  }
  ngOnChanges() {
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
  }
  track(_, item) {
    return item.id;
  }
};
PinsComponent.decorators = [
  { type: Component, args: [{
    // [component-directive]
    template: '<reroute-pin *ngFor="let pin of pins; trackBy: track" [position]="pin.position" [selected]="pin.selected"\n  (menu)="menu && menu(pin.id)" (translate)="translate && translate(pin.id, $event.dx, $event.dy)"\n  (down)="down && down(pin.id)" [getPointer]="getPointer"></reroute-pin>\n'
  }] }
];
PinsComponent.ctorParameters = () => [
  { type: ChangeDetectorRef }
];
PinsComponent.propDecorators = {
  rendered: [{ type: Input }],
  pins: [{ type: Input }],
  down: [{ type: Input }],
  translate: [{ type: Input }],
  menu: [{ type: Input }],
  getPointer: [{ type: Input }]
};
function setup(props) {
  const getProps = () => ({
    menu: (props === null || props === void 0 ? void 0 : props.contextMenu) || (() => null),
    translate: (props === null || props === void 0 ? void 0 : props.translate) || (() => null),
    down: (props === null || props === void 0 ? void 0 : props.pointerdown) || (() => null)
  });
  return {
    update(context) {
      if (context.data.type === "reroute-pins") {
        return Object.assign(Object.assign({}, getProps()), { pins: context.data.data.pins });
      }
      return null;
    },
    mount(context, plugin) {
      const area = plugin.parentScope(BaseAreaPlugin);
      const rendered = () => {
        area.emit({ type: "rendered", data: context.data });
      };
      if (context.data.type === "reroute-pins") {
        return {
          key: "rete-reroute",
          component: PinsComponent,
          props: Object.assign(Object.assign({}, getProps()), { pins: context.data.data.pins, rendered, getPointer: () => area.area.pointer })
        };
      }
      return null;
    }
  };
}
var index$1 = Object.freeze({
  __proto__: null,
  setup
});
var index = Object.freeze({
  __proto__: null,
  classic: index$4,
  contextMenu: index$3,
  minimap: index$2,
  reroute: index$1
});
var RefDirective = class {
  constructor(el) {
    this.el = el;
  }
  ngOnChanges() {
    this.emit({ type: "render", data: Object.assign(Object.assign({}, this.data), { element: this.el.nativeElement }) });
  }
  ngOnDestroy() {
    this.emit({ type: "unmount", data: { element: this.el.nativeElement } });
  }
};
RefDirective.decorators = [
  { type: Directive, args: [{
    selector: "[refComponent]"
  }] }
];
RefDirective.ctorParameters = () => [
  { type: ElementRef }
];
RefDirective.propDecorators = {
  data: [{ type: Input }],
  emit: [{ type: Input }]
};
var ImpureKeyvaluePipe = class {
  transform(value, compareFn) {
    if (!value || typeof value !== "object") {
      return [];
    }
    const result = Object.entries(value).map(([key, val]) => ({ key, value: val }));
    if (compareFn) {
      result.sort(compareFn);
    }
    return result;
  }
};
ImpureKeyvaluePipe.decorators = [
  { type: Pipe, args: [{
    name: "keyvalueimpure",
    pure: false
  }] }
];
var ReteModule = class {
};
ReteModule.decorators = [
  { type: NgModule, args: [{
    declarations: [
      RefDirective,
      NodeComponent,
      ConnectionComponent,
      ConnectionWrapperComponent,
      SocketComponent,
      ControlComponent,
      ImpureKeyvaluePipe
    ],
    imports: [
      CommonModule
    ],
    exports: [
      RefDirective,
      NodeComponent,
      ConnectionComponent,
      ConnectionWrapperComponent,
      SocketComponent,
      ControlComponent,
      ImpureKeyvaluePipe
    ],
    entryComponents: [
      NodeComponent,
      ConnectionComponent,
      ConnectionWrapperComponent,
      SocketComponent,
      ControlComponent
    ]
  }] }
];
var ContextMenuSearchComponent = class {
  constructor() {
    this.update = new EventEmitter();
  }
};
ContextMenuSearchComponent.decorators = [
  { type: Component, args: [{
    selector: "context-menu-search",
    template: `<input class="search" [value]="value" (input)="update.emit($any($event.target)?.value || '')"
  data-testid="context-menu-search-input" />
`,
    styles: [".search{color:#fff;padding:1px 8px;border:1px solid white;border-radius:10px;font-size:16px;font-family:serif;width:100%;box-sizing:border-box;background:transparent}\n"]
  }] }
];
ContextMenuSearchComponent.propDecorators = {
  value: [{ type: Input }],
  update: [{ type: Output }]
};
var ContextMenuItemComponent = class {
  constructor(cdr) {
    this.cdr = cdr;
    this.select = new EventEmitter();
    this.hide = new EventEmitter();
    this.hideSubitems = debounce(() => {
      this.visibleSubitems = false;
      this.cdr.detectChanges();
    });
    this.visibleSubitems = false;
    this.cdr.detach();
  }
  get block() {
    return true;
  }
  get hasSubitems() {
    return this.subitems;
  }
  click(event) {
    event.stopPropagation();
    this.select.emit();
    this.hide.emit();
  }
  pointerdown(event) {
    event.stopPropagation();
  }
  wheel(event) {
    event.stopPropagation();
  }
  pointerover() {
    this.hideSubitems.cancel();
    this.visibleSubitems = true;
    this.cdr.detectChanges();
  }
  pointerleave() {
    this.hideSubitems.call(this.delay);
    this.cdr.detectChanges();
  }
};
ContextMenuItemComponent.decorators = [
  { type: Component, args: [{
    // [component-directive]
    selector: "context-menu-item",
    template: '<ng-content></ng-content>\n<div class="subitems" *ngIf="subitems && visibleSubitems">\n  <context-menu-item *ngFor="let item of subitems" [delay]="delay" (select)="item.handler()" (hide)="hide.emit()">\n    {{ item.label }}\n  </context-menu-item>\n</div>\n',
    host: {
      "data-testid": "context-menu-item"
    },
    styles: ['@charset "UTF-8";:host(.hasSubitems):after{content:"\\25ba";position:absolute;opacity:.6;right:5px;top:5px;font-family:initial}.subitems{position:absolute;top:0;left:100%;width:120px}\n', ".block{display:block;color:#fff;padding:4px;border-bottom:1px solid rgba(69,103,255,.8);background-color:#6e88ffcc;cursor:pointer;width:100%;position:relative}.block:first-child{border-top-left-radius:5px;border-top-right-radius:5px}.block:last-child{border-bottom-left-radius:5px;border-bottom-right-radius:5px}.block:hover{background-color:#8299ffcc}\n"]
  }] }
];
ContextMenuItemComponent.ctorParameters = () => [
  { type: ChangeDetectorRef }
];
ContextMenuItemComponent.propDecorators = {
  subitems: [{ type: Input }],
  delay: [{ type: Input }],
  select: [{ type: Output }],
  hide: [{ type: Output }],
  block: [{ type: HostBinding, args: ["class.block"] }],
  hasSubitems: [{ type: HostBinding, args: ["class.hasSubitems"] }],
  click: [{ type: HostListener, args: ["click", ["$event"]] }],
  pointerdown: [{ type: HostListener, args: ["pointerdown", ["$event"]] }],
  wheel: [{ type: HostListener, args: ["wheel", ["$event"]] }],
  pointerover: [{ type: HostListener, args: ["pointerover"] }],
  pointerleave: [{ type: HostListener, args: ["pointerleave"] }]
};
var ReteContextMenuModule = class {
};
ReteContextMenuModule.decorators = [
  { type: NgModule, args: [{
    declarations: [
      ContextMenuComponent,
      ContextMenuSearchComponent,
      ContextMenuItemComponent
    ],
    imports: [
      CommonModule
    ],
    exports: [
      ContextMenuComponent,
      ContextMenuSearchComponent,
      ContextMenuItemComponent
    ],
    entryComponents: [
      ContextMenuComponent
    ]
  }] }
];
function useDrag(translate, getPointer) {
  return {
    start(e) {
      let previous = Object.assign({}, getPointer(e));
      function move(moveEvent) {
        const current = Object.assign({}, getPointer(moveEvent));
        const dx = current.x - previous.x;
        const dy = current.y - previous.y;
        previous = current;
        translate(dx, dy);
      }
      function up() {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        window.removeEventListener("pointercancel", up);
      }
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
      window.addEventListener("pointercancel", up);
    }
  };
}
var MiniViewportComponent = class {
  constructor() {
    this.drag = useDrag((dx, dy) => this.onDrag(dx, dy), (e) => ({ x: e.pageX, y: e.pageY }));
  }
  get styleLeft() {
    return this.px(this.scale(this.left));
  }
  get styleTop() {
    return this.px(this.scale(this.top));
  }
  get styleWidth() {
    return this.px(this.scale(this.width));
  }
  get styleHeight() {
    return this.px(this.scale(this.height));
  }
  pointerdown(event) {
    event.stopPropagation();
    this.drag.start(event);
  }
  px(value) {
    return `${value}px`;
  }
  scale(v) {
    return v * this.containerWidth;
  }
  invert(v) {
    return v / this.containerWidth;
  }
  onDrag(dx, dy) {
    this.translate(this.invert(-dx), this.invert(-dy));
  }
};
MiniViewportComponent.decorators = [
  { type: Component, args: [{
    selector: "minimap-mini-viewport",
    template: "",
    host: {
      "data-testid": "minimap-viewport"
    },
    styles: [":host{display:block;position:absolute;background:rgba(255,251,128,.32);border:1px solid #ffe52b}\n"]
  }] }
];
MiniViewportComponent.propDecorators = {
  left: [{ type: Input }],
  top: [{ type: Input }],
  width: [{ type: Input }],
  height: [{ type: Input }],
  containerWidth: [{ type: Input }],
  translate: [{ type: Input }],
  styleLeft: [{ type: HostBinding, args: ["style.left"] }],
  styleTop: [{ type: HostBinding, args: ["style.top"] }],
  styleWidth: [{ type: HostBinding, args: ["style.width"] }],
  styleHeight: [{ type: HostBinding, args: ["style.height"] }],
  pointerdown: [{ type: HostListener, args: ["pointerdown", ["$event"]] }]
};
var MiniNodeComponent = class {
  get styleLeft() {
    return this.px(this.left);
  }
  get styleTop() {
    return this.px(this.top);
  }
  get styleWidth() {
    return this.px(this.width);
  }
  get styleHeight() {
    return this.px(this.height);
  }
  px(value) {
    return `${value}px`;
  }
};
MiniNodeComponent.decorators = [
  { type: Component, args: [{
    selector: "minimap-mini-node",
    template: "",
    host: {
      "data-testid": "minimap-node"
    },
    styles: [":host{display:block;position:absolute;background:rgba(110,136,255,.8);border:1px solid rgba(192,206,212,.6)}\n"]
  }] }
];
MiniNodeComponent.propDecorators = {
  left: [{ type: Input }],
  top: [{ type: Input }],
  width: [{ type: Input }],
  height: [{ type: Input }],
  styleLeft: [{ type: HostBinding, args: ["style.left"] }],
  styleTop: [{ type: HostBinding, args: ["style.top"] }],
  styleWidth: [{ type: HostBinding, args: ["style.width"] }],
  styleHeight: [{ type: HostBinding, args: ["style.height"] }]
};
var ReteMinimapModule = class {
};
ReteMinimapModule.decorators = [
  { type: NgModule, args: [{
    declarations: [
      MinimapComponent,
      MiniViewportComponent,
      MiniNodeComponent
    ],
    imports: [
      CommonModule
    ],
    exports: [
      MinimapComponent,
      MiniViewportComponent,
      MiniNodeComponent
    ],
    entryComponents: [
      MinimapComponent
    ]
  }] }
];
var pinSize = 20;
var PinComponent = class {
  constructor(cdr) {
    this.cdr = cdr;
    this.menu = new EventEmitter();
    this.translate = new EventEmitter();
    this.down = new EventEmitter();
    this.drag = useDrag((dx, dy) => {
      this.translate.emit({ dx, dy });
    }, () => this.getPointer());
  }
  get _selected() {
    return this.selected;
  }
  get top() {
    return `${this.position.y - pinSize / 2}px`;
  }
  get left() {
    return `${this.position.x - pinSize / 2}px`;
  }
  pointerdown(event) {
    event.stopPropagation();
    event.preventDefault();
    this.drag.start(event);
    this.down.emit();
  }
  contextmenu(event) {
    event.stopPropagation();
    event.preventDefault();
    this.menu.emit();
  }
  ngOnChanges() {
  }
};
PinComponent.decorators = [
  { type: Component, args: [{
    selector: "reroute-pin",
    template: "",
    host: {
      "data-testid": "pin"
    },
    styles: [":host{display:block;width:20px;height:20px;box-sizing:border-box;background:steelblue;border:2px solid white;border-radius:20px;position:absolute}:host.selected{background:#ffd92c}\n"]
  }] }
];
PinComponent.ctorParameters = () => [
  { type: ChangeDetectorRef }
];
PinComponent.propDecorators = {
  position: [{ type: Input }],
  selected: [{ type: Input }],
  getPointer: [{ type: Input }],
  menu: [{ type: Output }],
  translate: [{ type: Output }],
  down: [{ type: Output }],
  _selected: [{ type: HostBinding, args: ["class.selected"] }],
  top: [{ type: HostBinding, args: ["style.top"] }],
  left: [{ type: HostBinding, args: ["style.left"] }],
  pointerdown: [{ type: HostListener, args: ["pointerdown", ["$event"]] }],
  contextmenu: [{ type: HostListener, args: ["contextmenu", ["$event"]] }]
};
var ReteRerouteModule = class {
};
ReteRerouteModule.decorators = [
  { type: NgModule, args: [{
    declarations: [
      PinsComponent,
      PinComponent
    ],
    imports: [
      CommonModule
    ],
    exports: [
      PinsComponent,
      PinComponent
    ],
    entryComponents: [
      PinsComponent
    ]
  }] }
];
function reflect(obj) {
  if (typeof obj !== "object" || obj === null) {
    return obj;
  }
  return new Proxy(obj, {
    get(target, prop) {
      return target[prop];
    },
    set(target, prop, value) {
      target[prop] = value;
      return true;
    },
    has: (target, prop) => prop in target,
    deleteProperty: (target, prop) => delete target[prop],
    ownKeys: (target) => Reflect.ownKeys(target)
  });
}
function getRenderer() {
  const elements = /* @__PURE__ */ new WeakMap();
  return {
    get(element) {
      return elements.get(element);
    },
    mount(element, key, component, injector, props) {
      let CustomElement = customElements.get(key);
      if (!CustomElement) {
        CustomElement = createCustomElement(component, { injector });
        customElements.define(key, CustomElement);
      }
      const ngElement = new CustomElement(injector);
      Object.keys(props).forEach((key2) => {
        ngElement[key2] = props[key2];
      });
      element.appendChild(ngElement);
      elements.set(element, { key, ngElement });
    },
    update({ ngElement }, props) {
      Object.keys(props).forEach((key) => {
        ngElement.ngElementStrategy.setInputValue(key, reflect(props[key]));
      });
    },
    unmount(element) {
      const existing = elements.get(element);
      if (existing) {
        existing.ngElement.remove();
        elements.delete(element);
      }
    }
  };
}
var AngularPlugin = class extends Scope {
  /**
   * @constructor
   * @param params Plugin properties
   * @param params.injector Angular's Injector instance
   */
  constructor(params) {
    super("angular-render");
    this.params = params;
    this.presets = [];
    this.owners = /* @__PURE__ */ new WeakMap();
    this.renderer = getRenderer();
    this.addPipe((context) => {
      if (!context || typeof context !== "object" || !("type" in context))
        return context;
      if (context.type === "unmount") {
        this.unmount(context.data.element);
      } else if (context.type === "render") {
        if ("filled" in context.data && context.data.filled) {
          return context;
        }
        if (this.mount(context.data.element, context)) {
          return Object.assign(Object.assign({}, context), { data: Object.assign(Object.assign({}, context.data), { filled: true }) });
        }
      }
      return context;
    });
  }
  setParent(scope) {
    super.setParent(scope);
    this.presets.forEach((preset) => {
      if (preset.attach)
        preset.attach(this);
    });
  }
  unmount(element) {
    this.owners.delete(element);
    this.renderer.unmount(element);
  }
  mount(element, context) {
    const existing = this.renderer.get(element);
    if (existing) {
      this.presets.forEach((preset) => {
        if (this.owners.get(element) !== preset)
          return;
        const result = preset.update(context, this);
        if (result) {
          this.renderer.update(existing, result);
        }
      });
      return true;
    }
    for (const preset of this.presets) {
      const result = preset.mount(context, this);
      if (!result)
        continue;
      const { key, component, props } = result;
      this.renderer.mount(element, key, component, this.params.injector, props);
      this.owners.set(element, preset);
      return true;
    }
    return;
  }
  /**
   * Adds a preset to the plugin.
   * @param preset Preset that can render nodes, connections and other elements.
   */
  addPreset(preset) {
    const local = preset;
    if (local.attach)
      local.attach(this);
    this.presets.push(local);
  }
};
export {
  AngularPlugin,
  ConnectionComponent,
  ConnectionWrapperComponent,
  ContextMenuComponent,
  ContextMenuItemComponent,
  ContextMenuSearchComponent,
  ControlComponent,
  ImpureKeyvaluePipe,
  MiniNodeComponent,
  MiniViewportComponent,
  MinimapComponent,
  NodeComponent,
  PinComponent,
  PinsComponent,
  index as Presets,
  RefDirective,
  ReteContextMenuModule,
  ReteMinimapModule,
  ReteModule,
  ReteRerouteModule,
  SocketComponent,
  NodeComponent as ɵa,
  ConnectionComponent as ɵb,
  ConnectionWrapperComponent as ɵc,
  SocketComponent as ɵd,
  ControlComponent as ɵe,
  ImpureKeyvaluePipe as ɵf,
  ContextMenuComponent as ɵg,
  ContextMenuSearchComponent as ɵh,
  ContextMenuItemComponent as ɵi,
  MinimapComponent as ɵj,
  MiniViewportComponent as ɵk,
  MiniNodeComponent as ɵl,
  PinsComponent as ɵm,
  PinComponent as ɵn
};
//# sourceMappingURL=rete-angular-plugin.js.map
