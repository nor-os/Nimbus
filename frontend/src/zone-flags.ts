/**
 * Overview: Pre-zone.js patches to prevent Zone.js event-wrapping errors.
 * Architecture: Polyfills loaded before zone.js (Section 3.2)
 * Dependencies: None (must be side-effect-only, no imports)
 * Concepts: Zone.js keyboard event patching, getModifierState polyfill
 */

// Zone.js wraps KeyboardEvent and calls getModifierState on the wrapped copy.
// Some environments (or synthetic events from Monaco/Rete.js) lack this method,
// causing "t.getModifierState is not a function". Ensure it exists before Zone.js loads.
if (typeof KeyboardEvent !== 'undefined' && !KeyboardEvent.prototype.getModifierState) {
  KeyboardEvent.prototype.getModifierState = function (key: string): boolean {
    const map: Record<string, string> = {
      Alt: 'altKey',
      Control: 'ctrlKey',
      Meta: 'metaKey',
      Shift: 'shiftKey',
    };
    return !!(this as any)[map[key] || ''];
  };
}
