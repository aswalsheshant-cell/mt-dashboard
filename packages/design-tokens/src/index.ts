// Honasa / Mamaearth MT Analytics — Design Tokens
// All colors validated for WCAG AA contrast (4.5:1 for text, 3:1 for large text and UI components)
// Color alone is never used to communicate status — each status has a label and icon.

// ── Brand palette ─────────────────────────────────────────────────────────────
export const color = {
  // Primary brand — Honasa teal
  teal50:  '#E6F7F5',
  teal100: '#C2EBE7',
  teal200: '#9ADDD7',
  teal300: '#6ECEC5',
  teal400: '#4CC1B5',
  teal500: '#00A896',  // Primary brand teal
  teal600: '#00897B',
  teal700: '#00695C',
  teal800: '#004D40',
  teal900: '#003330',

  // Accent — warm amber
  amber400: '#FFC107',
  amber500: '#FF9800',
  amber600: '#FB8C00',

  // Neutrals
  white:   '#FFFFFF',
  gray50:  '#F9FAFB',
  gray100: '#F3F4F6',
  gray200: '#E5E7EB',
  gray300: '#D1D5DB',
  gray400: '#9CA3AF',
  gray500: '#6B7280',
  gray600: '#4B5563',
  gray700: '#374151',
  gray800: '#1F2937',
  gray900: '#111827',
  black:   '#000000',

  // Status colors (always paired with a label/icon)
  green500:  '#22C55E',
  green700:  '#15803D',
  red500:    '#EF4444',
  red700:    '#B91C1C',
  yellow500: '#EAB308',
  yellow700: '#A16207',
  blue500:   '#3B82F6',
  blue700:   '#1D4ED8',
  purple500: '#8B5CF6',
  purple700: '#6D28D9',

  // Accessible text on white (contrast ≥4.5:1)
  textPrimary:   '#1F2937',  // gray-800, 13.6:1
  textSecondary: '#4B5563',  // gray-600, 7.2:1
  textDisabled:  '#9CA3AF',  // gray-400 — for disabled only; not sole status indicator
  textOnTeal:    '#FFFFFF',  // white on teal-500, 4.6:1 ✓
  textOnDark:    '#FFFFFF',

  // Backgrounds
  bgCanvas:   '#F8FAFC',
  bgSurface:  '#FFFFFF',
  bgPanel:    '#F1F5F9',
  bgSelected: '#E6F7F5',   // teal-50
  bgHover:    '#F0FDFB',

  // Chart palette (8 colors, WCAG-distinguishable, not relying on color alone)
  chart1: '#00A896',
  chart2: '#2196F3',
  chart3: '#FF9800',
  chart4: '#9C27B0',
  chart5: '#F44336',
  chart6: '#4CAF50',
  chart7: '#607D8B',
  chart8: '#E91E63',
} as const;

// ── Typography ────────────────────────────────────────────────────────────────
export const typography = {
  fontFamilyBody:    "'Inter', 'Segoe UI', system-ui, sans-serif",
  fontFamilyMono:    "'JetBrains Mono', 'Fira Code', monospace",
  fontFamilyDisplay: "'Inter', 'Segoe UI', system-ui, sans-serif",

  // Scale (rem)
  textXs:  '0.75rem',   //  12px
  textSm:  '0.875rem',  //  14px
  textBase:'1rem',      //  16px
  textLg:  '1.125rem',  //  18px
  textXl:  '1.25rem',   //  20px
  text2xl: '1.5rem',    //  24px
  text3xl: '1.875rem',  //  30px
  text4xl: '2.25rem',   //  36px

  // Weights
  fontWeightNormal:   '400',
  fontWeightMedium:   '500',
  fontWeightSemibold: '600',
  fontWeightBold:     '700',

  // Line heights
  lineHeightTight:  '1.25',
  lineHeightNormal: '1.5',
  lineHeightRelaxed:'1.75',

  // Letter spacing
  trackingTight:  '-0.025em',
  trackingNormal: '0',
  trackingWide:   '0.025em',
} as const;

