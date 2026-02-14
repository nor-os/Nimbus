import {
  CommonModule,
  NgForOf,
  NgIf
} from "./chunk-3II4CH2V.js";
import {
  ApplicationRef,
  ChangeDetectorRef,
  Component,
  ComponentFactoryResolver$1,
  Directive,
  ElementRef,
  EventEmitter,
  HostBinding,
  HostListener,
  Injector,
  Input,
  NgModule,
  NgZone,
  Output,
  Pipe,
  SimpleChange,
  Version,
  ViewContainerRef,
  setClassMetadata,
  ɵsetClassDebugInfo,
  ɵɵNgOnChangesFeature,
  ɵɵadvance,
  ɵɵattribute,
  ɵɵclassProp,
  ɵɵdefineComponent,
  ɵɵdefineDirective,
  ɵɵdefineInjector,
  ɵɵdefineNgModule,
  ɵɵdefinePipe,
  ɵɵdirectiveInject,
  ɵɵelement,
  ɵɵelementEnd,
  ɵɵelementStart,
  ɵɵgetCurrentView,
  ɵɵhostProperty,
  ɵɵlistener,
  ɵɵnamespaceSVG,
  ɵɵnextContext,
  ɵɵpipe,
  ɵɵpipeBind2,
  ɵɵprojection,
  ɵɵprojectionDef,
  ɵɵproperty,
  ɵɵpureFunction1,
  ɵɵpureFunction4,
  ɵɵresetView,
  ɵɵrestoreView,
  ɵɵsetNgModuleScope,
  ɵɵstyleProp,
  ɵɵtemplate,
  ɵɵtext,
  ɵɵtextInterpolate,
  ɵɵtextInterpolate1
} from "./chunk-KHB3FGJO.js";
import {
  merge
} from "./chunk-4RMHXXWK.js";
import "./chunk-LFVCTHGI.js";
import {
  ReplaySubject,
  map,
  switchMap
} from "./chunk-AJN3JCM6.js";
import {
  _slicedToArray
} from "./chunk-MTISOBFE.js";
import {
  BaseAreaPlugin,
  _toConsumableArray
} from "./chunk-FDF2NVCL.js";
import {
  Scope,
  _asyncToGenerator,
  _classCallCheck,
  _createClass,
  _defineProperty,
  _getPrototypeOf,
  _inherits,
  _possibleConstructorReturn,
  classic,
  getUID,
  require_regenerator
} from "./chunk-PXWGCFSP.js";
import {
  __async,
  __spreadProps,
  __spreadValues,
  __toESM
} from "./chunk-TXDUYLVM.js";

// node_modules/rete-render-utils/rete-render-utils.esm.js
var import_regenerator = __toESM(require_regenerator());
function classicConnectionPath(points, curvature) {
  var _points = _slicedToArray(points, 2), _points$ = _points[0], x1 = _points$.x, y1 = _points$.y, _points$2 = _points[1], x2 = _points$2.x, y2 = _points$2.y;
  var vertical = Math.abs(y1 - y2);
  var hx1 = x1 + Math.max(vertical / 2, Math.abs(x2 - x1)) * curvature;
  var hx2 = x2 - Math.max(vertical / 2, Math.abs(x2 - x1)) * curvature;
  return "M ".concat(x1, " ").concat(y1, " C ").concat(hx1, " ").concat(y1, " ").concat(hx2, " ").concat(y2, " ").concat(x2, " ").concat(y2);
}
function loopConnectionPath(points, curvature, size) {
  var _points2 = _slicedToArray(points, 2), _points2$ = _points2[0], x1 = _points2$.x, y1 = _points2$.y, _points2$2 = _points2[1], x2 = _points2$2.x, y2 = _points2$2.y;
  var k = y2 > y1 ? 1 : -1;
  var scale = size + Math.abs(x1 - x2) / (size / 2);
  var middleX = (x1 + x2) / 2;
  var middleY = y1 - k * scale;
  var vertical = (y2 - y1) * curvature;
  return "\n        M ".concat(x1, " ").concat(y1, "\n        C ").concat(x1 + scale, " ").concat(y1, "\n        ").concat(x1 + scale, " ").concat(middleY - vertical, "\n        ").concat(middleX, " ").concat(middleY, "\n        C ").concat(x2 - scale, " ").concat(middleY + vertical, "\n        ").concat(x2 - scale, " ").concat(y2, "\n        ").concat(x2, " ").concat(y2, "\n    ");
}
function getElementCenter(_x, _x2) {
  return _getElementCenter.apply(this, arguments);
}
function _getElementCenter() {
  _getElementCenter = _asyncToGenerator(import_regenerator.default.mark(function _callee(child, parent) {
    var x, y, currentElement, width, height;
    return import_regenerator.default.wrap(function _callee$(_context) {
      while (1) switch (_context.prev = _context.next) {
        case 0:
          if (child.offsetParent) {
            _context.next = 5;
            break;
          }
          _context.next = 3;
          return new Promise(function(res) {
            return setTimeout(res, 0);
          });
        case 3:
          _context.next = 0;
          break;
        case 5:
          x = child.offsetLeft;
          y = child.offsetTop;
          currentElement = child.offsetParent;
          if (currentElement) {
            _context.next = 10;
            break;
          }
          throw new Error("child has null offsetParent");
        case 10:
          while (currentElement !== null && currentElement !== parent) {
            x += currentElement.offsetLeft + currentElement.clientLeft;
            y += currentElement.offsetTop + currentElement.clientTop;
            currentElement = currentElement.offsetParent;
          }
          width = child.offsetWidth;
          height = child.offsetHeight;
          return _context.abrupt("return", {
            x: x + width / 2,
            y: y + height / 2
          });
        case 14:
        case "end":
          return _context.stop();
      }
    }, _callee);
  }));
  return _getElementCenter.apply(this, arguments);
}
var EventEmitter2 = function() {
  function EventEmitter3() {
    _classCallCheck(this, EventEmitter3);
    _defineProperty(this, "listeners", /* @__PURE__ */ new Set());
  }
  return _createClass(EventEmitter3, [{
    key: "emit",
    value: function emit(data) {
      this.listeners.forEach(function(listener) {
        listener(data);
      });
    }
  }, {
    key: "listen",
    value: function listen(handler) {
      var _this = this;
      this.listeners.add(handler);
      return function() {
        _this.listeners["delete"](handler);
      };
    }
  }]);
}();
var SocketsPositionsStorage = function() {
  function SocketsPositionsStorage2() {
    _classCallCheck(this, SocketsPositionsStorage2);
    _defineProperty(this, "elements", /* @__PURE__ */ new Map());
  }
  return _createClass(SocketsPositionsStorage2, [{
    key: "getPosition",
    value: function getPosition(data) {
      var _found$pop$position, _found$pop;
      var list = Array.from(this.elements.values()).flat();
      var found = list.filter(function(item) {
        return item.side === data.side && item.nodeId === data.nodeId && item.key === data.key;
      });
      if (found.length > 1) console.warn(["Found more than one element for socket with same key and side.", "Probably it was not unmounted correctly"].join(" "), data);
      return (_found$pop$position = (_found$pop = found.pop()) === null || _found$pop === void 0 ? void 0 : _found$pop.position) !== null && _found$pop$position !== void 0 ? _found$pop$position : null;
    }
  }, {
    key: "add",
    value: function add(data) {
      var existing = this.elements.get(data.element);
      this.elements.set(data.element, existing ? [].concat(_toConsumableArray(existing.filter(function(n) {
        return !(n.nodeId === data.nodeId && n.key === data.key && n.side === data.side);
      })), [data]) : [data]);
    }
  }, {
    key: "remove",
    value: function remove(element) {
      this.elements["delete"](element);
    }
  }, {
    key: "snapshot",
    value: function snapshot() {
      return Array.from(this.elements.values()).flat();
    }
  }]);
}();
var BaseSocketPosition = function() {
  function BaseSocketPosition2() {
    _classCallCheck(this, BaseSocketPosition2);
    _defineProperty(this, "sockets", new SocketsPositionsStorage());
    _defineProperty(this, "emitter", new EventEmitter2());
    _defineProperty(this, "area", null);
  }
  return _createClass(BaseSocketPosition2, [{
    key: "attach",
    value: (
      /**
       * Attach the watcher to the area's child scope.
       * @param scope Scope of the watcher that should be a child of `BaseAreaPlugin`
       */
      function attach(scope) {
        var _this = this;
        if (this.area) return;
        if (!scope.hasParent()) return;
        this.area = scope.parentScope(BaseAreaPlugin);
        this.area.addPipe(function() {
          var _ref = _asyncToGenerator(import_regenerator.default.mark(function _callee2(context) {
            var _context$data, _nodeId, _key, _side, _element, position, _nodeId2, _context$data$payload, source, target, _nodeId3;
            return import_regenerator.default.wrap(function _callee2$(_context2) {
              while (1) switch (_context2.prev = _context2.next) {
                case 0:
                  if (!(context.type === "rendered" && context.data.type === "socket")) {
                    _context2.next = 8;
                    break;
                  }
                  _context$data = context.data, _nodeId = _context$data.nodeId, _key = _context$data.key, _side = _context$data.side, _element = _context$data.element;
                  _context2.next = 4;
                  return _this.calculatePosition(_nodeId, _side, _key, _element);
                case 4:
                  position = _context2.sent;
                  if (position) {
                    _this.sockets.add({
                      nodeId: _nodeId,
                      key: _key,
                      side: _side,
                      element: _element,
                      position
                    });
                    _this.emitter.emit({
                      nodeId: _nodeId,
                      key: _key,
                      side: _side
                    });
                  }
                  _context2.next = 24;
                  break;
                case 8:
                  if (!(context.type === "unmount")) {
                    _context2.next = 12;
                    break;
                  }
                  _this.sockets.remove(context.data.element);
                  _context2.next = 24;
                  break;
                case 12:
                  if (!(context.type === "nodetranslated")) {
                    _context2.next = 16;
                    break;
                  }
                  _this.emitter.emit({
                    nodeId: context.data.id
                  });
                  _context2.next = 24;
                  break;
                case 16:
                  if (!(context.type === "noderesized")) {
                    _context2.next = 23;
                    break;
                  }
                  _nodeId2 = context.data.id;
                  _context2.next = 20;
                  return Promise.all(_this.sockets.snapshot().filter(function(item) {
                    return item.nodeId === context.data.id && item.side === "output";
                  }).map(function() {
                    var _ref2 = _asyncToGenerator(import_regenerator.default.mark(function _callee(item) {
                      var side, key, element, position2;
                      return import_regenerator.default.wrap(function _callee$(_context) {
                        while (1) switch (_context.prev = _context.next) {
                          case 0:
                            side = item.side, key = item.key, element = item.element;
                            _context.next = 3;
                            return _this.calculatePosition(_nodeId2, side, key, element);
                          case 3:
                            position2 = _context.sent;
                            if (position2) {
                              item.position = position2;
                            }
                          case 5:
                          case "end":
                            return _context.stop();
                        }
                      }, _callee);
                    }));
                    return function(_x2) {
                      return _ref2.apply(this, arguments);
                    };
                  }()));
                case 20:
                  _this.emitter.emit({
                    nodeId: _nodeId2
                  });
                  _context2.next = 24;
                  break;
                case 23:
                  if (context.type === "render" && context.data.type === "connection") {
                    _context$data$payload = context.data.payload, source = _context$data$payload.source, target = _context$data$payload.target;
                    _nodeId3 = source || target;
                    _this.emitter.emit({
                      nodeId: _nodeId3
                    });
                  }
                case 24:
                  return _context2.abrupt("return", context);
                case 25:
                case "end":
                  return _context2.stop();
              }
            }, _callee2);
          }));
          return function(_x) {
            return _ref.apply(this, arguments);
          };
        }());
      }
    )
    /**
     * Listen to socket position changes. Usually used by rendering plugins to update the start/end of the connection.
     * @internal
     * @param nodeId Node ID
     * @param side Side of the socket, 'input' or 'output'
     * @param key Socket key
     * @param change Callback function that is called when the socket position changes
     */
  }, {
    key: "listen",
    value: function listen(nodeId, side, key, change) {
      var _this2 = this;
      var unlisten = this.emitter.listen(function(data) {
        if (data.nodeId !== nodeId) return;
        if ((!data.key || data.side === side) && (!data.side || data.key === key)) {
          var _this2$area;
          var position = _this2.sockets.getPosition({
            side,
            nodeId,
            key
          });
          if (!position) return;
          var x = position.x, y = position.y;
          var nodeView = (_this2$area = _this2.area) === null || _this2$area === void 0 ? void 0 : _this2$area.nodeViews.get(nodeId);
          if (nodeView) change({
            x: x + nodeView.position.x,
            y: y + nodeView.position.y
          });
        }
      });
      this.sockets.snapshot().forEach(function(data) {
        if (data.nodeId === nodeId) _this2.emitter.emit(data);
      });
      return unlisten;
    }
  }]);
}();
function _callSuper(t, o, e) {
  return o = _getPrototypeOf(o), _possibleConstructorReturn(t, _isNativeReflectConstruct() ? Reflect.construct(o, e || [], _getPrototypeOf(t).constructor) : o.apply(t, e));
}
function _isNativeReflectConstruct() {
  try {
    var t = !Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function() {
    }));
  } catch (t2) {
  }
  return (_isNativeReflectConstruct = function _isNativeReflectConstruct2() {
    return !!t;
  })();
}
var DOMSocketPosition = function(_BaseSocketPosition) {
  function DOMSocketPosition2(props) {
    var _this;
    _classCallCheck(this, DOMSocketPosition2);
    _this = _callSuper(this, DOMSocketPosition2);
    _this.props = props;
    return _this;
  }
  _inherits(DOMSocketPosition2, _BaseSocketPosition);
  return _createClass(DOMSocketPosition2, [{
    key: "calculatePosition",
    value: function() {
      var _calculatePosition = _asyncToGenerator(import_regenerator.default.mark(function _callee(nodeId, side, key, element) {
        var _this$area, _this$props;
        var view, position;
        return import_regenerator.default.wrap(function _callee$(_context) {
          while (1) switch (_context.prev = _context.next) {
            case 0:
              view = (_this$area = this.area) === null || _this$area === void 0 ? void 0 : _this$area.nodeViews.get(nodeId);
              if (view !== null && view !== void 0 && view.element) {
                _context.next = 3;
                break;
              }
              return _context.abrupt("return", null);
            case 3:
              _context.next = 5;
              return getElementCenter(element, view.element);
            case 5:
              position = _context.sent;
              if (!((_this$props = this.props) !== null && _this$props !== void 0 && _this$props.offset)) {
                _context.next = 8;
                break;
              }
              return _context.abrupt("return", this.props.offset(position, nodeId, side, key));
            case 8:
              return _context.abrupt("return", {
                x: position.x + 12 * (side === "input" ? -1 : 1),
                y: position.y
              });
            case 9:
            case "end":
              return _context.stop();
          }
        }, _callee, this);
      }));
      function calculatePosition(_x, _x2, _x3, _x4) {
        return _calculatePosition.apply(this, arguments);
      }
      return calculatePosition;
    }()
  }]);
}(BaseSocketPosition);
function getDOMSocketPosition(props) {
  return new DOMSocketPosition(props);
}

