import {
  __commonJS,
  __toESM
} from "./chunk-TXDUYLVM.js";

// node_modules/@babel/runtime/helpers/typeof.js
var require_typeof = __commonJS({
  "node_modules/@babel/runtime/helpers/typeof.js"(exports, module) {
    function _typeof2(o) {
      "@babel/helpers - typeof";
      return module.exports = _typeof2 = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(o2) {
        return typeof o2;
      } : function(o2) {
        return o2 && "function" == typeof Symbol && o2.constructor === Symbol && o2 !== Symbol.prototype ? "symbol" : typeof o2;
      }, module.exports.__esModule = true, module.exports["default"] = module.exports, _typeof2(o);
    }
    module.exports = _typeof2, module.exports.__esModule = true, module.exports["default"] = module.exports;
  }
});

// node_modules/@babel/runtime/helpers/regeneratorRuntime.js
var require_regeneratorRuntime = __commonJS({
  "node_modules/@babel/runtime/helpers/regeneratorRuntime.js"(exports, module) {
    var _typeof2 = require_typeof()["default"];
    function _regeneratorRuntime2() {
      "use strict";
      module.exports = _regeneratorRuntime2 = function _regeneratorRuntime3() {
        return e;
      }, module.exports.__esModule = true, module.exports["default"] = module.exports;
      var t, e = {}, r = Object.prototype, n = r.hasOwnProperty, o = Object.defineProperty || function(t2, e2, r2) {
        t2[e2] = r2.value;
      }, i = "function" == typeof Symbol ? Symbol : {}, a = i.iterator || "@@iterator", c = i.asyncIterator || "@@asyncIterator", u = i.toStringTag || "@@toStringTag";
      function define(t2, e2, r2) {
        return Object.defineProperty(t2, e2, {
          value: r2,
          enumerable: true,
          configurable: true,
          writable: true
        }), t2[e2];
      }
      try {
        define({}, "");
      } catch (t2) {
        define = function define2(t3, e2, r2) {
          return t3[e2] = r2;
        };
      }
      function wrap(t2, e2, r2, n2) {
        var i2 = e2 && e2.prototype instanceof Generator ? e2 : Generator, a2 = Object.create(i2.prototype), c2 = new Context(n2 || []);
        return o(a2, "_invoke", {
          value: makeInvokeMethod(t2, r2, c2)
        }), a2;
      }
      function tryCatch(t2, e2, r2) {
        try {
          return {
            type: "normal",
            arg: t2.call(e2, r2)
          };
        } catch (t3) {
          return {
            type: "throw",
            arg: t3
          };
        }
      }
      e.wrap = wrap;
      var h = "suspendedStart", l = "suspendedYield", f = "executing", s = "completed", y = {};
      function Generator() {
      }
      function GeneratorFunction() {
      }
      function GeneratorFunctionPrototype() {
      }
      var p = {};
      define(p, a, function() {
        return this;
      });
      var d = Object.getPrototypeOf, v = d && d(d(values([])));
      v && v !== r && n.call(v, a) && (p = v);
      var g = GeneratorFunctionPrototype.prototype = Generator.prototype = Object.create(p);
      function defineIteratorMethods(t2) {
        ["next", "throw", "return"].forEach(function(e2) {
          define(t2, e2, function(t3) {
            return this._invoke(e2, t3);
          });
        });
      }
      function AsyncIterator(t2, e2) {
        function invoke(r3, o2, i2, a2) {
          var c2 = tryCatch(t2[r3], t2, o2);
          if ("throw" !== c2.type) {
            var u2 = c2.arg, h2 = u2.value;
            return h2 && "object" == _typeof2(h2) && n.call(h2, "__await") ? e2.resolve(h2.__await).then(function(t3) {
              invoke("next", t3, i2, a2);
            }, function(t3) {
              invoke("throw", t3, i2, a2);
            }) : e2.resolve(h2).then(function(t3) {
              u2.value = t3, i2(u2);
            }, function(t3) {
              return invoke("throw", t3, i2, a2);
            });
          }
          a2(c2.arg);
        }
        var r2;
        o(this, "_invoke", {
          value: function value(t3, n2) {
            function callInvokeWithMethodAndArg() {
              return new e2(function(e3, r3) {
                invoke(t3, n2, e3, r3);
              });
            }
            return r2 = r2 ? r2.then(callInvokeWithMethodAndArg, callInvokeWithMethodAndArg) : callInvokeWithMethodAndArg();
          }
        });
      }
      function makeInvokeMethod(e2, r2, n2) {
        var o2 = h;
        return function(i2, a2) {
          if (o2 === f) throw Error("Generator is already running");
          if (o2 === s) {
            if ("throw" === i2) throw a2;
            return {
              value: t,
              done: true
            };
          }
          for (n2.method = i2, n2.arg = a2; ; ) {
            var c2 = n2.delegate;
            if (c2) {
              var u2 = maybeInvokeDelegate(c2, n2);
              if (u2) {
                if (u2 === y) continue;
                return u2;
              }
            }
            if ("next" === n2.method) n2.sent = n2._sent = n2.arg;
            else if ("throw" === n2.method) {
              if (o2 === h) throw o2 = s, n2.arg;
              n2.dispatchException(n2.arg);
            } else "return" === n2.method && n2.abrupt("return", n2.arg);
            o2 = f;
            var p2 = tryCatch(e2, r2, n2);
            if ("normal" === p2.type) {
              if (o2 = n2.done ? s : l, p2.arg === y) continue;
              return {
                value: p2.arg,
                done: n2.done
              };
            }
            "throw" === p2.type && (o2 = s, n2.method = "throw", n2.arg = p2.arg);
          }
        };
      }
      function maybeInvokeDelegate(e2, r2) {
        var n2 = r2.method, o2 = e2.iterator[n2];
        if (o2 === t) return r2.delegate = null, "throw" === n2 && e2.iterator["return"] && (r2.method = "return", r2.arg = t, maybeInvokeDelegate(e2, r2), "throw" === r2.method) || "return" !== n2 && (r2.method = "throw", r2.arg = new TypeError("The iterator does not provide a '" + n2 + "' method")), y;
        var i2 = tryCatch(o2, e2.iterator, r2.arg);
        if ("throw" === i2.type) return r2.method = "throw", r2.arg = i2.arg, r2.delegate = null, y;
        var a2 = i2.arg;
        return a2 ? a2.done ? (r2[e2.resultName] = a2.value, r2.next = e2.nextLoc, "return" !== r2.method && (r2.method = "next", r2.arg = t), r2.delegate = null, y) : a2 : (r2.method = "throw", r2.arg = new TypeError("iterator result is not an object"), r2.delegate = null, y);
      }
      function pushTryEntry(t2) {
        var e2 = {
          tryLoc: t2[0]
        };
        1 in t2 && (e2.catchLoc = t2[1]), 2 in t2 && (e2.finallyLoc = t2[2], e2.afterLoc = t2[3]), this.tryEntries.push(e2);
      }
      function resetTryEntry(t2) {
        var e2 = t2.completion || {};
        e2.type = "normal", delete e2.arg, t2.completion = e2;
      }
      function Context(t2) {
        this.tryEntries = [{
          tryLoc: "root"
        }], t2.forEach(pushTryEntry, this), this.reset(true);
      }
      function values(e2) {
        if (e2 || "" === e2) {
          var r2 = e2[a];
          if (r2) return r2.call(e2);
          if ("function" == typeof e2.next) return e2;
          if (!isNaN(e2.length)) {
            var o2 = -1, i2 = function next() {
              for (; ++o2 < e2.length; ) if (n.call(e2, o2)) return next.value = e2[o2], next.done = false, next;
              return next.value = t, next.done = true, next;
            };
            return i2.next = i2;
          }
        }
        throw new TypeError(_typeof2(e2) + " is not iterable");
      }
      return GeneratorFunction.prototype = GeneratorFunctionPrototype, o(g, "constructor", {
        value: GeneratorFunctionPrototype,
        configurable: true
      }), o(GeneratorFunctionPrototype, "constructor", {
        value: GeneratorFunction,
        configurable: true
      }), GeneratorFunction.displayName = define(GeneratorFunctionPrototype, u, "GeneratorFunction"), e.isGeneratorFunction = function(t2) {
        var e2 = "function" == typeof t2 && t2.constructor;
        return !!e2 && (e2 === GeneratorFunction || "GeneratorFunction" === (e2.displayName || e2.name));
      }, e.mark = function(t2) {
        return Object.setPrototypeOf ? Object.setPrototypeOf(t2, GeneratorFunctionPrototype) : (t2.__proto__ = GeneratorFunctionPrototype, define(t2, u, "GeneratorFunction")), t2.prototype = Object.create(g), t2;
      }, e.awrap = function(t2) {
        return {
          __await: t2
        };
      }, defineIteratorMethods(AsyncIterator.prototype), define(AsyncIterator.prototype, c, function() {
        return this;
      }), e.AsyncIterator = AsyncIterator, e.async = function(t2, r2, n2, o2, i2) {
        void 0 === i2 && (i2 = Promise);
        var a2 = new AsyncIterator(wrap(t2, r2, n2, o2), i2);
        return e.isGeneratorFunction(r2) ? a2 : a2.next().then(function(t3) {
          return t3.done ? t3.value : a2.next();
        });
      }, defineIteratorMethods(g), define(g, u, "Generator"), define(g, a, function() {
        return this;
      }), define(g, "toString", function() {
        return "[object Generator]";
      }), e.keys = function(t2) {
        var e2 = Object(t2), r2 = [];
        for (var n2 in e2) r2.push(n2);
        return r2.reverse(), function next() {
          for (; r2.length; ) {
            var t3 = r2.pop();
            if (t3 in e2) return next.value = t3, next.done = false, next;
          }
          return next.done = true, next;
        };
      }, e.values = values, Context.prototype = {
        constructor: Context,
        reset: function reset(e2) {
          if (this.prev = 0, this.next = 0, this.sent = this._sent = t, this.done = false, this.delegate = null, this.method = "next", this.arg = t, this.tryEntries.forEach(resetTryEntry), !e2) for (var r2 in this) "t" === r2.charAt(0) && n.call(this, r2) && !isNaN(+r2.slice(1)) && (this[r2] = t);
        },
        stop: function stop() {
          this.done = true;
          var t2 = this.tryEntries[0].completion;
          if ("throw" === t2.type) throw t2.arg;
          return this.rval;
        },
        dispatchException: function dispatchException(e2) {
          if (this.done) throw e2;
          var r2 = this;
          function handle(n2, o3) {
            return a2.type = "throw", a2.arg = e2, r2.next = n2, o3 && (r2.method = "next", r2.arg = t), !!o3;
          }
          for (var o2 = this.tryEntries.length - 1; o2 >= 0; --o2) {
            var i2 = this.tryEntries[o2], a2 = i2.completion;
            if ("root" === i2.tryLoc) return handle("end");
            if (i2.tryLoc <= this.prev) {
              var c2 = n.call(i2, "catchLoc"), u2 = n.call(i2, "finallyLoc");
              if (c2 && u2) {
                if (this.prev < i2.catchLoc) return handle(i2.catchLoc, true);
                if (this.prev < i2.finallyLoc) return handle(i2.finallyLoc);
              } else if (c2) {
                if (this.prev < i2.catchLoc) return handle(i2.catchLoc, true);
              } else {
                if (!u2) throw Error("try statement without catch or finally");
                if (this.prev < i2.finallyLoc) return handle(i2.finallyLoc);
              }
            }
          }
        },
        abrupt: function abrupt(t2, e2) {
          for (var r2 = this.tryEntries.length - 1; r2 >= 0; --r2) {
            var o2 = this.tryEntries[r2];
            if (o2.tryLoc <= this.prev && n.call(o2, "finallyLoc") && this.prev < o2.finallyLoc) {
              var i2 = o2;
              break;
            }
          }
          i2 && ("break" === t2 || "continue" === t2) && i2.tryLoc <= e2 && e2 <= i2.finallyLoc && (i2 = null);
          var a2 = i2 ? i2.completion : {};
          return a2.type = t2, a2.arg = e2, i2 ? (this.method = "next", this.next = i2.finallyLoc, y) : this.complete(a2);
        },
        complete: function complete(t2, e2) {
          if ("throw" === t2.type) throw t2.arg;
          return "break" === t2.type || "continue" === t2.type ? this.next = t2.arg : "return" === t2.type ? (this.rval = this.arg = t2.arg, this.method = "return", this.next = "end") : "normal" === t2.type && e2 && (this.next = e2), y;
        },
        finish: function finish(t2) {
          for (var e2 = this.tryEntries.length - 1; e2 >= 0; --e2) {
            var r2 = this.tryEntries[e2];
            if (r2.finallyLoc === t2) return this.complete(r2.completion, r2.afterLoc), resetTryEntry(r2), y;
          }
        },
        "catch": function _catch(t2) {
          for (var e2 = this.tryEntries.length - 1; e2 >= 0; --e2) {
            var r2 = this.tryEntries[e2];
            if (r2.tryLoc === t2) {
              var n2 = r2.completion;
              if ("throw" === n2.type) {
                var o2 = n2.arg;
                resetTryEntry(r2);
              }
              return o2;
            }
          }
          throw Error("illegal catch attempt");
        },
        delegateYield: function delegateYield(e2, r2, n2) {
          return this.delegate = {
            iterator: values(e2),
            resultName: r2,
            nextLoc: n2
          }, "next" === this.method && (this.arg = t), y;
        }
      }, e;
    }
    module.exports = _regeneratorRuntime2, module.exports.__esModule = true, module.exports["default"] = module.exports;
  }
});