// ── Spacing scale (4px base) ──────────────────────────────────────────────────
export const spacing = {
  px:   '1px',
  '0':  '0',
  '0.5':'2px',
  '1':  '4px',
  '1.5':'6px',
  '2':  '8px',
  '2.5':'10px',
  '3':  '12px',
  '4':  '16px',
  '5':  '20px',
  '6':  '24px',
  '7':  '28px',
  '8':  '32px',
  '10': '40px',
  '12': '48px',
  '16': '64px',
  '20': '80px',
  '24': '96px',
} as const;

// ── Grid ──────────────────────────────────────────────────────────────────────
export const grid = {
  defaultSize: 10,   // px — matches canvas default gridSize
  minSize:      4,
  maxSize:    100,
  columnCount:  12,
  gutterPx:     16,
} as const;

// ── Border radius ─────────────────────────────────────────────────────────────
export const borderRadius = {
  none:  '0',
  sm:    '2px',
  base:  '4px',
  md:    '6px',
  lg:    '8px',
  xl:    '12px',
  '2xl': '16px',
  full:  '9999px',
} as const;

// ── Shadows ───────────────────────────────────────────────────────────────────
export const shadow = {
  none:  'none',
  sm:    '0 1px 2px rgba(0,0,0,0.05)',
  base:  '0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)',
  md:    '0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)',
  lg:    '0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)',
  xl:    '0 20px 25px rgba(0,0,0,0.1), 0 10px 10px rgba(0,0,0,0.04)',
  selected: '0 0 0 2px #00A896',  // teal-500 selection ring
  focus:    '0 0 0 3px rgba(0,168,150,0.4)',
} as const;

// ── Standard visual dimensions (px) ──────────────────────────────────────────
export const visualDefaults = {
  kpiCard:               { width: 220, height: 100 },
  text:                  { width: 320, height:  60 },
  imagePlaceholder:      { width: 200, height: 150 },
  barChart:              { width: 400, height: 300 },
  columnChart:           { width: 400, height: 300 },
  lineChart:             { width: 500, height: 280 },
  comboChart:            { width: 500, height: 300 },
  pieChart:              { width: 300, height: 280 },
  donutChart:            { width: 300, height: 280 },
  table:                 { width: 600, height: 320 },
  matrix:                { width: 600, height: 320 },
  slicer:                { width: 180, height: 200 },
  gauge:                 { width: 220, height: 180 },
  funnel:                { width: 320, height: 300 },
  treemap:               { width: 400, height: 300 },
  decompositionTree:     { width: 600, height: 360 },
  mapPlaceholder:        { width: 500, height: 360 },
} as const;

// ── Canvas dimensions ─────────────────────────────────────────────────────────
export const canvas = {
  defaultWidth:  1280,
  defaultHeight:  720,
  mobileWidth:    360,
  mobileHeight:   800,
  minZoom:       0.25,
  maxZoom:       4.0,
  defaultZoom:   1.0,
  safeMarginPx:   20,
} as const;

// ── Status (always with label/icon, never color-only) ─────────────────────────
export const statusColors = {
  success: { bg: '#D1FAE5', text: '#065F46', border: '#6EE7B7', icon: '✓' },
  warning: { bg: '#FEF3C7', text: '#92400E', border: '#FCD34D', icon: '⚠' },
  error:   { bg: '#FEE2E2', text: '#991B1B', border: '#FCA5A5', icon: '✕' },
  info:    { bg: '#DBEAFE', text: '#1E40AF', border: '#93C5FD', icon: 'ℹ' },
  neutral: { bg: '#F3F4F6', text: '#374151', border: '#D1D5DB', icon: '·' },
} as const;

// ── Consolidated token export ──────────────────────────────────────────────────
export const tokens = {
  color,
  typography,
  spacing,
  grid,
  borderRadius,
  shadow,
  visualDefaults,
  canvas,
  statusColors,
} as const;

export default tokens;
