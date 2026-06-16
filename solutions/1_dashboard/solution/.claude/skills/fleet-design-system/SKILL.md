---
name: fleet-design-system
description: Apply the FleetOS industrial dark-theme design system to any FleetOS page or component. Use when building new FleetOS surfaces to ensure visual consistency.
---

# FleetOS Design System

FleetOS uses a dark industrial aesthetic optimised for readability on workshop and depot monitors. Every surface should feel high-contrast, structured, and information-dense without being cluttered.

## Colour Palette

| Token | Value | Meaning |
|---|---|---|
| `--bg` | `#0f1117` | Page background — deepest layer |
| `--bg-surface` | `#1a1f2e` | Hover states, secondary surfaces |
| `--panel` | `#1e2436` | Cards, panels, table backgrounds |
| `--border` | `#2e3650` | All borders — 1px only, never heavy |
| `--text` | `#f0f4ff` | Primary text — near-white, not pure white |
| `--text-muted` | `#7b8db0` | Labels, column headers, secondary info |
| `--accent` | `#5b9bd5` | Steel blue — primary actions, focus rings, brand moments. Desaturated for eye comfort on dark backgrounds. |
| `--accent-dim` | `#1a3050` | Accent hover backgrounds, focus shadows |

**Rule:** Never use pure black (`#000`) or pure white (`#fff`). The palette is navy-tinted throughout.

## Typography

- **Font stack:** `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Base size:** 14px
- **Page title:** 30px, weight 700, color `--accent`, letter-spacing `-0.02em`
- **Subtitle / eyebrow:** 13px, uppercase, letter-spacing `0.03em`, color `--text-muted`
- **Section headings (h2):** 15px, weight 600, color `--text`, letter-spacing `0.01em`
- **Column headers / labels:** 11px, uppercase, weight 600, letter-spacing `0.08em`, color `--text-muted`
- **Stat values:** 28px, weight 700, `font-variant-numeric: tabular-nums`
- **Never use comments or decorative text** — every string on screen should be data or a label.

## Spacing Scale

- Page padding: `32px`
- Between major sections: `20–28px` (use margin on `.summary`, gap between cards)
- Card internal padding: `24px` (panels), `20–24px` (stat cards)
- Table cell padding: `16px 14px` (vertical × horizontal)
- Filter bar padding: `14px 20px`
- Gap between inline elements (filter controls, stat cards): `12–20px`

**Rule:** Err toward more whitespace. Each row and card should feel scannable at a glance.

## Cards & Panels

- Background: `--panel`
- Border: `1px solid var(--border)` — always 1px, no drop shadows
- Border-radius: `10px`
- Never use `box-shadow` for elevation — use border and background layering instead
- **Accent-bordered variant** (warnings/alerts): add `border-left: 4px solid <accent-color>` and tint the heading to match

## Status Pills

Status is always displayed as a pill badge. Use traffic-light colours with dark tinted backgrounds so they read clearly on the dark surface.

| Status | Background | Text |
|---|---|---|
| `active` | `#14532d` | `#4ade80` (green) |
| `maintenance` | `#451a03` | `#fbbf24` (amber) |
| `overdue` | `#450a0a` | `#f87171` (red) |
| `retired` | `#1e293b` | `#64748b` (slate) |

Pill styles: `border-radius: 999px`, `padding: 3px 11px`, `font-size: 11px`, `font-weight: 700`, `text-transform: uppercase`, `letter-spacing: 0.04em`.

**Rule:** Status must always use a pill — never plain text, never an icon alone.

## Tables

- `border-collapse: collapse`, `table-layout: fixed`, full width
- Header row: 11px uppercase labels in `--text-muted`, weight 600
- Row padding: `16px 14px`
- Row separator: `1px solid var(--border)`
- Row hover: background `--bg-surface` with `transition: background 0.1s`
- No alternating row colours (zebra striping) — hover state is sufficient
- Numeric columns: `text-align: right`, `font-variant-numeric: tabular-nums`

## Interactive Controls (Filters, Buttons)

- Inputs and selects: `background: --bg`, `border: 1px solid --border`, `border-radius: 6px`, `padding: 7px 11px`, `color: --text`
- Focus state: `border-color: --accent` + `box-shadow: 0 0 0 2px --accent-dim`
- Secondary buttons: `background: --bg-surface`, `color: --text-muted`, border matches inputs
- Button hover: `background: --accent-dim`, `color: --accent`, `border-color: --accent`
- All transitions: `0.1s` — fast, not animated

## Maintenance / Warning Panels

- Use the accent-bordered card variant with `border-left: 4px solid #f59e0b`
- Heading colour: `#f59e0b` (amber)
- Day-count badges: `background: #f59e0b`, `color: #92400e` (dark text on amber for contrast), same pill shape as status pills

## Applying This System

When building a new FleetOS page:
1. Start with `--bg` as the page background, `--panel` for all card surfaces
2. Use 1px `--border` borders everywhere — no shadows
3. Mark every status value with a traffic-light pill
4. Use `--accent` only for the brand title, focus states, and primary interactive elements
5. Keep font sizes small and labels uppercase — this is a data dashboard, not a marketing page
6. Give rows and cards generous padding so fleet managers can scan quickly on a large monitor