// node_modules/@babel/runtime/regenerator/index.js
var require_regenerator = __commonJS({
  "node_modules/@babel/runtime/regenerator/index.js"(exports, module) {
    var runtime = require_regeneratorRuntime()();
    module.exports = runtime;
    try {
      regeneratorRuntime = runtime;
    } catch (accidentalStrictMode) {
      if (typeof globalThis === "object") {
        globalThis.regeneratorRuntime = runtime;
      } else {
        Function("r", "regeneratorRuntime = r")(runtime);
      }
    }
  }
});

// node_modules/@babel/runtime/helpers/esm/asyncToGenerator.js
function asyncGeneratorStep(n, t, e, r, o, a, c) {
  try {
    var i = n[a](c), u = i.value;
  } catch (n2) {
    return void e(n2);
  }
  i.done ? t(u) : Promise.resolve(u).then(r, o);
}
function _asyncToGenerator(n) {
  return function() {
    var t = this, e = arguments;
    return new Promise(function(r, o) {
      var a = n.apply(t, e);
      function _next(n2) {
        asyncGeneratorStep(a, r, o, _next, _throw, "next", n2);
      }
      function _throw(n2) {
        asyncGeneratorStep(a, r, o, _next, _throw, "throw", n2);
      }
      _next(void 0);
    });
  };
}