// node_modules/@angular/elements/fesm2022/elements.mjs
var scheduler = {
  /**
   * Schedule a callback to be called after some delay.
   *
   * Returns a function that when executed will cancel the scheduled function.
   */
  schedule(taskFn, delay) {
    const id = setTimeout(taskFn, delay);
    return () => clearTimeout(id);
  },
  /**
   * Schedule a callback to be called before the next render.
   * (If `window.requestAnimationFrame()` is not available, use `scheduler.schedule()` instead.)
   *
   * Returns a function that when executed will cancel the scheduled function.
   */
  scheduleBeforeRender(taskFn) {
    if (typeof window === "undefined") {
      return scheduler.schedule(taskFn, 0);
    }
    if (typeof window.requestAnimationFrame === "undefined") {
      const frameMs = 16;
      return scheduler.schedule(taskFn, frameMs);
    }
    const id = window.requestAnimationFrame(taskFn);
    return () => window.cancelAnimationFrame(id);
  }
};
function camelToDashCase(input) {
  return input.replace(/[A-Z]/g, (char) => `-${char.toLowerCase()}`);
}
function isElement(node) {
  return !!node && node.nodeType === Node.ELEMENT_NODE;
}
function isFunction(value) {
  return typeof value === "function";
}
var _matches;
function matchesSelector(el, selector) {
  if (!_matches) {
    const elProto = Element.prototype;
    _matches = elProto.matches || elProto.matchesSelector || elProto.mozMatchesSelector || elProto.msMatchesSelector || elProto.oMatchesSelector || elProto.webkitMatchesSelector;
  }
  return el.nodeType === Node.ELEMENT_NODE ? _matches.call(el, selector) : false;
}
function strictEquals(value1, value2) {
  return value1 === value2 || value1 !== value1 && value2 !== value2;
}
function getDefaultAttributeToPropertyInputs(inputs) {
  const attributeToPropertyInputs = {};
  inputs.forEach(({ propName, templateName, transform }) => {
    attributeToPropertyInputs[camelToDashCase(templateName)] = [propName, transform];
  });
  return attributeToPropertyInputs;
}
function getComponentInputs(component, injector) {
  const componentFactoryResolver = injector.get(ComponentFactoryResolver$1);
  const componentFactory = componentFactoryResolver.resolveComponentFactory(component);
  return componentFactory.inputs;
}
function extractProjectableNodes(host, ngContentSelectors) {
  const nodes = host.childNodes;
  const projectableNodes = ngContentSelectors.map(() => []);
  let wildcardIndex = -1;
  ngContentSelectors.some((selector, i) => {
    if (selector === "*") {
      wildcardIndex = i;
      return true;
    }
    return false;
  });
  for (let i = 0, ii = nodes.length; i < ii; ++i) {
    const node = nodes[i];
    const ngContentIndex = findMatchingIndex(node, ngContentSelectors, wildcardIndex);
    if (ngContentIndex !== -1) {
      projectableNodes[ngContentIndex].push(node);
    }
  }
  return projectableNodes;
}
function findMatchingIndex(node, selectors, defaultIndex) {
  let matchingIndex = defaultIndex;
  if (isElement(node)) {
    selectors.some((selector, i) => {
      if (selector !== "*" && matchesSelector(node, selector)) {
        matchingIndex = i;
        return true;
      }
      return false;
    });
  }
  return matchingIndex;
}
var DESTROY_DELAY = 10;
var ComponentNgElementStrategyFactory = class {
  constructor(component, injector) {
    this.componentFactory = injector.get(ComponentFactoryResolver$1).resolveComponentFactory(component);
  }
  create(injector) {
    return new ComponentNgElementStrategy(this.componentFactory, injector);
  }
};
var ComponentNgElementStrategy = class {
  constructor(componentFactory, injector) {
    this.componentFactory = componentFactory;
    this.injector = injector;
    this.eventEmitters = new ReplaySubject(1);
    this.events = this.eventEmitters.pipe(switchMap((emitters) => merge(...emitters)));
    this.componentRef = null;
    this.viewChangeDetectorRef = null;
    this.inputChanges = null;
    this.hasInputChanges = false;
    this.implementsOnChanges = false;
    this.scheduledChangeDetectionFn = null;
    this.scheduledDestroyFn = null;
    this.initialInputValues = /* @__PURE__ */ new Map();
    this.unchangedInputs = new Set(this.componentFactory.inputs.map(({ propName }) => propName));
    this.ngZone = this.injector.get(NgZone);
    this.elementZone = typeof Zone === "undefined" ? null : this.ngZone.run(() => Zone.current);
  }
  /**
   * Initializes a new component if one has not yet been created and cancels any scheduled
   * destruction.
   */
  connect(element) {
    this.runInZone(() => {
      if (this.scheduledDestroyFn !== null) {
        this.scheduledDestroyFn();
        this.scheduledDestroyFn = null;
        return;
      }
      if (this.componentRef === null) {
        this.initializeComponent(element);
      }
    });
  }
  /**
   * Schedules the component to be destroyed after some small delay in case the element is just
   * being moved across the DOM.
   */
  disconnect() {
    this.runInZone(() => {
      if (this.componentRef === null || this.scheduledDestroyFn !== null) {
        return;
      }
      this.scheduledDestroyFn = scheduler.schedule(() => {
        if (this.componentRef !== null) {
          this.componentRef.destroy();
          this.componentRef = null;
          this.viewChangeDetectorRef = null;
        }
      }, DESTROY_DELAY);
    });
  }
  /**
   * Returns the component property value. If the component has not yet been created, the value is
   * retrieved from the cached initialization values.
   */
  getInputValue(property) {
    return this.runInZone(() => {
      if (this.componentRef === null) {
        return this.initialInputValues.get(property);
      }
      return this.componentRef.instance[property];
    });
  }
  /**
   * Sets the input value for the property. If the component has not yet been created, the value is
   * cached and set when the component is created.
   */
  setInputValue(property, value, transform) {
    this.runInZone(() => {
      if (transform) {
        value = transform.call(this.componentRef?.instance, value);
      }
      if (this.componentRef === null) {
        this.initialInputValues.set(property, value);
        return;
      }
      if (strictEquals(value, this.getInputValue(property)) && !(value === void 0 && this.unchangedInputs.has(property))) {
        return;
      }
      this.recordInputChange(property, value);
      this.unchangedInputs.delete(property);
      this.hasInputChanges = true;
      this.componentRef.instance[property] = value;
      this.scheduleDetectChanges();
    });
  }
  /**
   * Creates a new component through the component factory with the provided element host and
   * sets up its initial inputs, listens for outputs changes, and runs an initial change detection.
   */
  initializeComponent(element) {
    const childInjector = Injector.create({ providers: [], parent: this.injector });
    const projectableNodes = extractProjectableNodes(element, this.componentFactory.ngContentSelectors);
    this.componentRef = this.componentFactory.create(childInjector, projectableNodes, element);
    this.viewChangeDetectorRef = this.componentRef.injector.get(ChangeDetectorRef);
    this.implementsOnChanges = isFunction(this.componentRef.instance.ngOnChanges);
    this.initializeInputs();
    this.initializeOutputs(this.componentRef);
    this.detectChanges();
    const applicationRef = this.injector.get(ApplicationRef);
    applicationRef.attachView(this.componentRef.hostView);
  }
  /** Set any stored initial inputs on the component's properties. */
  initializeInputs() {
    this.componentFactory.inputs.forEach(({ propName, transform }) => {
      if (this.initialInputValues.has(propName)) {
        this.setInputValue(propName, this.initialInputValues.get(propName), transform);
      }
    });
    this.initialInputValues.clear();
  }
  /** Sets up listeners for the component's outputs so that the events stream emits the events. */
  initializeOutputs(componentRef) {
    const eventEmitters = this.componentFactory.outputs.map(({ propName, templateName }) => {
      const emitter = componentRef.instance[propName];
      return emitter.pipe(map((value) => ({ name: templateName, value })));
    });
    this.eventEmitters.next(eventEmitters);
  }
  /** Calls ngOnChanges with all the inputs that have changed since the last call. */
  callNgOnChanges(componentRef) {
    if (!this.implementsOnChanges || this.inputChanges === null) {
      return;
    }
    const inputChanges = this.inputChanges;
    this.inputChanges = null;
    componentRef.instance.ngOnChanges(inputChanges);
  }
  /**
   * Marks the component view for check, if necessary.
   * (NOTE: This is required when the `ChangeDetectionStrategy` is set to `OnPush`.)
   */
  markViewForCheck(viewChangeDetectorRef) {
    if (this.hasInputChanges) {
      this.hasInputChanges = false;
      viewChangeDetectorRef.markForCheck();
    }
  }
  /**
   * Schedules change detection to run on the component.
   * Ignores subsequent calls if already scheduled.
   */
  scheduleDetectChanges() {
    if (this.scheduledChangeDetectionFn) {
      return;
    }
    this.scheduledChangeDetectionFn = scheduler.scheduleBeforeRender(() => {
      this.scheduledChangeDetectionFn = null;
      this.detectChanges();
    });
  }
  /**
   * Records input changes so that the component receives SimpleChanges in its onChanges function.
   */
  recordInputChange(property, currentValue) {
    if (!this.implementsOnChanges) {
      return;
    }
    if (this.inputChanges === null) {
      this.inputChanges = {};
    }
    const pendingChange = this.inputChanges[property];
    if (pendingChange) {
      pendingChange.currentValue = currentValue;
      return;
    }
    const isFirstChange = this.unchangedInputs.has(property);
    const previousValue = isFirstChange ? void 0 : this.getInputValue(property);
    this.inputChanges[property] = new SimpleChange(previousValue, currentValue, isFirstChange);
  }
  /** Runs change detection on the component. */
  detectChanges() {
    if (this.componentRef === null) {
      return;
    }
    this.callNgOnChanges(this.componentRef);
    this.markViewForCheck(this.viewChangeDetectorRef);
    this.componentRef.changeDetectorRef.detectChanges();
  }
  /** Runs in the angular zone, if present. */
  runInZone(fn) {
    return this.elementZone && Zone.current !== this.elementZone ? this.ngZone.run(fn) : fn();
  }
};
var NgElement = class extends HTMLElement {
  constructor() {
    super(...arguments);
    this.ngElementEventsSubscription = null;
  }
};
function createCustomElement(component, config) {
  const inputs = getComponentInputs(component, config.injector);
  const strategyFactory = config.strategyFactory || new ComponentNgElementStrategyFactory(component, config.injector);
  const attributeToPropertyInputs = getDefaultAttributeToPropertyInputs(inputs);
  class NgElementImpl extends NgElement {
    static {
      this["observedAttributes"] = Object.keys(attributeToPropertyInputs);
    }
    get ngElementStrategy() {
      if (!this._ngElementStrategy) {
        const strategy = this._ngElementStrategy = strategyFactory.create(this.injector || config.injector);
        inputs.forEach(({ propName, transform }) => {
          if (!this.hasOwnProperty(propName)) {
            return;
          }
          const value = this[propName];
          delete this[propName];
          strategy.setInputValue(propName, value, transform);
        });
      }
      return this._ngElementStrategy;
    }
    constructor(injector) {
      super();
      this.injector = injector;
    }
    attributeChangedCallback(attrName, oldValue, newValue, namespace) {
      const [propName, transform] = attributeToPropertyInputs[attrName];
      this.ngElementStrategy.setInputValue(propName, newValue, transform);
    }
    connectedCallback() {
      let subscribedToEvents = false;
      if (this.ngElementStrategy.events) {
        this.subscribeToEvents();
        subscribedToEvents = true;
      }
      this.ngElementStrategy.connect(this);
      if (!subscribedToEvents) {
        this.subscribeToEvents();
      }
    }
    disconnectedCallback() {
      if (this._ngElementStrategy) {
        this._ngElementStrategy.disconnect();
      }
      if (this.ngElementEventsSubscription) {
        this.ngElementEventsSubscription.unsubscribe();
        this.ngElementEventsSubscription = null;
      }
    }
    subscribeToEvents() {
      this.ngElementEventsSubscription = this.ngElementStrategy.events.subscribe((e) => {
        const customEvent = new CustomEvent(e.name, { detail: e.value });
        this.dispatchEvent(customEvent);
      });
    }
  }
  inputs.forEach(({ propName, transform }) => {
    Object.defineProperty(NgElementImpl.prototype, propName, {
      get() {
        return this.ngElementStrategy.getInputValue(propName);
      },
      set(newValue) {
        this.ngElementStrategy.setInputValue(propName, newValue, transform);
      },
      configurable: true,
      enumerable: true
    });
  });
  return NgElementImpl;
}
var VERSION = new Version("17.3.12");

