/**
 * Intent Tracker — brand tokens (TypeScript)
 *
 * Single source of truth for colors, typography, spacing, radius.
 * Keep in sync with tokens.py and theme.css (same values, different format).
 */

export const colors = {
  // Brand
  brand: {
    orange: "#FF6B2C",
    orangeHover: "#E55A1B",
    nearBlack: "#111827",
    white: "#FFFFFF",
  },
  // Surface
  surface: {
    background: "#FFFFFF",
    card: "#FFFFFF",
    surfaceHover: "#F9FAFB",
    tableHeader: "#F9FAFB",
    border: "#E5E7EB",
    borderHover: "#D1D5DB",
  },
  // Text
  text: {
    primary: "#111827",
    body: "#374151",
    secondary: "#6B7280",
    muted: "#9CA3AF",
  },
  // Data / semantic
  data: {
    positive: "#10B981",
    negative: "#EF4444",
    warning: "#F59E0B",
  },
  // Category palette
  category: {
    solver: "#6366F1",
    filler: "#10B981",
    quoter: "#F59E0B",
    bridge: "#06B6D4",
    dex: "#8B5CF6",
    infrastructure: "#EC4899",
  },
  // Dark theme (used by Streamlit dashboard)
  dark: {
    background: "#0B0F19",
    surface: "#111827",
    border: "#1F2937",
    borderHover: "#374151",
    text: "#D1D5DB",
    textPrimary: "#F9FAFB",
    textMuted: "#6B7280",
    accent: "#00D4AA",
    accentHover: "#00F0C0",
  },
} as const;

export const typography = {
  fontFamily: {
    sans: "Inter, system-ui, -apple-system, sans-serif",
    mono: "ui-monospace, SFMono-Regular, Menlo, monospace",
  },
  fontSize: {
    xs: "0.75rem",   // 12px
    sm: "0.875rem",  // 14px
    base: "1rem",    // 16px
    lg: "1.125rem",  // 18px
    xl: "1.25rem",   // 20px
    "2xl": "1.5rem", // 24px
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
} as const;

export const spacing = {
  tight: "0.5rem",     // 8px
  default: "0.75rem",  // 12px
  cardPadding: "1.25rem", // 20px
  section: "2rem",     // 32px
  page: "1.5rem",      // 24px
} as const;

export const radius = {
  sm: "0.5rem",   // 8px — buttons, inputs
  md: "0.625rem", // 10px — shadcn default
  lg: "0.75rem",  // 12px — cards, panels, tables
  full: "9999px", // badges, pills, logos
} as const;

export const logo = {
  primary: "/logos/logo.svg",        // white letters on black
  light: "/logos/logo-light.svg",    // dark letters on white
  favicon: "/logos/favicon.svg",
  minimumSize: 24,
  clearSpacePct: 25,
  dotColor: colors.brand.orange,
} as const;

export const categoryColor = (category: string): string => {
  const key = category.toLowerCase() as keyof typeof colors.category;
  return colors.category[key] ?? colors.text.secondary;
};

export const theme = { colors, typography, spacing, radius, logo } as const;
export type Theme = typeof theme;