// node_modules/@babel/runtime/helpers/esm/classCallCheck.js
function _classCallCheck(a, n) {
  if (!(a instanceof n)) throw new TypeError("Cannot call a class as a function");
}

// node_modules/@babel/runtime/helpers/esm/typeof.js
function _typeof(o) {
  "@babel/helpers - typeof";
  return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(o2) {
    return typeof o2;
  } : function(o2) {
    return o2 && "function" == typeof Symbol && o2.constructor === Symbol && o2 !== Symbol.prototype ? "symbol" : typeof o2;
  }, _typeof(o);
}

// node_modules/@babel/runtime/helpers/esm/toPrimitive.js
function toPrimitive(t, r) {
  if ("object" != _typeof(t) || !t) return t;
  var e = t[Symbol.toPrimitive];
  if (void 0 !== e) {
    var i = e.call(t, r || "default");
    if ("object" != _typeof(i)) return i;
    throw new TypeError("@@toPrimitive must return a primitive value.");
  }
  return ("string" === r ? String : Number)(t);
}

// node_modules/@babel/runtime/helpers/esm/toPropertyKey.js
function toPropertyKey(t) {
  var i = toPrimitive(t, "string");
  return "symbol" == _typeof(i) ? i : i + "";
}

// node_modules/@babel/runtime/helpers/esm/createClass.js
function _defineProperties(e, r) {
  for (var t = 0; t < r.length; t++) {
    var o = r[t];
    o.enumerable = o.enumerable || false, o.configurable = true, "value" in o && (o.writable = true), Object.defineProperty(e, toPropertyKey(o.key), o);
  }
}
function _createClass(e, r, t) {
  return r && _defineProperties(e.prototype, r), t && _defineProperties(e, t), Object.defineProperty(e, "prototype", {
    writable: false
  }), e;
}

