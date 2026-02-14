/**
 * Overview: Maps Lucide/Feather icon names to Unicode symbols for lightweight icon rendering.
 * Architecture: Shared utility (Section 3.2)
 * Dependencies: none
 * Concepts: Icon name to Unicode mapping, fallback symbol
 */

const ICON_MAP: Record<string, string> = {
  // Infrastructure
  'server': '\u2630',       // ☰
  'cloud': '\u2601',        // ☁
  'database': '\u26C1',     // ⛁
  'hard-drive': '\u2395',   // ⎕
  'cpu': '\u2338',          // ⌸
  'monitor': '\u25A3',      // ▣
  'terminal': '\u2588',     // █ → use >_
  'box': '\u25A1',          // □
  'archive': '\u25A4',      // ▤
  'layers': '\u25A7',       // ▧
  'grid': '\u25A6',         // ▦
  'package': '\u25A8',      // ▨
  'inbox': '\u25AB',        // ▫
  'folder': '\u25B7',       // ▷
  'save': '\u25C6',         // ◆

  // Networking
  'globe': '\u25CE',        // ◎
  'link': '\u26D3',         // ⛓
  'share-2': '\u2B82',      // ⮂
  'at-sign': '\u0040',      // @
  'zap': '\u26A1',          // ⚡

  // Security
  'shield': '\u25C8',       // ◈
  'lock': '\u26BF',         // ⚿
  'key': '\u26BF',          // ⚿
  'user-check': '\u2611',   // ☑

  // Monitoring / Management
  'activity': '\u2248',     // ≈
  'bar-chart-2': '\u2261',  // ≡
  'trending-up': '\u2197',  // ↗
  'bell': '\u25D5',         // ◕
  'alert-triangle': '\u26A0', // ⚠
  'headphones': '\u260E',   // ☎

  // Documents / Data
  'file-text': '\u25A2',    // ▢
  'list': '\u2630',         // ☰
  'layout': '\u25EB',       // ◫

  // Version control / DevOps
  'git-branch': '\u2442',   // ⑂

  // Business
  'briefcase': '\u25A0',    // ■
  'award': '\u2605',        // ★
  'users': '\u2616',        // ☖

  // Services
  'settings': '\u2699',     // ⚙
  'gear': '\u2699',         // ⚙
};

/**
 * Converts a Lucide/Feather icon name to a Unicode symbol.
 * Returns the symbol string, or a default fallback.
 */
export function iconNameToSymbol(iconName: string | null | undefined): string {
  if (!iconName) return '\u25C7'; // ◇ default
  // If it already looks like an HTML entity or Unicode char, pass through
  if (iconName.startsWith('&#') || iconName.length <= 2) return iconName;
  return ICON_MAP[iconName] || '\u25C7'; // ◇ fallback
}
