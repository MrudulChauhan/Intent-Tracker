# @intent-tracker/brand

Single source of truth for the Intent Tracker brand.

## Contents

| File | Consumer | Format |
|------|----------|--------|
| `tokens.ts` | `apps/web` | TS const exports |
| `theme.css` | `apps/web/src/app/globals.css` (imported) | CSS custom properties |
| `guidelines.md` | humans | markdown |
| `logos/` | `apps/web/public/logos/` (copied via `sync_logos.sh`) | SVG + PNG |

## Logos

- `logos/logo.svg` — white on dark, primary
- `logos/logo-light.svg` — dark on white
- `logos/favicon.svg`
- `logos/chains/<slug>.png` — 23 chains (source: [DefiLlama icons](https://github.com/DefiLlama/icons))
- `logos/protocols/<slug>.png` — 48 protocols (source: [DefiLlama icons](https://github.com/DefiLlama/icons))

### Adding a new logo

1. Drop the file into `logos/chains/` or `logos/protocols/` (PNG, square, ~64px).
2. Run `npm run sync-logos` to propagate to `apps/web/public/logos/`.
3. Update the slug map in `apps/web/src/components/chain-logo.tsx` or `project-logo.tsx` if the display name differs from the filename slug.

## Updating tokens

When changing a color / spacing / radius value, update **both** files:

- `tokens.ts` (TypeScript export for the Next.js app)
- `theme.css` (CSS custom properties consumed by Tailwind in `apps/web`)

See `guidelines.md` for the full brand system and rationale.