// node_modules/@babel/runtime/helpers/esm/assertThisInitialized.js
function _assertThisInitialized(e) {
  if (void 0 === e) throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
  return e;
}

// node_modules/@babel/runtime/helpers/esm/possibleConstructorReturn.js
function _possibleConstructorReturn(t, e) {
  if (e && ("object" == _typeof(e) || "function" == typeof e)) return e;
  if (void 0 !== e) throw new TypeError("Derived constructors may only return object or undefined");
  return _assertThisInitialized(t);
}

// node_modules/@babel/runtime/helpers/esm/getPrototypeOf.js
function _getPrototypeOf(t) {
  return _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf.bind() : function(t2) {
    return t2.__proto__ || Object.getPrototypeOf(t2);
  }, _getPrototypeOf(t);
}

// node_modules/@babel/runtime/helpers/esm/setPrototypeOf.js
function _setPrototypeOf(t, e) {
  return _setPrototypeOf = Object.setPrototypeOf ? Object.setPrototypeOf.bind() : function(t2, e2) {
    return t2.__proto__ = e2, t2;
  }, _setPrototypeOf(t, e);
}

// node_modules/@babel/runtime/helpers/esm/inherits.js
function _inherits(t, e) {
  if ("function" != typeof e && null !== e) throw new TypeError("Super expression must either be null or a function");
  t.prototype = Object.create(e && e.prototype, {
    constructor: {
      value: t,
      writable: true,
      configurable: true
    }
  }), Object.defineProperty(t, "prototype", {
    writable: false
  }), e && _setPrototypeOf(t, e);
}

// node_modules/@babel/runtime/helpers/esm/defineProperty.js
function _defineProperty(e, r, t) {
  return (r = toPropertyKey(r)) in e ? Object.defineProperty(e, r, {
    value: t,
    enumerable: true,
    configurable: true,
    writable: true
  }) : e[r] = t, e;
}

