import {
  _getPrototypeOf
} from "./chunk-PXWGCFSP.js";

// node_modules/@babel/runtime/helpers/esm/superPropBase.js
function _superPropBase(t, o) {
  for (; !{}.hasOwnProperty.call(t, o) && null !== (t = _getPrototypeOf(t)); ) ;
  return t;
}

// node_modules/@babel/runtime/helpers/esm/get.js
function _get() {
  return _get = "undefined" != typeof Reflect && Reflect.get ? Reflect.get.bind() : function(e, t, r) {
    var p = _superPropBase(e, t);
    if (p) {
      var n = Object.getOwnPropertyDescriptor(p, t);
      return n.get ? n.get.call(arguments.length < 3 ? e : r) : n.value;
    }
  }, _get.apply(null, arguments);
}

export {
  _get
};
//# sourceMappingURL=chunk-K5PC3ORH.js.map