// node_modules/rete-angular-plugin/17/fesm2022/rete-angular-plugin-ng17.mjs
var RefDirective = class _RefDirective {
  el;
  data;
  emit;
  constructor(el) {
    this.el = el;
  }
  ngOnChanges() {
    this.emit({ type: "render", data: __spreadProps(__spreadValues({}, this.data), { element: this.el.nativeElement }) });
  }
  ngOnDestroy() {
    this.emit({ type: "unmount", data: { element: this.el.nativeElement } });
  }
  static ɵfac = function RefDirective_Factory(t) {
    return new (t || _RefDirective)(ɵɵdirectiveInject(ElementRef));
  };
  static ɵdir = ɵɵdefineDirective({ type: _RefDirective, selectors: [["", "refComponent", ""]], inputs: { data: "data", emit: "emit" }, features: [ɵɵNgOnChangesFeature] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(RefDirective, [{
    type: Directive,
    args: [{
      selector: "[refComponent]"
    }]
  }], () => [{ type: ElementRef }], { data: [{
    type: Input
  }], emit: [{
    type: Input
  }] });
})();
var ImpureKeyvaluePipe = class _ImpureKeyvaluePipe {
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
  static ɵfac = function ImpureKeyvaluePipe_Factory(t) {
    return new (t || _ImpureKeyvaluePipe)();
  };
  static ɵpipe = ɵɵdefinePipe({ name: "keyvalueimpure", type: _ImpureKeyvaluePipe, pure: false });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ImpureKeyvaluePipe, [{
    type: Pipe,
    args: [{
      name: "keyvalueimpure",
      pure: false
    }]
  }], null, null);
})();
var _c0$1 = (a2, a3, a4, a5) => ({ type: "socket", side: "output", key: a2, nodeId: a3, payload: a4, seed: a5 });
function NodeComponent_div_2_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "div", 4)(1, "div", 5);
    ɵɵtext(2);
    ɵɵelementEnd();
    ɵɵelement(3, "div", 6);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    const output_r3 = ctx.$implicit;
    const ctx_r0 = ɵɵnextContext();
    ɵɵattribute("data-testid", "output-" + output_r3.key);
    ɵɵadvance(2);
    ɵɵtextInterpolate(output_r3.value == null ? null : output_r3.value.label);
    ɵɵadvance(1);
    ɵɵproperty("data", ɵɵpureFunction4(4, _c0$1, output_r3.key, ctx_r0.data.id, output_r3.value == null ? null : output_r3.value.socket, ctx_r0.seed))("emit", ctx_r0.emit);
  }
}
var _c1 = (a1) => ({ type: "control", payload: a1 });
function NodeComponent_div_4_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelement(0, "div", 7);
  }
  if (rf & 2) {
    const control_r4 = ctx.$implicit;
    const ctx_r1 = ɵɵnextContext();
    ɵɵproperty("data", ɵɵpureFunction1(3, _c1, control_r4.value))("emit", ctx_r1.emit);
    ɵɵattribute("data-testid", "control-" + control_r4.key);
  }
}
function NodeComponent_div_6_div_2_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "div", 12);
    ɵɵtext(1);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    const input_r5 = ɵɵnextContext().$implicit;
    ɵɵadvance(1);
    ɵɵtextInterpolate(input_r5.value == null ? null : input_r5.value.label);
  }
}
var _c2 = (a2, a3, a4, a5) => ({ type: "socket", side: "input", key: a2, nodeId: a3, payload: a4, seed: a5 });
function NodeComponent_div_6_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "div", 8);
    ɵɵelement(1, "div", 9);
    ɵɵtemplate(2, NodeComponent_div_6_div_2_Template, 2, 1, "div", 10);
    ɵɵelement(3, "div", 11);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    const input_r5 = ctx.$implicit;
    const ctx_r2 = ɵɵnextContext();
    ɵɵattribute("data-testid", "input-" + input_r5.key);
    ɵɵadvance(1);
    ɵɵproperty("data", ɵɵpureFunction4(8, _c2, input_r5.key, ctx_r2.data.id, input_r5.value == null ? null : input_r5.value.socket, ctx_r2.seed))("emit", ctx_r2.emit);
    ɵɵadvance(1);
    ɵɵproperty("ngIf", !(input_r5.value == null ? null : input_r5.value.control) || !(input_r5.value == null ? null : input_r5.value.showControl));
    ɵɵadvance(1);
    ɵɵstyleProp("display", (input_r5.value == null ? null : input_r5.value.control) && (input_r5.value == null ? null : input_r5.value.showControl) ? "" : "none");
    ɵɵproperty("data", ɵɵpureFunction1(13, _c1, input_r5.value == null ? null : input_r5.value.control))("emit", ctx_r2.emit);
  }
}
var NodeComponent = class _NodeComponent {
  cdr;
  data;
  emit;
  rendered;
  seed = 0;
  get width() {
    return this.data.width;
  }
  get height() {
    return this.data.height;
  }
  get selected() {
    return this.data.selected;
  }
  constructor(cdr) {
    this.cdr = cdr;
    this.cdr.detach();
  }
  ngOnChanges() {
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
    this.seed++;
  }
  sortByIndex(a, b) {
    const ai = a.value?.index || 0;
    const bi = b.value?.index || 0;
    return ai - bi;
  }
  static ɵfac = function NodeComponent_Factory(t) {
    return new (t || _NodeComponent)(ɵɵdirectiveInject(ChangeDetectorRef));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _NodeComponent, selectors: [["ng-component"]], hostAttrs: ["data-testid", "node"], hostVars: 6, hostBindings: function NodeComponent_HostBindings(rf, ctx) {
    if (rf & 2) {
      ɵɵstyleProp("width", ctx.width, "px")("height", ctx.height, "px");
      ɵɵclassProp("selected", ctx.selected);
    }
  }, inputs: { data: "data", emit: "emit", rendered: "rendered" }, features: [ɵɵNgOnChangesFeature], decls: 8, vars: 13, consts: [["data-testid", "title", 1, "title"], ["class", "output", 4, "ngFor", "ngForOf"], ["class", "control", "refComponent", "", 3, "data", "emit", 4, "ngFor", "ngForOf"], ["class", "input", 4, "ngFor", "ngForOf"], [1, "output"], ["data-testid", "output-title", 1, "output-title"], ["refComponent", "", "data-testid", "output-socket", 1, "output-socket", 3, "data", "emit"], ["refComponent", "", 1, "control", 3, "data", "emit"], [1, "input"], ["refComponent", "", "data-testid", "input-socket", 1, "input-socket", 3, "data", "emit"], ["class", "input-title", "data-testid", "input-title", 4, "ngIf"], ["refComponent", "", "data-testid", "input-control", 1, "input-control", 3, "data", "emit"], ["data-testid", "input-title", 1, "input-title"]], template: function NodeComponent_Template(rf, ctx) {
    if (rf & 1) {
      ɵɵelementStart(0, "div", 0);
      ɵɵtext(1);
      ɵɵelementEnd();
      ɵɵtemplate(2, NodeComponent_div_2_Template, 4, 9, "div", 1);
      ɵɵpipe(3, "keyvalueimpure");
      ɵɵtemplate(4, NodeComponent_div_4_Template, 1, 5, "div", 2);
      ɵɵpipe(5, "keyvalueimpure");
      ɵɵtemplate(6, NodeComponent_div_6_Template, 4, 15, "div", 3);
      ɵɵpipe(7, "keyvalueimpure");
    }
    if (rf & 2) {
      ɵɵadvance(1);
      ɵɵtextInterpolate(ctx.data.label);
      ɵɵadvance(1);
      ɵɵproperty("ngForOf", ɵɵpipeBind2(3, 4, ctx.data.outputs, ctx.sortByIndex));
      ɵɵadvance(2);
      ɵɵproperty("ngForOf", ɵɵpipeBind2(5, 7, ctx.data.controls, ctx.sortByIndex));
      ɵɵadvance(2);
      ɵɵproperty("ngForOf", ɵɵpipeBind2(7, 10, ctx.data.inputs, ctx.sortByIndex));
    }
  }, dependencies: [NgForOf, NgIf, RefDirective, ImpureKeyvaluePipe], styles: ["[_nghost-%COMP%]{display:block;background:rgba(110,136,255,.8);border:2px solid #4e58bf;border-radius:10px;cursor:pointer;box-sizing:border-box;width:180px;height:auto;padding-bottom:6px;position:relative;-webkit-user-select:none;user-select:none;line-height:initial;font-family:Arial}[_nghost-%COMP%]:hover{background:rgba(130,153,255,.8)}.selected[_nghost-%COMP%]{background:#ffd92c;border-color:#e3c000}[_nghost-%COMP%]   .title[_ngcontent-%COMP%]{color:#fff;font-family:sans-serif;font-size:18px;padding:8px}[_nghost-%COMP%]   .output[_ngcontent-%COMP%]{text-align:right}[_nghost-%COMP%]   .input[_ngcontent-%COMP%]{text-align:left}[_nghost-%COMP%]   .input-title[_ngcontent-%COMP%], [_nghost-%COMP%]   .output-title[_ngcontent-%COMP%]{vertical-align:middle;color:#fff;display:inline-block;font-family:sans-serif;font-size:14px;margin:6px;line-height:24px}[_nghost-%COMP%]   .input-title[hidden][_ngcontent-%COMP%], [_nghost-%COMP%]   .output-title[hidden][_ngcontent-%COMP%]{display:none}[_nghost-%COMP%]   .output-socket[_ngcontent-%COMP%]{text-align:right;margin-right:-18px;display:inline-block}[_nghost-%COMP%]   .input-socket[_ngcontent-%COMP%]{text-align:left;margin-left:-18px;display:inline-block}[_nghost-%COMP%]   .input-control[_ngcontent-%COMP%]{z-index:1;width:calc(100% - 36px);vertical-align:middle;display:inline-block}[_nghost-%COMP%]   .control[_ngcontent-%COMP%]{padding:6px 18px}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(NodeComponent, [{
    type: Component,
    args: [{ host: {
      "data-testid": "node"
    }, template: `<div class="title" data-testid="title">{{data.label}}</div>
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
`, styles: [":host{display:block;background:rgba(110,136,255,.8);border:2px solid #4e58bf;border-radius:10px;cursor:pointer;box-sizing:border-box;width:180px;height:auto;padding-bottom:6px;position:relative;-webkit-user-select:none;user-select:none;line-height:initial;font-family:Arial}:host:hover{background:rgba(130,153,255,.8)}:host.selected{background:#ffd92c;border-color:#e3c000}:host .title{color:#fff;font-family:sans-serif;font-size:18px;padding:8px}:host .output{text-align:right}:host .input{text-align:left}:host .input-title,:host .output-title{vertical-align:middle;color:#fff;display:inline-block;font-family:sans-serif;font-size:14px;margin:6px;line-height:24px}:host .input-title[hidden],:host .output-title[hidden]{display:none}:host .output-socket{text-align:right;margin-right:-18px;display:inline-block}:host .input-socket{text-align:left;margin-left:-18px;display:inline-block}:host .input-control{z-index:1;width:calc(100% - 36px);vertical-align:middle;display:inline-block}:host .control{padding:6px 18px}\n"] }]
  }], () => [{ type: ChangeDetectorRef }], { data: [{
    type: Input
  }], emit: [{
    type: Input
  }], rendered: [{
    type: Input
  }], width: [{
    type: HostBinding,
    args: ["style.width.px"]
  }], height: [{
    type: HostBinding,
    args: ["style.height.px"]
  }], selected: [{
    type: HostBinding,
    args: ["class.selected"]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(NodeComponent, { className: "NodeComponent", filePath: "presets/classic/components/node/node.component.ts", lineNumber: 17 });
})();
var SocketComponent = class _SocketComponent {
  cdr;
  data;
  rendered;
  get title() {
    return this.data.name;
  }
  constructor(cdr) {
    this.cdr = cdr;
    this.cdr.detach();
  }
  ngOnChanges() {
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.rendered());
  }
  static ɵfac = function SocketComponent_Factory(t) {
    return new (t || _SocketComponent)(ɵɵdirectiveInject(ChangeDetectorRef));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _SocketComponent, selectors: [["ng-component"]], hostVars: 1, hostBindings: function SocketComponent_HostBindings(rf, ctx) {
    if (rf & 2) {
      ɵɵhostProperty("title", ctx.title);
    }
  }, inputs: { data: "data", rendered: "rendered" }, features: [ɵɵNgOnChangesFeature], decls: 0, vars: 0, template: function SocketComponent_Template(rf, ctx) {
  }, styles: ["[_nghost-%COMP%]{display:inline-block;cursor:pointer;border:1px solid white;border-radius:12px;width:24px;height:24px;margin:6px;vertical-align:middle;background:#96b38a;z-index:2;box-sizing:border-box}[_nghost-%COMP%]:hover{border-width:4px}.multiple[_nghost-%COMP%]{border-color:#ff0}.output[_nghost-%COMP%]{margin-right:-12px}.input[_nghost-%COMP%]{margin-left:-12px}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(SocketComponent, [{
    type: Component,
    args: [{ template: ``, styles: [":host{display:inline-block;cursor:pointer;border:1px solid white;border-radius:12px;width:24px;height:24px;margin:6px;vertical-align:middle;background:#96b38a;z-index:2;box-sizing:border-box}:host:hover{border-width:4px}:host.multiple{border-color:#ff0}:host.output{margin-right:-12px}:host.input{margin-left:-12px}\n"] }]
  }], () => [{ type: ChangeDetectorRef }], { data: [{
    type: Input
  }], rendered: [{
    type: Input
  }], title: [{
    type: HostBinding,
    args: ["title"]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(SocketComponent, { className: "SocketComponent", filePath: "presets/classic/components/socket/socket.component.ts", lineNumber: 7 });
})();
var ControlComponent = class _ControlComponent {
  cdr;
  data;
  rendered;
  pointerdown(event) {
    event.stopPropagation();
  }
  constructor(cdr) {
    this.cdr = cdr;
    this.cdr.detach();
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
  static ɵfac = function ControlComponent_Factory(t) {
    return new (t || _ControlComponent)(ɵɵdirectiveInject(ChangeDetectorRef));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _ControlComponent, selectors: [["ng-component"]], hostBindings: function ControlComponent_HostBindings(rf, ctx) {
    if (rf & 1) {
      ɵɵlistener("pointerdown", function ControlComponent_pointerdown_HostBindingHandler($event) {
        return ctx.pointerdown($event);
      });
    }
  }, inputs: { data: "data", rendered: "rendered" }, features: [ɵɵNgOnChangesFeature], decls: 1, vars: 3, consts: [[3, "value", "readonly", "type", "input"]], template: function ControlComponent_Template(rf, ctx) {
    if (rf & 1) {
      ɵɵelementStart(0, "input", 0);
      ɵɵlistener("input", function ControlComponent_Template_input_input_0_listener($event) {
        return ctx.onChange($event);
      });
      ɵɵelementEnd();
    }
    if (rf & 2) {
      ɵɵproperty("value", ctx.data.value)("readonly", ctx.data.readonly)("type", ctx.data.type);
    }
  }, styles: ["input[_ngcontent-%COMP%]{width:100%;border-radius:30px;background-color:#fff;padding:2px 6px;border:1px solid #999;font-size:110%;box-sizing:border-box}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ControlComponent, [{
    type: Component,
    args: [{ template: '<input\n  [value]="data.value"\n  [readonly]="data.readonly"\n  [type]="data.type"\n  (input)="onChange($event)"\n/>\n', styles: ["input{width:100%;border-radius:30px;background-color:#fff;padding:2px 6px;border:1px solid #999;font-size:110%;box-sizing:border-box}\n"] }]
  }], () => [{ type: ChangeDetectorRef }], { data: [{
    type: Input
  }], rendered: [{
    type: Input
  }], pointerdown: [{
    type: HostListener,
    args: ["pointerdown", ["$event"]]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(ControlComponent, { className: "ControlComponent", filePath: "presets/classic/components/control/control.component.ts", lineNumber: 8 });
})();
var ConnectionComponent = class _ConnectionComponent {
  data;
  start;
  end;
  path;
  static ɵfac = function ConnectionComponent_Factory(t) {
    return new (t || _ConnectionComponent)();
  };
  static ɵcmp = ɵɵdefineComponent({ type: _ConnectionComponent, selectors: [["connection"]], inputs: { data: "data", start: "start", end: "end", path: "path" }, decls: 2, vars: 1, consts: [["data-testid", "connection"]], template: function ConnectionComponent_Template(rf, ctx) {
    if (rf & 1) {
      ɵɵnamespaceSVG();
      ɵɵelementStart(0, "svg", 0);
      ɵɵelement(1, "path");
      ɵɵelementEnd();
    }
    if (rf & 2) {
      ɵɵadvance(1);
      ɵɵattribute("d", ctx.path);
    }
  }, styles: ["svg[_ngcontent-%COMP%]{overflow:visible!important;position:absolute;pointer-events:none;width:9999px;height:9999px}svg[_ngcontent-%COMP%]   path[_ngcontent-%COMP%]{fill:none;stroke-width:5px;stroke:#4682b4;pointer-events:auto}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ConnectionComponent, [{
    type: Component,
    args: [{ selector: "connection", template: '<svg data-testid="connection">\n    <path [attr.d]="path" />\n</svg>\n', styles: ["svg{overflow:visible!important;position:absolute;pointer-events:none;width:9999px;height:9999px}svg path{fill:none;stroke-width:5px;stroke:#4682b4;pointer-events:auto}\n"] }]
  }], null, { data: [{
    type: Input
  }], start: [{
    type: Input
  }], end: [{
    type: Input
  }], path: [{
    type: Input
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(ConnectionComponent, { className: "ConnectionComponent", filePath: "presets/classic/components/connection/connection.component.ts", lineNumber: 12 });
})();
var ConnectionWrapperComponent = class _ConnectionWrapperComponent {
  cdr;
  viewContainerRef;
  componentFactoryResolver;
  data;
  start;
  end;
  path;
  rendered;
  connectionComponent;
  ref;
  startOb = null;
  get _start() {
    return "x" in this.start ? this.start : this.startOb;
  }
  endOb = null;
  get _end() {
    return "x" in this.end ? this.end : this.endOb;
  }
  _path;
  constructor(cdr, viewContainerRef, componentFactoryResolver) {
    this.cdr = cdr;
    this.viewContainerRef = viewContainerRef;
    this.componentFactoryResolver = componentFactoryResolver;
    this.cdr.detach();
  }
  ngOnChanges() {
    return __async(this, null, function* () {
      yield this.updatePath();
      requestAnimationFrame(() => this.rendered());
      this.cdr.detectChanges();
      this.update();
    });
  }
  updatePath() {
    return __async(this, null, function* () {
      if (this._start && this._end) {
        this._path = yield this.path(this._start, this._end);
      }
    });
  }
  ngOnInit() {
    if (typeof this.start === "function") {
      this.start((value) => __async(this, null, function* () {
        this.startOb = value;
        yield this.updatePath();
        this.cdr.detectChanges();
        this.update();
      }));
    }
    if (typeof this.end === "function") {
      this.end((value) => __async(this, null, function* () {
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
  static ɵfac = function ConnectionWrapperComponent_Factory(t) {
    return new (t || _ConnectionWrapperComponent)(ɵɵdirectiveInject(ChangeDetectorRef), ɵɵdirectiveInject(ViewContainerRef), ɵɵdirectiveInject(ComponentFactoryResolver$1));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _ConnectionWrapperComponent, selectors: [["ng-component"]], inputs: { data: "data", start: "start", end: "end", path: "path", rendered: "rendered", connectionComponent: "connectionComponent" }, features: [ɵɵNgOnChangesFeature], decls: 0, vars: 0, template: function ConnectionWrapperComponent_Template(rf, ctx) {
  }, encapsulation: 2 });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ConnectionWrapperComponent, [{
    type: Component,
    args: [{
      template: ""
    }]
  }], () => [{ type: ChangeDetectorRef }, { type: ViewContainerRef }, { type: ComponentFactoryResolver$1 }], { data: [{
    type: Input
  }], start: [{
    type: Input
  }], end: [{
    type: Input
  }], path: [{
    type: Input
  }], rendered: [{
    type: Input
  }], connectionComponent: [{
    type: Input
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(ConnectionWrapperComponent, { className: "ConnectionWrapperComponent", filePath: "presets/classic/components/connection/connection-wrapper.component.ts", lineNumber: 10 });
})();
function setup$3(props) {
  const positionWatcher = typeof props?.socketPositionWatcher === "undefined" ? getDOMSocketPosition() : props?.socketPositionWatcher;
  const { node, connection, socket, control } = props?.customize || {};
  return {
    attach(plugin) {
      positionWatcher.attach(plugin);
    },
    update(context) {
      const data = context.data.payload;
      if (context.data.type === "connection") {
        const { start, end } = context.data;
        return __spreadValues(__spreadValues({
          data
        }, start ? { start } : {}), end ? { end } : {});
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
            path: (start2, end2) => __async(this, null, function* () {
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
var ContextMenuSearchComponent = class _ContextMenuSearchComponent {
  value;
  update = new EventEmitter();
  static ɵfac = function ContextMenuSearchComponent_Factory(t) {
    return new (t || _ContextMenuSearchComponent)();
  };
  static ɵcmp = ɵɵdefineComponent({ type: _ContextMenuSearchComponent, selectors: [["context-menu-search"]], inputs: { value: "value" }, outputs: { update: "update" }, decls: 1, vars: 1, consts: [["data-testid", "context-menu-search-input", 1, "search", 3, "value", "input"]], template: function ContextMenuSearchComponent_Template(rf, ctx) {
    if (rf & 1) {
      ɵɵelementStart(0, "input", 0);
      ɵɵlistener("input", function ContextMenuSearchComponent_Template_input_input_0_listener($event) {
        let tmp_b_0;
        return ctx.update.emit(((tmp_b_0 = $event.target) == null ? null : tmp_b_0.value) || "");
      });
      ɵɵelementEnd();
    }
    if (rf & 2) {
      ɵɵproperty("value", ctx.value);
    }
  }, styles: [".search[_ngcontent-%COMP%]{color:#fff;padding:1px 8px;border:1px solid white;border-radius:10px;font-size:16px;font-family:serif;width:100%;box-sizing:border-box;background:transparent}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ContextMenuSearchComponent, [{
    type: Component,
    args: [{ selector: "context-menu-search", template: `<input class="search" [value]="value" (input)="update.emit($any($event.target)?.value || '')"
  data-testid="context-menu-search-input" />
`, styles: [".search{color:#fff;padding:1px 8px;border:1px solid white;border-radius:10px;font-size:16px;font-family:serif;width:100%;box-sizing:border-box;background:transparent}\n"] }]
  }], null, { value: [{
    type: Input
  }], update: [{
    type: Output
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(ContextMenuSearchComponent, { className: "ContextMenuSearchComponent", filePath: "presets/context-menu/components/search/search.component.ts", lineNumber: 8 });
})();
function ContextMenuItemComponent_div_1_context_menu_item_1_Template(rf, ctx) {
  if (rf & 1) {
    const _r4 = ɵɵgetCurrentView();
    ɵɵelementStart(0, "context-menu-item", 3);
    ɵɵlistener("select", function ContextMenuItemComponent_div_1_context_menu_item_1_Template_context_menu_item_select_0_listener() {
      const restoredCtx = ɵɵrestoreView(_r4);
      const item_r2 = restoredCtx.$implicit;
      return ɵɵresetView(item_r2.handler());
    })("hide", function ContextMenuItemComponent_div_1_context_menu_item_1_Template_context_menu_item_hide_0_listener() {
      ɵɵrestoreView(_r4);
      const ctx_r5 = ɵɵnextContext(2);
      return ɵɵresetView(ctx_r5.hide.emit());
    });
    ɵɵtext(1);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    const item_r2 = ctx.$implicit;
    const ctx_r1 = ɵɵnextContext(2);
    ɵɵproperty("delay", ctx_r1.delay);
    ɵɵadvance(1);
    ɵɵtextInterpolate1(" ", item_r2.label, " ");
  }
}
function ContextMenuItemComponent_div_1_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelementStart(0, "div", 1);
    ɵɵtemplate(1, ContextMenuItemComponent_div_1_context_menu_item_1_Template, 2, 2, "context-menu-item", 2);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    const ctx_r0 = ɵɵnextContext();
    ɵɵadvance(1);
    ɵɵproperty("ngForOf", ctx_r0.subitems);
  }
}
var _c0 = ["*"];
var ContextMenuItemComponent = class _ContextMenuItemComponent {
  cdr;
  subitems;
  delay;
  select = new EventEmitter();
  hide = new EventEmitter();
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
  hideSubitems = debounce(() => {
    this.visibleSubitems = false;
    this.cdr.detectChanges();
  });
  visibleSubitems = false;
  pointerover() {
    this.hideSubitems.cancel();
    this.visibleSubitems = true;
    this.cdr.detectChanges();
  }
  pointerleave() {
    this.hideSubitems.call(this.delay);
    this.cdr.detectChanges();
  }
  constructor(cdr) {
    this.cdr = cdr;
    this.cdr.detach();
  }
  static ɵfac = function ContextMenuItemComponent_Factory(t) {
    return new (t || _ContextMenuItemComponent)(ɵɵdirectiveInject(ChangeDetectorRef));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _ContextMenuItemComponent, selectors: [["context-menu-item"]], hostAttrs: ["data-testid", "context-menu-item"], hostVars: 4, hostBindings: function ContextMenuItemComponent_HostBindings(rf, ctx) {
    if (rf & 1) {
      ɵɵlistener("click", function ContextMenuItemComponent_click_HostBindingHandler($event) {
        return ctx.click($event);
      })("pointerdown", function ContextMenuItemComponent_pointerdown_HostBindingHandler($event) {
        return ctx.pointerdown($event);
      })("wheel", function ContextMenuItemComponent_wheel_HostBindingHandler($event) {
        return ctx.wheel($event);
      })("pointerover", function ContextMenuItemComponent_pointerover_HostBindingHandler() {
        return ctx.pointerover();
      })("pointerleave", function ContextMenuItemComponent_pointerleave_HostBindingHandler() {
        return ctx.pointerleave();
      });
    }
    if (rf & 2) {
      ɵɵclassProp("block", ctx.block)("hasSubitems", ctx.hasSubitems);
    }
  }, inputs: { subitems: "subitems", delay: "delay" }, outputs: { select: "select", hide: "hide" }, ngContentSelectors: _c0, decls: 2, vars: 1, consts: [["class", "subitems", 4, "ngIf"], [1, "subitems"], [3, "delay", "select", "hide", 4, "ngFor", "ngForOf"], [3, "delay", "select", "hide"]], template: function ContextMenuItemComponent_Template(rf, ctx) {
    if (rf & 1) {
      ɵɵprojectionDef();
      ɵɵprojection(0);
      ɵɵtemplate(1, ContextMenuItemComponent_div_1_Template, 2, 1, "div", 0);
    }
    if (rf & 2) {
      ɵɵadvance(1);
      ɵɵproperty("ngIf", ctx.subitems && ctx.visibleSubitems);
    }
  }, dependencies: [NgForOf, NgIf, _ContextMenuItemComponent], styles: ['@charset "UTF-8";.hasSubitems[_nghost-%COMP%]:after{content:"\\25ba";position:absolute;opacity:.6;right:5px;top:5px;font-family:initial}.subitems[_ngcontent-%COMP%]{position:absolute;top:0;left:100%;width:120px}', ".block[_ngcontent-%COMP%]{display:block;color:#fff;padding:4px;border-bottom:1px solid rgba(69,103,255,.8);background-color:#6e88ffcc;cursor:pointer;width:100%;position:relative}.block[_ngcontent-%COMP%]:first-child{border-top-left-radius:5px;border-top-right-radius:5px}.block[_ngcontent-%COMP%]:last-child{border-bottom-left-radius:5px;border-bottom-right-radius:5px}.block[_ngcontent-%COMP%]:hover{background-color:#8299ffcc}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ContextMenuItemComponent, [{
    type: Component,
    args: [{ selector: "context-menu-item", host: {
      "data-testid": "context-menu-item"
    }, template: '<ng-content></ng-content>\n<div class="subitems" *ngIf="subitems && visibleSubitems">\n  <context-menu-item *ngFor="let item of subitems" [delay]="delay" (select)="item.handler()" (hide)="hide.emit()">\n    {{ item.label }}\n  </context-menu-item>\n</div>\n', styles: ['@charset "UTF-8";:host(.hasSubitems):after{content:"\\25ba";position:absolute;opacity:.6;right:5px;top:5px;font-family:initial}.subitems{position:absolute;top:0;left:100%;width:120px}\n', ".block{display:block;color:#fff;padding:4px;border-bottom:1px solid rgba(69,103,255,.8);background-color:#6e88ffcc;cursor:pointer;width:100%;position:relative}.block:first-child{border-top-left-radius:5px;border-top-right-radius:5px}.block:last-child{border-bottom-left-radius:5px;border-bottom-right-radius:5px}.block:hover{background-color:#8299ffcc}\n"] }]
  }], () => [{ type: ChangeDetectorRef }], { subitems: [{
    type: Input
  }], delay: [{
    type: Input
  }], select: [{
    type: Output
  }], hide: [{
    type: Output
  }], block: [{
    type: HostBinding,
    args: ["class.block"]
  }], hasSubitems: [{
    type: HostBinding,
    args: ["class.hasSubitems"]
  }], click: [{
    type: HostListener,
    args: ["click", ["$event"]]
  }], pointerdown: [{
    type: HostListener,
    args: ["pointerdown", ["$event"]]
  }], wheel: [{
    type: HostListener,
    args: ["wheel", ["$event"]]
  }], pointerover: [{
    type: HostListener,
    args: ["pointerover"]
  }], pointerleave: [{
    type: HostListener,
    args: ["pointerleave"]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(ContextMenuItemComponent, { className: "ContextMenuItemComponent", filePath: "presets/context-menu/components/item/item.component.ts", lineNumber: 15 });
})();
function ContextMenuComponent_div_0_Template(rf, ctx) {
  if (rf & 1) {
    const _r3 = ɵɵgetCurrentView();
    ɵɵelementStart(0, "div", 2)(1, "context-menu-search", 3);
    ɵɵlistener("update", function ContextMenuComponent_div_0_Template_context_menu_search_update_1_listener($event) {
      ɵɵrestoreView(_r3);
      const ctx_r2 = ɵɵnextContext();
      return ɵɵresetView(ctx_r2.setFilter($event));
    });
    ɵɵelementEnd()();
  }
  if (rf & 2) {
    const ctx_r0 = ɵɵnextContext();
    ɵɵadvance(1);
    ɵɵproperty("value", ctx_r0.filter);
  }
}
function ContextMenuComponent_context_menu_item_1_Template(rf, ctx) {
  if (rf & 1) {
    const _r6 = ɵɵgetCurrentView();
    ɵɵelementStart(0, "context-menu-item", 4);
    ɵɵlistener("select", function ContextMenuComponent_context_menu_item_1_Template_context_menu_item_select_0_listener() {
      const restoredCtx = ɵɵrestoreView(_r6);
      const item_r4 = restoredCtx.$implicit;
      return ɵɵresetView(item_r4.handler());
    })("hide", function ContextMenuComponent_context_menu_item_1_Template_context_menu_item_hide_0_listener() {
      ɵɵrestoreView(_r6);
      const ctx_r7 = ɵɵnextContext();
      return ɵɵresetView(ctx_r7.onHide());
    });
    ɵɵtext(1);
    ɵɵelementEnd();
  }
  if (rf & 2) {
    const item_r4 = ctx.$implicit;
    const ctx_r1 = ɵɵnextContext();
    ɵɵproperty("delay", ctx_r1.delay)("subitems", item_r4.subitems);
    ɵɵadvance(1);
    ɵɵtextInterpolate1(" ", item_r4.label, "\n");
  }
}
var ContextMenuComponent = class _ContextMenuComponent {
  cdr;
  items;
  delay;
  searchBar;
  onHide;
  rendered;
  filter = "";
  hide = debounce(() => {
    this.onHide();
    this.cdr.detectChanges();
  });
  customAttribute = "";
  pointerover() {
    this.hide.cancel();
    this.cdr.detectChanges();
  }
  pointerleave() {
    this.hide.call(this.delay);
    this.cdr.detectChanges();
  }
  constructor(cdr) {
    this.cdr = cdr;
    this.cdr.detach();
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
  static ɵfac = function ContextMenuComponent_Factory(t) {
    return new (t || _ContextMenuComponent)(ɵɵdirectiveInject(ChangeDetectorRef));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _ContextMenuComponent, selectors: [["ng-component"]], hostAttrs: ["data-testid", "context-menu"], hostVars: 1, hostBindings: function ContextMenuComponent_HostBindings(rf, ctx) {
    if (rf & 1) {
      ɵɵlistener("mouseover", function ContextMenuComponent_mouseover_HostBindingHandler() {
        return ctx.pointerover();
      })("mouseleave", function ContextMenuComponent_mouseleave_HostBindingHandler() {
        return ctx.pointerleave();
      });
    }
    if (rf & 2) {
      ɵɵattribute("rete-context-menu", ctx.customAttribute);
    }
  }, inputs: { items: "items", delay: "delay", searchBar: "searchBar", onHide: "onHide", rendered: "rendered" }, features: [ɵɵNgOnChangesFeature], decls: 2, vars: 2, consts: [["class", "block", 4, "ngIf"], [3, "delay", "subitems", "select", "hide", 4, "ngFor", "ngForOf"], [1, "block"], [3, "value", "update"], [3, "delay", "subitems", "select", "hide"]], template: function ContextMenuComponent_Template(rf, ctx) {
    if (rf & 1) {
      ɵɵtemplate(0, ContextMenuComponent_div_0_Template, 2, 1, "div", 0)(1, ContextMenuComponent_context_menu_item_1_Template, 2, 3, "context-menu-item", 1);
    }
    if (rf & 2) {
      ɵɵproperty("ngIf", ctx.searchBar);
      ɵɵadvance(1);
      ɵɵproperty("ngForOf", ctx.getItems());
    }
  }, dependencies: [NgForOf, NgIf, ContextMenuSearchComponent, ContextMenuItemComponent], styles: ["[_nghost-%COMP%]{display:block;padding:10px;width:120px;margin-top:-20px;margin-left:-60px}", ".block[_ngcontent-%COMP%]{display:block;color:#fff;padding:4px;border-bottom:1px solid rgba(69,103,255,.8);background-color:#6e88ffcc;cursor:pointer;width:100%;position:relative}.block[_ngcontent-%COMP%]:first-child{border-top-left-radius:5px;border-top-right-radius:5px}.block[_ngcontent-%COMP%]:last-child{border-bottom-left-radius:5px;border-bottom-right-radius:5px}.block[_ngcontent-%COMP%]:hover{background-color:#8299ffcc}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ContextMenuComponent, [{
    type: Component,
    args: [{ host: {
      "data-testid": "context-menu"
    }, template: '<div class="block" *ngIf="searchBar">\n  <context-menu-search [value]="filter" (update)="setFilter($event)"></context-menu-search>\n</div>\n\n<context-menu-item *ngFor="let item of getItems()" [delay]="delay" (select)="item.handler()" [subitems]="item.subitems"\n  (hide)="onHide()">\n  {{ item.label }}\n</context-menu-item>\n', styles: [":host{display:block;padding:10px;width:120px;margin-top:-20px;margin-left:-60px}\n", ".block{display:block;color:#fff;padding:4px;border-bottom:1px solid rgba(69,103,255,.8);background-color:#6e88ffcc;cursor:pointer;width:100%;position:relative}.block:first-child{border-top-left-radius:5px;border-top-right-radius:5px}.block:last-child{border-bottom-left-radius:5px;border-bottom-right-radius:5px}.block:hover{background-color:#8299ffcc}\n"] }]
  }], () => [{ type: ChangeDetectorRef }], { items: [{
    type: Input
  }], delay: [{
    type: Input
  }], searchBar: [{
    type: Input
  }], onHide: [{
    type: Input
  }], rendered: [{
    type: Input
  }], customAttribute: [{
    type: HostBinding,
    args: ["attr.rete-context-menu"]
  }], pointerover: [{
    type: HostListener,
    args: ["mouseover"]
  }], pointerleave: [{
    type: HostListener,
    args: ["mouseleave"]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(ContextMenuComponent, { className: "ContextMenuComponent", filePath: "presets/context-menu/components/menu/menu.component.ts", lineNumber: 14 });
})();
function setup$2(props) {
  const delay = typeof props?.delay === "undefined" ? 1e3 : props.delay;
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
function useDrag(translate, getPointer) {
  return {
    start(e) {
      let previous = __spreadValues({}, getPointer(e));
      function move(moveEvent) {
        const current = __spreadValues({}, getPointer(moveEvent));
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
var MiniViewportComponent = class _MiniViewportComponent {
  left;
  top;
  width;
  height;
  containerWidth;
  translate;
  drag = useDrag((dx, dy) => this.onDrag(dx, dy), (e) => ({ x: e.pageX, y: e.pageY }));
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
  static ɵfac = function MiniViewportComponent_Factory(t) {
    return new (t || _MiniViewportComponent)();
  };
  static ɵcmp = ɵɵdefineComponent({ type: _MiniViewportComponent, selectors: [["minimap-mini-viewport"]], hostAttrs: ["data-testid", "minimap-viewport"], hostVars: 8, hostBindings: function MiniViewportComponent_HostBindings(rf, ctx) {
    if (rf & 1) {
      ɵɵlistener("pointerdown", function MiniViewportComponent_pointerdown_HostBindingHandler($event) {
        return ctx.pointerdown($event);
      });
    }
    if (rf & 2) {
      ɵɵstyleProp("left", ctx.styleLeft)("top", ctx.styleTop)("width", ctx.styleWidth)("height", ctx.styleHeight);
    }
  }, inputs: { left: "left", top: "top", width: "width", height: "height", containerWidth: "containerWidth", translate: "translate" }, decls: 0, vars: 0, template: function MiniViewportComponent_Template(rf, ctx) {
  }, styles: ["[_nghost-%COMP%]{display:block;position:absolute;background:rgba(255,251,128,.32);border:1px solid #ffe52b}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MiniViewportComponent, [{
    type: Component,
    args: [{ selector: "minimap-mini-viewport", host: {
      "data-testid": "minimap-viewport"
    }, template: "", styles: [":host{display:block;position:absolute;background:rgba(255,251,128,.32);border:1px solid #ffe52b}\n"] }]
  }], null, { left: [{
    type: Input
  }], top: [{
    type: Input
  }], width: [{
    type: Input
  }], height: [{
    type: Input
  }], containerWidth: [{
    type: Input
  }], translate: [{
    type: Input
  }], styleLeft: [{
    type: HostBinding,
    args: ["style.left"]
  }], styleTop: [{
    type: HostBinding,
    args: ["style.top"]
  }], styleWidth: [{
    type: HostBinding,
    args: ["style.width"]
  }], styleHeight: [{
    type: HostBinding,
    args: ["style.height"]
  }], pointerdown: [{
    type: HostListener,
    args: ["pointerdown", ["$event"]]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(MiniViewportComponent, { className: "MiniViewportComponent", filePath: "presets/minimap/components/mini-viewport/mini-viewport.component.ts", lineNumber: 13 });
})();
var MiniNodeComponent = class _MiniNodeComponent {
  left;
  top;
  width;
  height;
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
  static ɵfac = function MiniNodeComponent_Factory(t) {
    return new (t || _MiniNodeComponent)();
  };
  static ɵcmp = ɵɵdefineComponent({ type: _MiniNodeComponent, selectors: [["minimap-mini-node"]], hostAttrs: ["data-testid", "minimap-node"], hostVars: 8, hostBindings: function MiniNodeComponent_HostBindings(rf, ctx) {
    if (rf & 2) {
      ɵɵstyleProp("left", ctx.styleLeft)("top", ctx.styleTop)("width", ctx.styleWidth)("height", ctx.styleHeight);
    }
  }, inputs: { left: "left", top: "top", width: "width", height: "height" }, decls: 0, vars: 0, template: function MiniNodeComponent_Template(rf, ctx) {
  }, styles: ["[_nghost-%COMP%]{display:block;position:absolute;background:rgba(110,136,255,.8);border:1px solid rgba(192,206,212,.6)}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MiniNodeComponent, [{
    type: Component,
    args: [{ selector: "minimap-mini-node", host: {
      "data-testid": "minimap-node"
    }, template: "", styles: [":host{display:block;position:absolute;background:rgba(110,136,255,.8);border:1px solid rgba(192,206,212,.6)}\n"] }]
  }], null, { left: [{
    type: Input
  }], top: [{
    type: Input
  }], width: [{
    type: Input
  }], height: [{
    type: Input
  }], styleLeft: [{
    type: HostBinding,
    args: ["style.left"]
  }], styleTop: [{
    type: HostBinding,
    args: ["style.top"]
  }], styleWidth: [{
    type: HostBinding,
    args: ["style.width"]
  }], styleHeight: [{
    type: HostBinding,
    args: ["style.height"]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(MiniNodeComponent, { className: "MiniNodeComponent", filePath: "presets/minimap/components/mini-node/mini-node.component.ts", lineNumber: 11 });
})();
function MinimapComponent_minimap_mini_node_0_Template(rf, ctx) {
  if (rf & 1) {
    ɵɵelement(0, "minimap-mini-node", 2);
  }
  if (rf & 2) {
    const node_r1 = ctx.$implicit;
    const ctx_r0 = ɵɵnextContext();
    ɵɵproperty("left", ctx_r0.scale(node_r1.left))("top", ctx_r0.scale(node_r1.top))("width", ctx_r0.scale(node_r1.width))("height", ctx_r0.scale(node_r1.height));
  }
}
var MinimapComponent = class _MinimapComponent {
  el;
  cdr;
  rendered;
  size;
  ratio;
  nodes;
  viewport;
  translate;
  point;
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
  constructor(el, cdr) {
    this.el = el;
    this.cdr = cdr;
    this.cdr.detach();
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
  static ɵfac = function MinimapComponent_Factory(t) {
    return new (t || _MinimapComponent)(ɵɵdirectiveInject(ElementRef), ɵɵdirectiveInject(ChangeDetectorRef));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _MinimapComponent, selectors: [["ng-component"]], hostAttrs: ["data-testid", "minimap"], hostVars: 4, hostBindings: function MinimapComponent_HostBindings(rf, ctx) {
    if (rf & 1) {
      ɵɵlistener("pointerdown", function MinimapComponent_pointerdown_HostBindingHandler($event) {
        return ctx.pointerdown($event);
      })("dblclick", function MinimapComponent_dblclick_HostBindingHandler($event) {
        return ctx.dblclick($event);
      });
    }
    if (rf & 2) {
      ɵɵstyleProp("width", ctx.width)("height", ctx.height);
    }
  }, inputs: { rendered: "rendered", size: "size", ratio: "ratio", nodes: "nodes", viewport: "viewport", translate: "translate", point: "point" }, features: [ɵɵNgOnChangesFeature], decls: 2, vars: 8, consts: [[3, "left", "top", "width", "height", 4, "ngFor", "ngForOf", "ngForTrackBy"], [3, "left", "top", "width", "height", "containerWidth", "translate"], [3, "left", "top", "width", "height"]], template: function MinimapComponent_Template(rf, ctx) {
    if (rf & 1) {
      ɵɵtemplate(0, MinimapComponent_minimap_mini_node_0_Template, 1, 4, "minimap-mini-node", 0);
      ɵɵelement(1, "minimap-mini-viewport", 1);
    }
    if (rf & 2) {
      ɵɵproperty("ngForOf", ctx.nodes)("ngForTrackBy", ctx.identifyMiniNode);
      ɵɵadvance(1);
      ɵɵproperty("left", ctx.viewport.left)("top", ctx.viewport.top)("width", ctx.viewport.width)("height", ctx.viewport.height)("containerWidth", ctx.el.nativeElement == null ? null : ctx.el.nativeElement.clientWidth)("translate", ctx.translate);
    }
  }, dependencies: [NgForOf, MiniViewportComponent, MiniNodeComponent], styles: ["[_nghost-%COMP%]{position:absolute;right:24px;bottom:24px;background:rgba(229,234,239,.65);padding:20px;overflow:hidden;border:1px solid #b1b7ff;border-radius:8px;box-sizing:border-box}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(MinimapComponent, [{
    type: Component,
    args: [{ host: {
      "data-testid": "minimap"
    }, template: '<minimap-mini-node *ngFor="let node of nodes; trackBy: identifyMiniNode" [left]="scale(node.left)"\n  [top]="scale(node.top)" [width]="scale(node.width)" [height]="scale(node.height)">\n\n</minimap-mini-node>\n<minimap-mini-viewport [left]="viewport.left" [top]="viewport.top" [width]="viewport.width" [height]="viewport.height"\n  [containerWidth]="el.nativeElement?.clientWidth" [translate]="translate"></minimap-mini-viewport>\n', styles: [":host{position:absolute;right:24px;bottom:24px;background:rgba(229,234,239,.65);padding:20px;overflow:hidden;border:1px solid #b1b7ff;border-radius:8px;box-sizing:border-box}\n"] }]
  }], () => [{ type: ElementRef }, { type: ChangeDetectorRef }], { rendered: [{
    type: Input
  }], size: [{
    type: Input
  }], ratio: [{
    type: Input
  }], nodes: [{
    type: Input
  }], viewport: [{
    type: Input
  }], translate: [{
    type: Input
  }], point: [{
    type: Input
  }], width: [{
    type: HostBinding,
    args: ["style.width"]
  }], height: [{
    type: HostBinding,
    args: ["style.height"]
  }], pointerdown: [{
    type: HostListener,
    args: ["pointerdown", ["$event"]]
  }], dblclick: [{
    type: HostListener,
    args: ["dblclick", ["$event"]]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(MinimapComponent, { className: "MinimapComponent", filePath: "presets/minimap/components/minimap/minimap.component.ts", lineNumber: 13 });
})();
function setup$1(props) {
  return {
    update(context) {
      if (context.data.type === "minimap") {
        return {
          nodes: context.data.nodes,
          size: props?.size || 200,
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
            size: props?.size || 200,
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
var pinSize = 20;
var PinComponent = class _PinComponent {
  cdr;
  position;
  selected;
  getPointer;
  menu = new EventEmitter();
  translate = new EventEmitter();
  down = new EventEmitter();
  drag = useDrag((dx, dy) => {
    this.translate.emit({ dx, dy });
  }, () => this.getPointer());
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
  constructor(cdr) {
    this.cdr = cdr;
  }
  ngOnChanges() {
  }
  static ɵfac = function PinComponent_Factory(t) {
    return new (t || _PinComponent)(ɵɵdirectiveInject(ChangeDetectorRef));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _PinComponent, selectors: [["reroute-pin"]], hostAttrs: ["data-testid", "pin"], hostVars: 6, hostBindings: function PinComponent_HostBindings(rf, ctx) {
    if (rf & 1) {
      ɵɵlistener("pointerdown", function PinComponent_pointerdown_HostBindingHandler($event) {
        return ctx.pointerdown($event);
      })("contextmenu", function PinComponent_contextmenu_HostBindingHandler($event) {
        return ctx.contextmenu($event);
      });
    }
    if (rf & 2) {
      ɵɵstyleProp("top", ctx.top)("left", ctx.left);
      ɵɵclassProp("selected", ctx._selected);
    }
  }, inputs: { position: "position", selected: "selected", getPointer: "getPointer" }, outputs: { menu: "menu", translate: "translate", down: "down" }, features: [ɵɵNgOnChangesFeature], decls: 0, vars: 0, template: function PinComponent_Template(rf, ctx) {
  }, styles: ["[_nghost-%COMP%]{display:block;width:20px;height:20px;box-sizing:border-box;background:steelblue;border:2px solid white;border-radius:20px;position:absolute}.selected[_nghost-%COMP%]{background:#ffd92c}"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(PinComponent, [{
    type: Component,
    args: [{ selector: "reroute-pin", template: "", host: {
      "data-testid": "pin"
    }, styles: [":host{display:block;width:20px;height:20px;box-sizing:border-box;background:steelblue;border:2px solid white;border-radius:20px;position:absolute}:host.selected{background:#ffd92c}\n"] }]
  }], () => [{ type: ChangeDetectorRef }], { position: [{
    type: Input
  }], selected: [{
    type: Input
  }], getPointer: [{
    type: Input
  }], menu: [{
    type: Output
  }], translate: [{
    type: Output
  }], down: [{
    type: Output
  }], _selected: [{
    type: HostBinding,
    args: ["class.selected"]
  }], top: [{
    type: HostBinding,
    args: ["style.top"]
  }], left: [{
    type: HostBinding,
    args: ["style.left"]
  }], pointerdown: [{
    type: HostListener,
    args: ["pointerdown", ["$event"]]
  }], contextmenu: [{
    type: HostListener,
    args: ["contextmenu", ["$event"]]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(PinComponent, { className: "PinComponent", filePath: "presets/reroute/components/pin/pin.component.ts", lineNumber: 15 });
})();
function PinsComponent_reroute_pin_0_Template(rf, ctx) {
  if (rf & 1) {
    const _r3 = ɵɵgetCurrentView();
    ɵɵelementStart(0, "reroute-pin", 1);
    ɵɵlistener("menu", function PinsComponent_reroute_pin_0_Template_reroute_pin_menu_0_listener() {
      const restoredCtx = ɵɵrestoreView(_r3);
      const pin_r1 = restoredCtx.$implicit;
      const ctx_r2 = ɵɵnextContext();
      return ɵɵresetView(ctx_r2.menu && ctx_r2.menu(pin_r1.id));
    })("translate", function PinsComponent_reroute_pin_0_Template_reroute_pin_translate_0_listener($event) {
      const restoredCtx = ɵɵrestoreView(_r3);
      const pin_r1 = restoredCtx.$implicit;
      const ctx_r4 = ɵɵnextContext();
      return ɵɵresetView(ctx_r4.translate && ctx_r4.translate(pin_r1.id, $event.dx, $event.dy));
    })("down", function PinsComponent_reroute_pin_0_Template_reroute_pin_down_0_listener() {
      const restoredCtx = ɵɵrestoreView(_r3);
      const pin_r1 = restoredCtx.$implicit;
      const ctx_r5 = ɵɵnextContext();
      return ɵɵresetView(ctx_r5.down && ctx_r5.down(pin_r1.id));
    });
    ɵɵelementEnd();
  }
  if (rf & 2) {
    const pin_r1 = ctx.$implicit;
    const ctx_r0 = ɵɵnextContext();
    ɵɵproperty("position", pin_r1.position)("selected", pin_r1.selected)("getPointer", ctx_r0.getPointer);
  }
}
var PinsComponent = class _PinsComponent {
  cdr;
  rendered;
  pins;
  down;
  translate;
  menu;
  getPointer;
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
  static ɵfac = function PinsComponent_Factory(t) {
    return new (t || _PinsComponent)(ɵɵdirectiveInject(ChangeDetectorRef));
  };
  static ɵcmp = ɵɵdefineComponent({ type: _PinsComponent, selectors: [["ng-component"]], inputs: { rendered: "rendered", pins: "pins", down: "down", translate: "translate", menu: "menu", getPointer: "getPointer" }, features: [ɵɵNgOnChangesFeature], decls: 1, vars: 2, consts: [[3, "position", "selected", "getPointer", "menu", "translate", "down", 4, "ngFor", "ngForOf", "ngForTrackBy"], [3, "position", "selected", "getPointer", "menu", "translate", "down"]], template: function PinsComponent_Template(rf, ctx) {
    if (rf & 1) {
      ɵɵtemplate(0, PinsComponent_reroute_pin_0_Template, 1, 3, "reroute-pin", 0);
    }
    if (rf & 2) {
      ɵɵproperty("ngForOf", ctx.pins)("ngForTrackBy", ctx.track);
    }
  }, dependencies: [NgForOf, PinComponent], encapsulation: 2 });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(PinsComponent, [{
    type: Component,
    args: [{ template: '<reroute-pin *ngFor="let pin of pins; trackBy: track" [position]="pin.position" [selected]="pin.selected"\n  (menu)="menu && menu(pin.id)" (translate)="translate && translate(pin.id, $event.dx, $event.dy)"\n  (down)="down && down(pin.id)" [getPointer]="getPointer"></reroute-pin>\n' }]
  }], () => [{ type: ChangeDetectorRef }], { rendered: [{
    type: Input
  }], pins: [{
    type: Input
  }], down: [{
    type: Input
  }], translate: [{
    type: Input
  }], menu: [{
    type: Input
  }], getPointer: [{
    type: Input
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && ɵsetClassDebugInfo(PinsComponent, { className: "PinsComponent", filePath: "presets/reroute/components/pins/pins.component.ts", lineNumber: 9 });
})();
function setup(props) {
  const getProps = () => ({
    menu: props?.contextMenu || (() => null),
    translate: props?.translate || (() => null),
    down: props?.pointerdown || (() => null)
  });
  return {
    update(context) {
      if (context.data.type === "reroute-pins") {
        return __spreadProps(__spreadValues({}, getProps()), {
          pins: context.data.data.pins
        });
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
          props: __spreadProps(__spreadValues({}, getProps()), {
            pins: context.data.data.pins,
            rendered,
            getPointer: () => area.area.pointer
          })
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
var ReteModule = class _ReteModule {
  static ɵfac = function ReteModule_Factory(t) {
    return new (t || _ReteModule)();
  };
  static ɵmod = ɵɵdefineNgModule({ type: _ReteModule });
  static ɵinj = ɵɵdefineInjector({ imports: [CommonModule] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ReteModule, [{
    type: NgModule,
    args: [{
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
      ]
    }]
  }], null, null);
})();
(function() {
  (typeof ngJitMode === "undefined" || ngJitMode) && ɵɵsetNgModuleScope(ReteModule, { declarations: [
    RefDirective,
    NodeComponent,
    ConnectionComponent,
    ConnectionWrapperComponent,
    SocketComponent,
    ControlComponent,
    ImpureKeyvaluePipe
  ], imports: [CommonModule], exports: [
    RefDirective,
    NodeComponent,
    ConnectionComponent,
    ConnectionWrapperComponent,
    SocketComponent,
    ControlComponent,
    ImpureKeyvaluePipe
  ] });
})();
var ReteContextMenuModule = class _ReteContextMenuModule {
  static ɵfac = function ReteContextMenuModule_Factory(t) {
    return new (t || _ReteContextMenuModule)();
  };
  static ɵmod = ɵɵdefineNgModule({ type: _ReteContextMenuModule });
  static ɵinj = ɵɵdefineInjector({ imports: [CommonModule] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ReteContextMenuModule, [{
    type: NgModule,
    args: [{
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
      ]
    }]
  }], null, null);
})();
(function() {
  (typeof ngJitMode === "undefined" || ngJitMode) && ɵɵsetNgModuleScope(ReteContextMenuModule, { declarations: [
    ContextMenuComponent,
    ContextMenuSearchComponent,
    ContextMenuItemComponent
  ], imports: [CommonModule], exports: [
    ContextMenuComponent,
    ContextMenuSearchComponent,
    ContextMenuItemComponent
  ] });
})();
var ReteMinimapModule = class _ReteMinimapModule {
  static ɵfac = function ReteMinimapModule_Factory(t) {
    return new (t || _ReteMinimapModule)();
  };
  static ɵmod = ɵɵdefineNgModule({ type: _ReteMinimapModule });
  static ɵinj = ɵɵdefineInjector({ imports: [CommonModule] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ReteMinimapModule, [{
    type: NgModule,
    args: [{
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
      ]
    }]
  }], null, null);
})();
(function() {
  (typeof ngJitMode === "undefined" || ngJitMode) && ɵɵsetNgModuleScope(ReteMinimapModule, { declarations: [
    MinimapComponent,
    MiniViewportComponent,
    MiniNodeComponent
  ], imports: [CommonModule], exports: [
    MinimapComponent,
    MiniViewportComponent,
    MiniNodeComponent
  ] });
})();
var ReteRerouteModule = class _ReteRerouteModule {
  static ɵfac = function ReteRerouteModule_Factory(t) {
    return new (t || _ReteRerouteModule)();
  };
  static ɵmod = ɵɵdefineNgModule({ type: _ReteRerouteModule });
  static ɵinj = ɵɵdefineInjector({ imports: [CommonModule] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(ReteRerouteModule, [{
    type: NgModule,
    args: [{
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
      ]
    }]
  }], null, null);
})();
(function() {
  (typeof ngJitMode === "undefined" || ngJitMode) && ɵɵsetNgModuleScope(ReteRerouteModule, { declarations: [
    PinsComponent,
    PinComponent
  ], imports: [CommonModule], exports: [
    PinsComponent,
    PinComponent
  ] });
})();
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
  params;
  presets = [];
  renderer;
  owners = /* @__PURE__ */ new WeakMap();
  /**
   * @constructor
   * @param params Plugin properties
   * @param params.injector Angular's Injector instance
   */
  constructor(params) {
    super("angular-render");
    this.params = params;
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
          return __spreadProps(__spreadValues({}, context), {
            data: __spreadProps(__spreadValues({}, context.data), {
              filled: true
            })
          });
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
  SocketComponent
};
/*! Bundled license information:

rete-render-utils/rete-render-utils.esm.js:
  (*!
  * rete-render-utils v2.0.2
  * (c) 2024 Vitaliy Stoliarov
  * Released under the MIT license.
  * *)

@angular/elements/fesm2022/elements.mjs:
  (**
   * @license Angular v17.3.12
   * (c) 2010-2024 Google LLC. https://angular.io/
   * License: MIT
   *)
*/
//# sourceMappingURL=rete-angular-plugin_17.js.map
