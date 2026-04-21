# Intent Tracker — Brand Guidelines

## Logo

The Intent Tracker logo is a minimal geometric mark representing the letters "i" and "t" — the initials of Intent Tracker.

### Logo Files
- **Primary (dark bg):** `/web/public/logo.svg` — white letters on black
- **Light variant (white bg):** `/web/public/logo-light.svg` — dark letters on white

### Logo Construction
- The "i" consists of a square dot and a rectangular stem
- The "t" consists of a crossbar and vertical stem
- The dot on the "i" is **Intent Orange (#FF6B2C)** — the signature brand accent
- All other letterforms are white (on dark) or near-black (on light)

### Logo Usage
- Minimum size: 24x24px
- Clear space: at least 25% of logo width on all sides
- Never rotate, stretch, or add effects to the logo
- The orange dot must always remain #FF6B2C

---

## Color Palette

### Brand Colors
| Name | Hex | Usage |
|------|-----|-------|
| Intent Orange | #FF6B2C | Brand accent, logo dot, primary CTA |
| Near Black | #111827 | Logo on light bg, primary headings |
| White | #FFFFFF | Logo on dark bg, backgrounds |

### UI Colors (Light Theme)
| Name | Hex | Tailwind | Usage |
|------|-----|----------|-------|
| Background | #FFFFFF | white | Page background |
| Surface | #FFFFFF | white | Cards, panels |
| Surface Hover | #F9FAFB | gray-50 | Hover states |
| Table Header | #F9FAFB | gray-50 | Table header bg |
| Border | #E5E7EB | gray-200 | Card borders, dividers |
| Border Hover | #D1D5DB | gray-300 | Hover borders |

### Text Colors
| Name | Hex | Tailwind | Usage |
|------|-----|----------|-------|
| Primary | #111827 | gray-900 | Headings, names, key data |
| Body | #374151 | gray-700 | Body text |
| Secondary | #6B7280 | gray-500 | Labels, descriptions |
| Muted | #9CA3AF | gray-400 | Timestamps, placeholders |

### Data Colors
| Name | Hex | Tailwind | Usage |
|------|-----|----------|-------|
| Positive | #10B981 | emerald-500 | Positive changes, success |
| Negative | #EF4444 | red-500 | Negative changes, errors |
| Warning | #F59E0B | amber-500 | Warnings, pending states |

### Category Colors (for badges and charts)
| Category | Hex | Tailwind |
|----------|-----|----------|
| Solver | #6366F1 | indigo-500 |
| Filler | #10B981 | emerald-500 |
| Quoter | #F59E0B | amber-500 |
| Bridge | #06B6D4 | cyan-500 |
| DEX | #8B5CF6 | violet-500 |
| Infrastructure | #EC4899 | pink-500 |

---

## Typography

### Font
- **Primary:** Inter — via Google Fonts / Next.js font optimization
- **Monospace (data):** System mono — for token tickers, numerical data
- **Feature:** `font-variant-numeric: tabular-nums` for aligned numbers

### Scale
| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Brand | text-sm (14px) | font-bold (700) | gray-900 |
| Page title | text-xl (20px) | font-bold (700) | gray-900 |
| Section title | text-base (16px) | font-semibold (600) | gray-900 |
| Card title | text-sm (14px) | font-semibold (600) | gray-900 |
| Body | text-sm (14px) | font-normal (400) | gray-700 |
| Label | text-xs (12px) | font-medium (500) | gray-500 |
| Metric value | text-2xl (24px) | font-bold (700) | gray-900 |
| Token ticker | text-xs (12px) | font-mono (500) | gray-500 |
| Timestamp | text-xs (12px) | font-normal (400) | gray-400 |

---

## Spacing

### Base Unit: 4px (Tailwind default)
| Usage | Value | Tailwind |
|-------|-------|----------|
| Tight gap | 8px | gap-2 |
| Default gap | 12px | gap-3 |
| Card padding | 20px | p-5 |
| Section spacing | 32px | mb-8 |
| Page padding | 24px | px-6 |

---

## Border Radius
| Element | Radius | Tailwind |
|---------|--------|----------|
| Cards, panels | 12px | rounded-xl |
| Buttons, inputs | 8px | rounded-lg |
| Badges, pills | 9999px | rounded-full |
| Protocol logos | 50% | rounded-full |
| Tables | 12px | rounded-xl |

---

## Components

### Cards
- `bg-white border border-gray-200 rounded-xl p-5`
- Hover: `hover:shadow-md hover:border-gray-300 transition-all duration-200`

### Buttons
- Primary: `bg-gray-900 text-white hover:bg-gray-800 rounded-lg px-4 py-2 text-sm font-medium`
- Secondary: `bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 rounded-lg px-4 py-2 text-sm font-medium`
- Brand: `bg-[#FF6B2C] text-white hover:bg-[#E55A1B] rounded-lg px-4 py-2 text-sm font-semibold`

### Badges
- Default: `bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full font-medium`
- Success: `bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs px-2 py-0.5 rounded-full`
- Type-specific: use category colors at 10% opacity bg + 70% text

### Protocol Logos
- Colorful rounded circles with white initials
- Deterministic color based on name hash
- Sizes: sm (20px), md (28px), lg (40px)

---

## Logo Integration

The brand mark "it" should appear:
- In the nav bar (28px height) next to "intent tracker" text
- As a favicon
- In the footer

The text "intent tracker" always appears in lowercase, with the brand orange applied to the period or as an accent.