// node_modules/rete/rete.esm.js
var import_regenerator = __toESM(require_regenerator());
function _createForOfIteratorHelper$1(r, e) {
  var t = "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"];
  if (!t) {
    if (Array.isArray(r) || (t = _unsupportedIterableToArray$1(r)) || e && r && "number" == typeof r.length) {
      t && (r = t);
      var _n = 0, F = function F2() {
      };
      return { s: F, n: function n() {
        return _n >= r.length ? { done: true } : { done: false, value: r[_n++] };
      }, e: function e2(r2) {
        throw r2;
      }, f: F };
    }
    throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
  }
  var o, a = true, u = false;
  return { s: function s() {
    t = t.call(r);
  }, n: function n() {
    var r2 = t.next();
    return a = r2.done, r2;
  }, e: function e2(r2) {
    u = true, o = r2;
  }, f: function f() {
    try {
      a || null == t["return"] || t["return"]();
    } finally {
      if (u) throw o;
    }
  } };
}
function _unsupportedIterableToArray$1(r, a) {
  if (r) {
    if ("string" == typeof r) return _arrayLikeToArray$1(r, a);
    var t = {}.toString.call(r).slice(8, -1);
    return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray$1(r, a) : void 0;
  }
}
function _arrayLikeToArray$1(r, a) {
  (null == a || a > r.length) && (a = r.length);
  for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e];
  return n;
}
function useHelper() {
  return {
    debug: function debug(_f) {
    }
  };
}
var Signal = function() {
  function Signal2() {
    _classCallCheck(this, Signal2);
    _defineProperty(this, "pipes", []);
  }
  return _createClass(Signal2, [{
    key: "addPipe",
    value: function addPipe(pipe) {
      this.pipes.push(pipe);
    }
  }, {
    key: "emit",
    value: function() {
      var _emit = _asyncToGenerator(import_regenerator.default.mark(function _callee(context) {
        var current, _iterator, _step, pipe;
        return import_regenerator.default.wrap(function _callee$(_context) {
          while (1) switch (_context.prev = _context.next) {
            case 0:
              current = context;
              _iterator = _createForOfIteratorHelper$1(this.pipes);
              _context.prev = 2;
              _iterator.s();
            case 4:
              if ((_step = _iterator.n()).done) {
                _context.next = 13;
                break;
              }
              pipe = _step.value;
              _context.next = 8;
              return pipe(current);
            case 8:
              current = _context.sent;
              if (!(typeof current === "undefined")) {
                _context.next = 11;
                break;
              }
              return _context.abrupt("return");
            case 11:
              _context.next = 4;
              break;
            case 13:
              _context.next = 18;
              break;
            case 15:
              _context.prev = 15;
              _context.t0 = _context["catch"](2);
              _iterator.e(_context.t0);
            case 18:
              _context.prev = 18;
              _iterator.f();
              return _context.finish(18);
            case 21:
              return _context.abrupt("return", current);
            case 22:
            case "end":
              return _context.stop();
          }
        }, _callee, this, [[2, 15, 18, 21]]);
      }));
      function emit(_x) {
        return _emit.apply(this, arguments);
      }
      return emit;
    }()
  }]);
}();
var Scope = function() {
  function Scope2(name) {
    _classCallCheck(this, Scope2);
    _defineProperty(this, "signal", new Signal());
    this.name = name;
  }
  return _createClass(Scope2, [{
    key: "addPipe",
    value: function addPipe(middleware) {
      this.signal.addPipe(middleware);
    }
  }, {
    key: "use",
    value: function use(scope) {
      if (!(scope instanceof Scope2)) throw new Error("cannot use non-Scope instance");
      scope.setParent(this);
      this.addPipe(function(context) {
        return scope.signal.emit(context);
      });
      return useHelper();
    }
  }, {
    key: "setParent",
    value: function setParent(scope) {
      this.parent = scope;
    }
  }, {
    key: "emit",
    value: function emit(context) {
      return this.signal.emit(context);
    }
  }, {
    key: "hasParent",
    value: function hasParent() {
      return Boolean(this.parent);
    }
  }, {
    key: "parentScope",
    value: function parentScope(type) {
      if (!this.parent) throw new Error("cannot find parent");
      if (type && this.parent instanceof type) return this.parent;
      if (type) throw new Error("actual parent is not instance of type");
      return this.parent;
    }
  }]);
}();
function _createForOfIteratorHelper(r, e) {
  var t = "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"];
  if (!t) {
    if (Array.isArray(r) || (t = _unsupportedIterableToArray(r)) || e && r && "number" == typeof r.length) {
      t && (r = t);
      var _n = 0, F = function F2() {
      };
      return { s: F, n: function n() {
        return _n >= r.length ? { done: true } : { done: false, value: r[_n++] };
      }, e: function e2(r2) {
        throw r2;
      }, f: F };
    }
    throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
  }
  var o, a = true, u = false;
  return { s: function s() {
    t = t.call(r);
  }, n: function n() {
    var r2 = t.next();
    return a = r2.done, r2;
  }, e: function e2(r2) {
    u = true, o = r2;
  }, f: function f() {
    try {
      a || null == t["return"] || t["return"]();
    } finally {
      if (u) throw o;
    }
  } };
}
function _unsupportedIterableToArray(r, a) {
  if (r) {
    if ("string" == typeof r) return _arrayLikeToArray(r, a);
    var t = {}.toString.call(r).slice(8, -1);
    return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0;
  }
}
function _arrayLikeToArray(r, a) {
  (null == a || a > r.length) && (a = r.length);
  for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e];
  return n;
}
function _callSuper$1(t, o, e) {
  return o = _getPrototypeOf(o), _possibleConstructorReturn(t, _isNativeReflectConstruct$1() ? Reflect.construct(o, e || [], _getPrototypeOf(t).constructor) : o.apply(t, e));
}
function _isNativeReflectConstruct$1() {
  try {
    var t = !Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function() {
    }));
  } catch (t2) {
  }
  return (_isNativeReflectConstruct$1 = function _isNativeReflectConstruct2() {
    return !!t;
  })();
}
var NodeEditor = function(_Scope) {
  function NodeEditor2() {
    var _this;
    _classCallCheck(this, NodeEditor2);
    _this = _callSuper$1(this, NodeEditor2, ["NodeEditor"]);
    _defineProperty(_this, "nodes", []);
    _defineProperty(_this, "connections", []);
    return _this;
  }
  _inherits(NodeEditor2, _Scope);
  return _createClass(NodeEditor2, [{
    key: "getNode",
    value: function getNode(id) {
      return this.nodes.find(function(node) {
        return node.id === id;
      });
    }
    /**
     * Get all nodes
     * @returns Copy of array with nodes
     */
  }, {
    key: "getNodes",
    value: function getNodes() {
      return this.nodes.slice();
    }
    /**
     * Get all connections
     * @returns Copy of array with onnections
     */
  }, {
    key: "getConnections",
    value: function getConnections() {
      return this.connections.slice();
    }
    /**
     * Get a connection by id
     * @param id - The connection id
     * @returns The connection or undefined
     */
  }, {
    key: "getConnection",
    value: function getConnection(id) {
      return this.connections.find(function(connection) {
        return connection.id === id;
      });
    }
    /**
     * Add a node
     * @param data - The node data
     * @returns Whether the node was added
     * @throws If the node has already been added
     * @emits nodecreate
     * @emits nodecreated
     */
  }, {
    key: "addNode",
    value: function() {
      var _addNode = _asyncToGenerator(import_regenerator.default.mark(function _callee(data) {
        return import_regenerator.default.wrap(function _callee$(_context) {
          while (1) switch (_context.prev = _context.next) {
            case 0:
              if (!this.getNode(data.id)) {
                _context.next = 2;
                break;
              }
              throw new Error("node has already been added");
            case 2:
              _context.next = 4;
              return this.emit({
                type: "nodecreate",
                data
              });
            case 4:
              if (_context.sent) {
                _context.next = 6;
                break;
              }
              return _context.abrupt("return", false);
            case 6:
              this.nodes.push(data);
              _context.next = 9;
              return this.emit({
                type: "nodecreated",
                data
              });
            case 9:
              return _context.abrupt("return", true);
            case 10:
            case "end":
              return _context.stop();
          }
        }, _callee, this);
      }));
      function addNode(_x) {
        return _addNode.apply(this, arguments);
      }
      return addNode;
    }()
  }, {
    key: "addConnection",
    value: function() {
      var _addConnection = _asyncToGenerator(import_regenerator.default.mark(function _callee2(data) {
        return import_regenerator.default.wrap(function _callee2$(_context2) {
          while (1) switch (_context2.prev = _context2.next) {
            case 0:
              if (!this.getConnection(data.id)) {
                _context2.next = 2;
                break;
              }
              throw new Error("connection has already been added");
            case 2:
              _context2.next = 4;
              return this.emit({
                type: "connectioncreate",
                data
              });
            case 4:
              if (_context2.sent) {
                _context2.next = 6;
                break;
              }
              return _context2.abrupt("return", false);
            case 6:
              this.connections.push(data);
              _context2.next = 9;
              return this.emit({
                type: "connectioncreated",
                data
              });
            case 9:
              return _context2.abrupt("return", true);
            case 10:
            case "end":
              return _context2.stop();
          }
        }, _callee2, this);
      }));
      function addConnection(_x2) {
        return _addConnection.apply(this, arguments);
      }
      return addConnection;
    }()
  }, {
    key: "removeNode",
    value: function() {
      var _removeNode = _asyncToGenerator(import_regenerator.default.mark(function _callee3(id) {
        var node, index;
        return import_regenerator.default.wrap(function _callee3$(_context3) {
          while (1) switch (_context3.prev = _context3.next) {
            case 0:
              node = this.nodes.find(function(n) {
                return n.id === id;
              });
              if (node) {
                _context3.next = 3;
                break;
              }
              throw new Error("cannot find node");
            case 3:
              _context3.next = 5;
              return this.emit({
                type: "noderemove",
                data: node
              });
            case 5:
              if (_context3.sent) {
                _context3.next = 7;
                break;
              }
              return _context3.abrupt("return", false);
            case 7:
              index = this.nodes.indexOf(node);
              this.nodes.splice(index, 1);
              _context3.next = 11;
              return this.emit({
                type: "noderemoved",
                data: node
              });
            case 11:
              return _context3.abrupt("return", true);
            case 12:
            case "end":
              return _context3.stop();
          }
        }, _callee3, this);
      }));
      function removeNode(_x3) {
        return _removeNode.apply(this, arguments);
      }
      return removeNode;
    }()
  }, {
    key: "removeConnection",
    value: function() {
      var _removeConnection = _asyncToGenerator(import_regenerator.default.mark(function _callee4(id) {
        var connection, index;
        return import_regenerator.default.wrap(function _callee4$(_context4) {
          while (1) switch (_context4.prev = _context4.next) {
            case 0:
              connection = this.connections.find(function(c) {
                return c.id === id;
              });
              if (connection) {
                _context4.next = 3;
                break;
              }
              throw new Error("cannot find connection");
            case 3:
              _context4.next = 5;
              return this.emit({
                type: "connectionremove",
                data: connection
              });
            case 5:
              if (_context4.sent) {
                _context4.next = 7;
                break;
              }
              return _context4.abrupt("return", false);
            case 7:
              index = this.connections.indexOf(connection);
              this.connections.splice(index, 1);
              _context4.next = 11;
              return this.emit({
                type: "connectionremoved",
                data: connection
              });
            case 11:
              return _context4.abrupt("return", true);
            case 12:
            case "end":
              return _context4.stop();
          }
        }, _callee4, this);
      }));
      function removeConnection(_x4) {
        return _removeConnection.apply(this, arguments);
      }
      return removeConnection;
    }()
  }, {
    key: "clear",
    value: function() {
      var _clear = _asyncToGenerator(import_regenerator.default.mark(function _callee5() {
        var _iterator, _step, connection, _iterator2, _step2, node;
        return import_regenerator.default.wrap(function _callee5$(_context5) {
          while (1) switch (_context5.prev = _context5.next) {
            case 0:
              _context5.next = 2;
              return this.emit({
                type: "clear"
              });
            case 2:
              if (_context5.sent) {
                _context5.next = 6;
                break;
              }
              _context5.next = 5;
              return this.emit({
                type: "clearcancelled"
              });
            case 5:
              return _context5.abrupt("return", false);
            case 6:
              _iterator = _createForOfIteratorHelper(this.connections.slice());
              _context5.prev = 7;
              _iterator.s();
            case 9:
              if ((_step = _iterator.n()).done) {
                _context5.next = 15;
                break;
              }
              connection = _step.value;
              _context5.next = 13;
              return this.removeConnection(connection.id);
            case 13:
              _context5.next = 9;
              break;
            case 15:
              _context5.next = 20;
              break;
            case 17:
              _context5.prev = 17;
              _context5.t0 = _context5["catch"](7);
              _iterator.e(_context5.t0);
            case 20:
              _context5.prev = 20;
              _iterator.f();
              return _context5.finish(20);
            case 23:
              _iterator2 = _createForOfIteratorHelper(this.nodes.slice());
              _context5.prev = 24;
              _iterator2.s();
            case 26:
              if ((_step2 = _iterator2.n()).done) {
                _context5.next = 32;
                break;
              }
              node = _step2.value;
              _context5.next = 30;
              return this.removeNode(node.id);
            case 30:
              _context5.next = 26;
              break;
            case 32:
              _context5.next = 37;
              break;
            case 34:
              _context5.prev = 34;
              _context5.t1 = _context5["catch"](24);
              _iterator2.e(_context5.t1);
            case 37:
              _context5.prev = 37;
              _iterator2.f();
              return _context5.finish(37);
            case 40:
              _context5.next = 42;
              return this.emit({
                type: "cleared"
              });
            case 42:
              return _context5.abrupt("return", true);
            case 43:
            case "end":
              return _context5.stop();
          }
        }, _callee5, this, [[7, 17, 20, 23], [24, 34, 37, 40]]);
      }));
      function clear() {
        return _clear.apply(this, arguments);
      }
      return clear;
    }()
  }]);
}(Scope);
var crypto = globalThis.crypto;
function getUID() {
  if ("randomBytes" in crypto) {
    return crypto.randomBytes(8).toString("hex");
  }
  var bytes = crypto.getRandomValues(new Uint8Array(8));
  var array = Array.from(bytes);
  var hexPairs = array.map(function(b) {
    return b.toString(16).padStart(2, "0");
  });
  return hexPairs.join("");
}
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
var Socket = _createClass(
  /**
   * @constructor
   * @param name Name of the socket
   */
  function Socket2(name) {
    _classCallCheck(this, Socket2);
    this.name = name;
  }
);
var Port = _createClass(
  /**
   * Port id, unique string generated by `getUID` function
   */
  /**
   * Port index, used for sorting ports. Default is `0`
   */
  /**
   * @constructor
   * @param socket Socket instance
   * @param label Label of the port
   * @param multipleConnections Whether the output port can have multiple connections
   */
  function Port2(socket, label, multipleConnections) {
    _classCallCheck(this, Port2);
    this.socket = socket;
    this.label = label;
    this.multipleConnections = multipleConnections;
    this.id = getUID();
  }
);
var Input = function(_Port) {
  function Input2(socket, label, multipleConnections) {
    var _this;
    _classCallCheck(this, Input2);
    _this = _callSuper(this, Input2, [socket, label, multipleConnections]);
    _defineProperty(_this, "control", null);
    _defineProperty(_this, "showControl", true);
    _this.socket = socket;
    _this.label = label;
    _this.multipleConnections = multipleConnections;
    return _this;
  }
  _inherits(Input2, _Port);
  return _createClass(Input2, [{
    key: "addControl",
    value: function addControl(control) {
      if (this.control) throw new Error("control already added for this input");
      this.control = control;
    }
    /**
     * Remove control from the input port
     */
  }, {
    key: "removeControl",
    value: function removeControl() {
      this.control = null;
    }
  }]);
}(Port);
var Output = function(_Port2) {
  function Output2(socket, label, multipleConnections) {
    _classCallCheck(this, Output2);
    return _callSuper(this, Output2, [socket, label, multipleConnections !== false]);
  }
  _inherits(Output2, _Port2);
  return _createClass(Output2);
}(Port);
var Control = _createClass(
  /**
   * Control id, unique string generated by `getUID` function
   */
  /**
   * Control index, used for sorting controls. Default is `0`
   */
  function Control2() {
    _classCallCheck(this, Control2);
    this.id = getUID();
  }
);
var InputControl = function(_Control) {
  function InputControl2(type, options) {
    var _options$readonly;
    var _this2;
    _classCallCheck(this, InputControl2);
    _this2 = _callSuper(this, InputControl2);
    _this2.type = type;
    _this2.options = options;
    _this2.id = getUID();
    _this2.readonly = (_options$readonly = options === null || options === void 0 ? void 0 : options.readonly) !== null && _options$readonly !== void 0 ? _options$readonly : false;
    if (typeof (options === null || options === void 0 ? void 0 : options.initial) !== "undefined") _this2.value = options.initial;
    return _this2;
  }
  _inherits(InputControl2, _Control);
  return _createClass(InputControl2, [{
    key: "setValue",
    value: function setValue(value) {
      var _this$options;
      this.value = value;
      if ((_this$options = this.options) !== null && _this$options !== void 0 && _this$options.change) this.options.change(value);
    }
  }]);
}(Control);
var Node = function() {
  function Node2(label) {
    _classCallCheck(this, Node2);
    _defineProperty(this, "inputs", {});
    _defineProperty(this, "outputs", {});
    _defineProperty(this, "controls", {});
    this.label = label;
    this.id = getUID();
  }
  return _createClass(Node2, [{
    key: "hasInput",
    value: function hasInput(key) {
      return Object.prototype.hasOwnProperty.call(this.inputs, key);
    }
  }, {
    key: "addInput",
    value: function addInput(key, input) {
      if (this.hasInput(key)) throw new Error("input with key '".concat(String(key), "' already added"));
      Object.defineProperty(this.inputs, key, {
        value: input,
        enumerable: true,
        configurable: true
      });
    }
  }, {
    key: "removeInput",
    value: function removeInput(key) {
      delete this.inputs[key];
    }
  }, {
    key: "hasOutput",
    value: function hasOutput(key) {
      return Object.prototype.hasOwnProperty.call(this.outputs, key);
    }
  }, {
    key: "addOutput",
    value: function addOutput(key, output) {
      if (this.hasOutput(key)) throw new Error("output with key '".concat(String(key), "' already added"));
      Object.defineProperty(this.outputs, key, {
        value: output,
        enumerable: true,
        configurable: true
      });
    }
  }, {
    key: "removeOutput",
    value: function removeOutput(key) {
      delete this.outputs[key];
    }
  }, {
    key: "hasControl",
    value: function hasControl(key) {
      return Object.prototype.hasOwnProperty.call(this.controls, key);
    }
  }, {
    key: "addControl",
    value: function addControl(key, control) {
      if (this.hasControl(key)) throw new Error("control with key '".concat(String(key), "' already added"));
      Object.defineProperty(this.controls, key, {
        value: control,
        enumerable: true,
        configurable: true
      });
    }
  }, {
    key: "removeControl",
    value: function removeControl(key) {
      delete this.controls[key];
    }
  }]);
}();
var Connection = _createClass(
  /**
   * Connection id, unique string generated by `getUID` function
   */
  /**
   * Source node id
   */
  /**
   * Target node id
   */
  /**
   * @constructor
   * @param source Source node instance
   * @param sourceOutput Source node output key
   * @param target Target node instance
   * @param targetInput Target node input key
   */
  function Connection2(source, sourceOutput, target, targetInput) {
    _classCallCheck(this, Connection2);
    this.sourceOutput = sourceOutput;
    this.targetInput = targetInput;
    if (!source.outputs[sourceOutput]) {
      throw new Error("source node doesn't have output with a key ".concat(String(sourceOutput)));
    }
    if (!target.inputs[targetInput]) {
      throw new Error("target node doesn't have input with a key ".concat(String(targetInput)));
    }
    this.id = getUID();
    this.source = source.id;
    this.target = target.id;
  }
);
var classic = Object.freeze({
  __proto__: null,
  Socket,
  Port,
  Input,
  Output,
  Control,
  InputControl,
  Node,
  Connection
});

export {
  _asyncToGenerator,
  _classCallCheck,
  _typeof,
  _createClass,
  _possibleConstructorReturn,
  _getPrototypeOf,
  _inherits,
  _defineProperty,
  require_regenerator,
  Signal,
  Scope,
  NodeEditor,
  getUID,
  classic
};
/*! Bundled license information:

@babel/runtime/helpers/regeneratorRuntime.js:
  (*! regenerator-runtime -- Copyright (c) 2014-present, Facebook, Inc. -- license (MIT): https://github.com/facebook/regenerator/blob/main/LICENSE *)

rete/rete.esm.js:
  (*!
  * rete v2.0.5
  * (c) 2025 Vitaliy Stoliarov
  * Released under the MIT license.
  * *)
*/
//# sourceMappingURL=chunk-PXWGCFSP.js.map
