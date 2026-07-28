# VigyanLLM — Design System & UI/UX Reference

> **Version:** 1.0.0 | **Last Updated:** July 2026
> **Platform:** VigyanLLM — Sovereign Bioinformatics Platform
> **Design Philosophy:** Clean, professional, accessible — scientific precision meets modern UI

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Color System](#2-color-system)
3. [Typography](#3-typography)
4. [Spacing & Grid](#4-spacing--grid)
5. [Layout System](#5-layout-system)
6. [Navigation](#6-navigation)
7. [Page Templates](#7-page-templates)
8. [Component Library](#8-component-library)
9. [Form Elements](#9-form-elements)
10. [Interactive States](#10-interactive-states)
11. [Animations & Transitions](#11-animations--transitions)
12. [Responsive Design](#12-responsive-design)
13. [Shadow System](#13-shadow-system)
14. [Z-Index Layers](#14-z-index-layers)
15. [Iconography & Graphics](#15-iconography--graphics)
16. [Data Visualization](#16-data-visualization)
17. [Accessibility](#17-accessibility)
18. [UX Patterns](#18-ux-patterns)

---

## 1. Design Philosophy

### 1.1 Principles

1. **Scientific Precision** — Clean layouts with generous whitespace. Every element serves a purpose. No decorative fluff.
2. **Hierarchy First** — Clear visual hierarchy: hero → tool form → results → references → footer. Users always know where they are.
3. **Trust & Credibility** — Professional navy/blue palette signals reliability. Citations and references are prominent.
4. **Accessibility** — High contrast ratios, readable font sizes, semantic HTML, keyboard-navigable.
5. **Consistency** — Single design token file (`design-tokens.css`) controls colors, spacing, and typography across 410+ pages.
6. **Performance** — No build step. No JS frameworks. Pure static HTML+CSS loads instantly from CDN.

### 1.2 Target Audience

- **Primary:** Researchers, PhD students, lab scientists (age 25–45)
- **Secondary:** Undergraduate/graduate students in biology/biotech
- **Tertiary:** Pharma/biotech professionals
- **Geography:** India-first (INR pricing), global audience

### 1.3 Emotional Design Goals

| Feeling | How We Achieve It |
|---------|-------------------|
| **Trust** | Navy/blue palette, clean typography, visible citations |
| **Precision** | Monospace outputs, structured data tables, consistent spacing |
| **Speed** | No JS framework overhead, instant page loads, CDN-delivered |
| **Professionalism** | Uppercase labels, Montserrat headings, structured forms |
| **Approachability** | Rounded corners (8–16px), friendly microcopy, clear CTAs |

---

## 2. Color System

### 2.1 Primary Palette

| Token | Hex | Usage | Example |
|-------|-----|-------|---------|
| `--blue` | `#1565C0` | Primary buttons, links, brand accent | `background: var(--blue)` |
| `--blue-light` | `#42A5F5` | Hover states, footer links | `color: var(--blue-light)` |
| `--blue-bg` | `#E3F2FD` | Dropdown hover, section tags, info cards | `background: var(--blue-bg)` |
| `--navy` | `#0F172A` | Nav bar, hero gradients, dark backgrounds | `background: var(--navy)` |
| `--navy-light` | `#1E293B` | Hero gradient endpoint | `to var(--navy-light)` |
| `--primary` | `#2563EB` | Interactive elements, active tabs | `background: var(--primary)` |

### 2.2 Neutral Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--black` | `#0A0A0F` | Footer background, dark mode |
| `--surface` | `#FFFFFF` | Page and card backgrounds |
| `--surface-alt` | `#F5F7FA` | Alternate section backgrounds |
| `--outline` | `#E2E5EA` | Card borders, input borders |
| `--slate` | `#F8FAFC` | Light section backgrounds |
| `--slate2` | `#F1F5F9` | Hover backgrounds, chips |
| `--slate-border` | `#E2E8F0` | Border color (tool pages) |
| `--text` | `#0A0A0F` | Primary text (almost black) |
| `--text2` | `#4A4A6A` | Secondary text, descriptions |
| `--muted` | `#7A7A9A` | Placeholder, subtle labels |
| `--slate-400` | `#94A3B8` | Muted text |
| `--slate-500` | `#64748B` | Medium text |
| `--slate-600` | `#475569` | Dark gray text |
| `--slate-700` | `#334155` | Dark gray |
| `--gray-blue` | `#5C6578` | Meta text |
| `--gray` | `#8B95A8` | Light meta text |

### 2.3 Semantic Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bio` | `#059669` | Success, pass indicators, green badges |
| `--green` | `#22C55E` | Success states, checkmarks |
| `--success` | `#10B981` | Success states |
| `--amber` | `#F59E0B` | Warnings, caution badges |
| `--red` | `#EF4444` | Errors, danger, logout |
| `--red-600` | `#DC2626` | Darker error |
| `--error` | `#EF4444` | Error states |
| `--warning` | `#F59E0B` | Warning states |
| `--indigo` | `#667EEA` | Skip link background |
| `--accent` | `#22D3EE` | Gradient accent (cyan) |

### 2.4 Background Variations

| Token | Hex | Usage |
|-------|-----|-------|
| `--bio-soft` | `#D1FAE5` | Success card backgrounds |
| `--primary-soft` | `#DBEAFE` | Info card backgrounds |
| `--amber-soft` | `#FEF3C7` | Warning card backgrounds |
| `--purple-soft` | `#EDE9FE` | Enterprise/pro badges |
| `--red-soft` | `#FEE2E2` | Error card backgrounds |
| `--error-soft` | `#FEE2E2` | Error backgrounds |
| `--dark-card` | `#1A2030` | Dark card backgrounds |

### 2.5 Color Application Rules

```
Text Colors:
  ┌─ Primary content  → var(--text)   (#0A0A0F)
  ├─ Secondary text   → var(--text2)  (#4A4A6A)
  ├─ Meta/help text   → var(--muted)  (#7A7A9A)
  └─ On dark bg       → var(--surface-alt) / rgba(255,255,255,.65)

Backgrounds:
  ┌─ Page             → var(--surface) / var(--slate)
  ├─ Cards            → var(--surface) / var(--slate)
  ├─ Nav              → var(--navy)
  ├─ Hero (tool pgs)  → linear-gradient(135deg, var(--navy), var(--navy-light))
  └─ Footer           → var(--black)

Borders:
  ┌─ Cards/inputs     → var(--outline) / var(--slate-border)
  ├─ Dividers         → var(--outline) / rgba(255,255,255,.06)
  └─ Focus rings      → var(--blue) with 0.1 alpha shadow

Status Colors:
  ┌─ Pass / Success   → var(--bio)    (#059669) + soft green bg
  ├─ Warning          → var(--amber)  (#F59E0B) + soft amber bg
  ├─ Error / Fail     → var(--red)    (#EF4444) + soft red bg
  └─ Info             → var(--blue)   (#1565C0) + soft blue bg
```

### 2.6 Gradients

| Gradient | Definition | Usage |
|----------|-----------|-------|
| Hero (tool pages) | `linear-gradient(135deg, #0F172A 0%, #1E293B 100%)` | Tool page hero banners |
| Avatar | `linear-gradient(135deg, #1565C0, #22D3EE)` | User profile avatar |
| Upgrade banner | `linear-gradient(135deg, #eff6ff, #dbeafe)` | Dashboard upgrade CTA |
| Landing CTA hover | `0 4px 20px rgba(21,101,192,.35)` | Button glow (not a gradient) |

---

## 3. Typography

### 3.1 Font Stack

```css
--font-h: 'Montserrat', sans-serif;    /* Headings */
--font-b: 'Open Sans', sans-serif;     /* Body text */
```

- **Montserrat** — Geometric, modern, highly legible at small sizes. Used for all headings, nav links, CTAs.
- **Open Sans** — Neutral, readable at small sizes. Used for body text, form inputs, tool content.

**Dashboard-specific:**
```css
--font-h: 'Inter', system-ui, -apple-system, sans-serif;
--font-b: 'Inter', system-ui, -apple-system, sans-serif;
```
Dashboard uses **Inter** exclusively for a tighter, more data-dense feel.

### 3.2 Type Scale

| Element | Font | Size | Weight | Letter-spacing | Line-height |
|---------|------|------|--------|----------------|-------------|
| Hero H1 | Montserrat | `clamp(2rem, 4.5vw, 3rem)` | 900 | `-.02em` | 1.1 |
| Tool Hero H1 | Montserrat | 32px | 800 | normal | 1.2 |
| Page Title H1 | Montserrat | `2rem` (32px) | 800 | normal | 1.2 |
| Section H2 | Montserrat | 22px | 800 | normal | 1.3 |
| Section H3 | Montserrat | 16–19px | 500–700 | normal | 1.3 |
| Card Title | Montserrat | 16px | 800 | normal | 1.3 |
| Plan Name | Montserrat | 16px | 800 | normal | 1.3 |
| Plan Price | Montserrat | 32px | 900 | normal | 1.2 |
| Body | Open Sans | 14–15px | 400 | normal | 1.6–1.8 |
| Small/Meta | Open Sans | 12–13px | 400–700 | normal | 1.6 |
| Nav Links | Open Sans | 13px | 600 | `.04em` uppercase | 1.3 |
| CTAs | Montserrat | 12–13px | 700 | `.06em` uppercase | 1.3 |
| Labels (uppercase) | Open Sans/Montserrat | 12px | 700 | `.05–.08em` uppercase | 1.3 |
| Form Labels | Montserrat | 12px | 700 | `.08em` uppercase | 1.3 |
| Tab Labels | Open Sans | 13px | 600 | `.01em` | 1.3 |
| Table Headers | Open Sans | 12px | 700 | `.04–.05em` uppercase | 1.3 |
| Tooltips | Open Sans | 12px | 400 | normal | 1.5 |
| Code/Sequence | Monospace | 13px | 400 | normal | 1.4 |

### 3.3 Font Loading

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800;900&family=Open+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
```

- **Preconnect hints** for both Google Fonts origins
- **`display=swap`** — ensures text remains visible during font load
- **No local font files** — all served from Google Fonts CDN

### 3.4 Text Utility Classes

```css
.text-muted   { color: rgba(255,255,255,.45) }     /* On dark backgrounds */
.text-sm      { font-size: 13px }
.text-14      { font-size: 14px }
.text-15      { font-size: 15px; font-weight: 700; margin-bottom: 8px }
.text-16      { font-family: var(--font-h); font-size: 16px; font-weight: 700; margin-bottom: 4px }
```

---

## 4. Spacing & Grid

### 4.1 Spacing Scale

```css
--space-1:   4px    /* Icons, inline gaps */
--space-2:   8px    /* Tight gaps, badge padding */
--space-3:  12px    /* Small gaps, button padding */
--space-4:  16px    /* Standard padding, card padding */
--space-5:  20px    /* Section padding, card padding */
--space-6:  24px    /* Page margins, content gaps */
--space-8:  32px    /* Section spacing */
--space-10: 40px    /* Large section spacing */
--space-12: 48px    /* Hero/CTA spacing */
--space-16: 64px    /* Major sections */
--space-20: 80px    /* Page-level spacing */
--space-24: 96px    /* Maximum spacing */
```

### 4.2 Spacing Patterns

```
┌─ Page margin        → 24px (32px on desktop nav)     ─┐
├─ Card padding       → 24–32px                         │
├─ Card gap (grid)    → 16–20px                         │
├─ Form group gap     → 14px                            │
├─ Button padding     → 12–14px vertical, 18–36px horiz │
├─ Input padding      → 10–12px vertical, 13–16px horiz │
├─ Nav link gap       → 40px                            │
├─ Footer column gap  → 40px                            │
├─ Section margin     → 32–48px                         │
├─ Hero padding       → 80px top, 60px bottom           │
└─ Accordion padding  → 16px 20px                       ─┘
```

---

## 5. Layout System

### 5.1 Container

```css
--max-w: 1200px    /* Max content width */
```

Most content containers use:
```css
max-width: var(--max-w);
margin: 0 auto;
padding: 0 24px;
```

### 5.2 Page Layouts

#### Landing Page (index.html)

```
┌─────────────────────────────────────────────────────┐
│  Nav (sticky, 72px)                                 │
├─────────────────────────────────────────────────────┤
│  Hero                                               │
│  ┌─────────────┐  ┌──────────────────────────────┐  │
│  │ Left text   │  │ Right graphic (animated)     │  │
│  └─────────────┘  └──────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│  Trust Bar (logos)                                  │
├─────────────────────────────────────────────────────┤
│  Pillars (3-column grid)                            │
├─────────────────────────────────────────────────────┤
│  Products Grid (auto-fit, minmax 280px)             │
├─────────────────────────────────────────────────────┤
│  Insights Grid (2-column)                           │
├─────────────────────────────────────────────────────┤
│  Collaboration (2-column)                           │
├─────────────────────────────────────────────────────┤
│  Comparison Table                                   │
├─────────────────────────────────────────────────────┤
│  FAQ Accordion                                      │
├─────────────────────────────────────────────────────┤
│  CTA Section                                        │
├─────────────────────────────────────────────────────┤
│  Footer (5-column grid)                             │
└─────────────────────────────────────────────────────┘
```

#### Tool Page (e.g., primer.html)

```
┌─────────────────────────────────────────────────────┐
│  Nav (sticky, 72px)                                 │
├─────────────────────────────────────────────────────┤
│  Page Header (eyebrow, title, meta chips)           │
├─────────────────────────────────────────────────────┤
│  Tab Bar (Design / Results / Help)                  │
├─────────────────────────────────────────────────────┤
│  Three-Column Layout                                │
│  ┌─────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │ Left    │  │  Center        │  │  Right        │ │
│  │ Sidebar │  │  (tool form)   │  │  Sidebar      │ │
│  │ 280px   │  │  flex: 1       │  │  260px        │ │
│  │ sticky  │  │                │  │  sticky       │ │
│  └─────────┘  └────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────┤
│  Educational H2 Sections (above results)            │
├─────────────────────────────────────────────────────┤
│  Results Container                                  │
├─────────────────────────────────────────────────────┤
│  Scientific References                              │
├─────────────────────────────────────────────────────┤
│  FAQ Section                                        │
├─────────────────────────────────────────────────────┤
│  Footer (minimal)                                   │
└─────────────────────────────────────────────────────┘
```

#### Pricing Page

```
┌─────────────────────────────────────────────────────┐
│  Nav (sticky, 72px)                                 │
├─────────────────────────────────────────────────────┤
│  Page Title + Subtitle                              │
├─────────────────────────────────────────────────────┤
│  Billing Toggle (Monthly / Yearly)                  │
├─────────────────────────────────────────────────────┤
│  Pricing Cards (4-column auto-fit grid)             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│  │ Free │ │ Pro  │ │ Lab  │ │Enterp│               │
│  └──────┘ └──────┘ └──────┘ └──────┘               │
├─────────────────────────────────────────────────────┤
│  Academic Discount Callout                          │
├─────────────────────────────────────────────────────┤
│  Comparison Table (18 rows)                         │
├─────────────────────────────────────────────────────┤
│  FAQ Accordion (8 items)                            │
├─────────────────────────────────────────────────────┤
│  Free Tools Grid                                    │
├─────────────────────────────────────────────────────┤
│  Footer                                             │
└─────────────────────────────────────────────────────┘
```

#### Dashboard Page

```
┌─────────────────────────────────────────────────────┐
│  Nav (fixed, 64px)                                  │
├─────────────────────────────────────────────────────┤
│  Page Title + Subtitle                              │
├─────────────────────────────────────────────────────┤
│  Upgrade Banner (Free users only)                   │
├─────────────────────────────────────────────────────┤
│  Plan Overview Card                                 │
├─────────────────────────────────────────────────────┤
│  Quick Stats (3-column grid)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Daily    │ │ Monthly  │ │ Saved    │            │
│  │ Usage    │ │ API Calls│ │ Results  │            │
│  └──────────┘ └──────────┘ └──────────┘            │
├─────────────────────────────────────────────────────┤
│  Tab Bar (Results / Team / API Keys)                │
├─────────────────────────────────────────────────────┤
│  Saved Results Table (paginated)                    │
├─────────────────────────────────────────────────────┤
│  Footer                                             │
└─────────────────────────────────────────────────────┘
```

#### Comparison Page (Blog-Style)

```
┌─────────────────────────────────────────────────────┐
│  Nav (sticky, 72px)                                 │
├─────────────────────────────────────────────────────┤
│  Breadcrumb                                         │
├─────────────────────────────────────────────────────┤
│  Hero (clamp 2–3rem, centered)                      │
├─────────────────────────────────────────────────────┤
│  Article Body (max-width 800px)                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Intro paragraph                             │   │
│  │  Comparison Table (14–18 rows)               │   │
│  │  Decision Guide (2-column cards)              │   │
│  │  Callout Box                                  │   │
│  │  FAQ (12 items, inline + JSON-LD)            │   │
│  │  References (5–6 items)                      │   │
│  │  CTA Box                                      │   │
│  └──────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  Footer                                             │
└─────────────────────────────────────────────────────┘
```

### 5.3 Grid Systems

```css
/* Auto-fit card grids */
.pricing-grid   { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px }
.products-grid  { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px }
.free-grid      { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px }

/* Two-column layouts */
.grid-2         { grid-template-columns: 1fr 1fr; gap: 16px }
.two-col        { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 20px }
.comp-cards     { grid-template-columns: 1fr 1fr; gap: 16px }

/* Three-column */
.grid-3         { grid-template-columns: repeat(3, 1fr); gap: 12px }
.pillars        { grid-template-columns: 1fr 1fr 1fr; gap: 24px }

/* Footer */
.footer-grid    { grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; gap: 40px }

/* Form rows */
.form-row2      { grid-template-columns: 1fr 1fr; gap: 8px }
.primer-grid    { grid-template-columns: 1fr 1fr; gap: 14px }

/* Parameter boxes */
.parambox       { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px }
```

### 5.4 Three-Column Tool Layout

```css
.tool-wrap {
  max-width: var(--max-w);
  margin: 0 auto;
  padding: 28px 24px;
  display: flex;
  flex-direction: row;
  gap: 24px;
  align-items: flex-start;
}
.tool-left  { position: sticky; top: 80px; align-self: start; flex: 0 0 var(--sidebar-l, 280px) }
.tool-right { position: sticky; top: 80px; align-self: start; flex: 0 0 var(--sidebar-r, 260px) }
.tool-center { flex: 1; min-width: 0 }
```

---

## 6. Navigation

### 6.1 Nav Bar

```
┌──────────────────────────────────────────────────────────────────┐
│ [Logo] Tools ▼  Resources ▼  Pricing  About  Blog               │
│                                [🔍 Search] [Sign in] [Get Started]│
└──────────────────────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Height | 72px |
| Background | `var(--navy)` (#0F172A) |
| Border-bottom | `1px solid rgba(255,255,255,.08)` |
| Position | `sticky`, top 0 |
| Z-index | 1000 |
| Inner padding | `0 32px 0 8px` |
| Logo | 34×34px image + "VigyanLLM" text (Montserrat 20px 800) |
| Logo hover | Image rotates `-10deg` over 0.3s |

### 6.2 Nav Links

| Property | Value |
|----------|-------|
| Font | Open Sans 13px 600 |
| Color | `rgba(255,255,255,.7)` → `#fff` on hover |
| Text transform | Uppercase |
| Letter-spacing | `.04em` |
| Padding | `6px 0` |
| Gap between items | 40px |

### 6.3 Dropdown Menu

```
┌──────────────────────────────────┐
│ Tools ▼                          │
│ ┌────────────────────────────┐   │
│ │ Primer Design              │   │
│ │ BLAST Search               │   │
│ │ Multiple Sequence Align... │   │
│ │ Molecular Docking          │   │
│ │ CRISPR Analysis            │   │
│ │ Tm Calculator              │   │
│ │ GC Calculator              │   │
│ │ DNA → RNA Transcription   │   │
│ │ PCR Analysis               │   │
│ │ Protein-Ligand Docking     │   │
│ └────────────────────────────┘   │
└──────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Background | #fff |
| Border | `1px solid var(--outline)` |
| Border-radius | 12px |
| Min-width | 240px |
| Padding | 8px |
| Shadow | `0 12px 40px rgba(0,0,0,.12)` |
| Animation | `opacity 0→1, transform translateY(4px)→0` over 0.2s |
| Item padding | `10px 16px` |
| Item hover | `background: var(--blue-bg), color: var(--blue), padding-left: 20px` |

### 6.4 Search Input

```
┌─────────────────────────────────────────────────┐
│ 🔍 Search tools, glossary, blog...              │
└─────────────────────────────────────────────────┘
```

| State | Width | Background | Border |
|-------|-------|------------|--------|
| Default | 200px | `rgba(255,255,255,.08)` | `1px solid rgba(255,255,255,.2)` |
| Focus | 260px | `rgba(255,255,255,.12)` | `1px solid rgba(255,255,255,.4)` |

### 6.5 Nav Buttons

| Button | Style | Hover |
|--------|-------|-------|
| **Sign in** | Transparent, 1.5px white border (25% opacity) | Border 100% white, bg rgba(255,255,255,.06) |
| **Get Started** | White bg, navy text | Blue-light bg, white text, blue glow shadow |

### 6.6 User Profile (Logged In)

```
┌──────────┐
│ [AB]     │  ← Avatar circle with initials
└──────────┘

Click → opens popup:
┌─────────────────────────────────────┐
│         [AB]                        │
│         user@email.com              │
│           [Pro]                     │  ← Plan badge
│                                     │
│         Dashboard                   │
│         🔒 Team Collaboration  Lab  │  ← Gated items
│         🔒 API Access          Pro  │
│         🔒 Admin Panel         Lab  │
│                                     │
│    [Upgrade to Pro →]               │  ← Upgrade CTA
│         Sign out                     │
└─────────────────────────────────────┘
```

### 6.7 Mobile Navigation

```
┌──────────────────────────────────────┐
│ [Logo]                         ☰     │
├──────────────────────────────────────┤
│ Mobile Menu (when ☰ tapped)          │
│ ┌──────────────────────────────────┐ │
│ │ TOOLS                            │ │
│ │ Primer Design                    │ │
│ │ BLAST Search                     │ │
│ │ ...                              │ │
│ │                                  │ │
│ │ RESOURCES                        │ │
│ │ Glossary                         │ │
│ │ Blog                             │ │
│ │                                  │ │
│ │ [Sign In]                        │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Hamburger | 3 stacked white bars, 22×2.5px, 5px gap |
| Active state | Bars animate to X shape |
| Menu position | Fixed, top 72px, full width |
| Max height | `calc(100vh - 72px)` with scroll |
| Section headers | 12px uppercase, `.1em` letter-spacing, 40% opacity white |
| Links | 14px, 70% opacity white |

---

## 7. Page Templates

### 7.1 Hero Patterns

#### Landing Page Hero

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│   [🎯 Bioinformatics for India]                              │
│   # Sovereign, Automated                                    │
│   ## Bioinformatics Platform                                │
│                                                              │
│   Design primers, run BLAST, dock proteins — all in your    │
│   browser. Free for researchers. No credit card needed.     │
│                                                              │
│   [Start Free Trial →]  [View All Tools →]                  │
│                                                              │
│                                         ┌──────────────────┐ │
│                                         │  Animated        │ │
│                                         │  graphic / 3D    │ │
│                                         │  molecule        │ │
│                                         └──────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Badge:** Inline flex, `var(--blue-bg)` bg, `var(--blue)` text, 12px uppercase, 6px border-radius
- **Title:** Montserrat, `clamp(2rem, 4.5vw, 3rem)`, 900 weight, `-.02em` letter-spacing
- **Subtitle:** `var(--text2)`, 15px, 1.8 line-height, max-width 520px
- **CTAs:** `btn-primary` (black → blue on hover) and `btn-secondary` (outlined)
- **Right panel:** Animated SVG/molecule graphic, fades in at 1.2s

#### Tool Page Hero

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│              Primer Design Tool                              │
│                                                              │
│    Design validated PCR primers for any gene target using    │
│    our automated 24-step pipeline with Primer3 and           │
│    SantaLucia nearest-neighbor thermodynamics.               │
│                                                              │
│              [Start Free Trial]  [Sign in]                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Gradient:** `linear-gradient(135deg, #0F172A 0%, #1E293B 100%)`
- **Padding:** 80px top, 60px bottom
- **Title:** 32px, 800, white
- **Description:** 15px, `rgba(255,255,255,.65)`, max-width 600px

### 7.2 Page Header (Tool Pages)

```
┌──────────────────────────────────────────────────────────┐
│  [🧬 Primer Design]  ← Eyebrow (12px uppercase, primary)│
│  Primer Design Tool — Design Validated PCR Primers      │
│  Design validated PCR primers for any gene target...     │
│                                                          │
│  [24-step pipeline]  [Primer3]  [SantaLucia '98]  [MIQE]│
└──────────────────────────────────────────────────────────┘
```

- **Eyebrow:** 12px, `var(--primary)`, `.14em` letter-spacing, uppercase
- **Title:** `clamp(1.6rem, 3.5vw, 2.2rem)`, 700 weight
- **Subtitle:** 14px, `var(--text2)`, max-width 520px
- **Chips:** 12px, `var(--slate)` bg, `var(--slate-border)` border, 6px border-radius

### 7.3 Tab Bar

```
┌──────────────────────────────────────────────────────────┐
│  [Design Primers]  [My Results]  [Help & Guide]          │
│  ───────────────────────────────────────────────────      │
└──────────────────────────────────────────────────────────┘
```

- **Tab buttons:** 14px padding horizontal, 13px font, 600 weight
- **Active:** `var(--navy)` text, `var(--navy)` bottom border 2px, 700 weight
- **Inactive:** `var(--muted)` text, no border
- **Hover:** `var(--navy)` text

---

## 8. Component Library

### 8.1 Cards

#### Standard Card
```
┌─────────────────────────────────────┐
│                                     │
│  Content...                         │
│                                     │
└─────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Background | `var(--surface)` |
| Border | `1px solid var(--outline)` / `var(--slate-border)` |
| Border-radius | 12px (16px for pricing/compare) |
| Padding | 24–32px (pricing: 28px 24px) |
| Shadow | `0 1px 3px rgba(0,0,0,.1)` |
| Hover | `0 4px 20px rgba(0,0,0,.08)`, translateY(-2–3px) |

#### Result Card
```
┌─────────────────────────────────────┐
│ 🟢 Top 5 Primer Pairs Found        │
│ ┌──────────────────────────────┐   │
│ │ Rank  Primer Sequence    GC  │   │
│ │ #1    ATGC...             55% │   │
│ │ #2    CGTA...             52% │   │
│ └──────────────────────────────┘   │
│ [Save] [Export PDF] [Export PPT]   │
└─────────────────────────────────────┘
```

- **Border-top:** 3px colored (green = pass, amber = partial/fail)
- **Head:** `var(--slate)` bg, border-bottom `var(--slate-border)`
- **Hover:** `0 4px 20px rgba(0,0,0,.07)`

#### Pricing Card
```
┌──────────────────────────────────────┐
│          Most Popular                │  ← Absolute positioned badge
│                                      │
│          Pro                         │
│    For power users and small labs    │
│                                      │
│         ₹699                         │
│         /month                       │
│    or ₹5,999/year (save 28%)         │
│                                      │
│    ✓ 100 analyses / day              │
│    ✓ Batch processing (50 seq)       │
│    ✓ API access (1,000 calls/mo)     │
│    ✓ PDF & PPT export                │
│    ✓ Saved workspaces                │
│    ✓ Priority support                │
│                                      │
│    [Subscribe to Pro]                │
└──────────────────────────────────────┘
```

| Element | Style |
|---------|-------|
| Popular badge | Absolute, `-12px` top, centered, `var(--blue)` bg, white text, 12px uppercase, 99px border-radius |
| Plan name | Montserrat 16px 800 |
| Price | Montserrat 32px 900 |
| Currency | 18px 700 `var(--text2)` |
| Period | 14px 500 `var(--muted)` |
| Features | 13px `var(--text2)`, border-bottom `#F1F5F9`, checkmark `#16A34A` |
| Hover | `0 8px 32px rgba(0,0,0,.08)`, translateY(-3px) |

#### Info / Status Cards

| Type | Border | Background | Text Color |
|------|--------|------------|------------|
| **Info** | `#bfdbfe` | `#eff6ff` | `#1d4ed8` |
| **Success** | `#bbf7d0` | `#D1FAE5` | `#166534` |
| **Error** | `#fecaca` | `#FEE2E2` | `#991b1b` |
| **Warning** | `#fde68a` | `#FEF3C7` | `#92400e` |

All: 10px border-radius, 14–18px padding, 13px font size.

### 8.2 Buttons

#### Primary Button
```
┌──────────────────────────────┐
│         Subscribe to Pro     │
└──────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Background | `var(--blue)` / `var(--primary)` / `var(--black)` |
| Text Color | #fff |
| Font | 12–15px, 700 weight, uppercase with `.06em` letter-spacing |
| Padding | 12–14px vertical, 18–36px horizontal |
| Border-radius | 8px |
| Transition | `opacity .15s` or `all .2s` |
| Hover | `opacity: .9` or background change |
| Disabled | `opacity: .45`, `cursor: not-allowed` |

#### Secondary Button
```
┌──────────────────────────────┐
│         View All Tools       │
└──────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Background | Transparent |
| Border | `1.5px solid var(--outline)` / `var(--slate-border)` |
| Text Color | `var(--blue)` / `var(--text)` |
| Padding | 8–14px vertical, 16–36px horizontal |
| Border-radius | 7–8px |
| Hover | Border color intensifies, bg tint appears |

#### CTA Button (Hero)
```
┌──────────────────────────────┐
│      Start Free Trial →      │
└──────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Font | Montserrat 13px 800 uppercase |
| Padding | 11–14px vertical, 18–36px horizontal |
| Hover | `var(--blue)`, glow shadow `0 4px 20px rgba(21,101,192,.35)` |
| `.secondary` variant | Transparent, `1.5px solid var(--outline)` |

#### Pricing Page Buttons

```css
.pricing-card .p-btn { display: block; padding: 12px; border-radius: 8px; font-size: 13px;
                       font-weight: 700; text-align: center; transition: all .2s; cursor: pointer }
.p-btn.primary { background: var(--blue); color: #fff }
.p-btn.primary:hover { background: #124a8c }
.p-btn.outline { border: 1.5px solid var(--outline); color: var(--text2) }
.p-btn.outline:hover { border-color: var(--blue); color: var(--blue) }
```

### 8.3 Badges & Pills

| Badge | Style | Colors |
|-------|-------|--------|
| **Status Pill** | `display:inline-flex; align-items:center; gap:6px; border-radius:99px; padding:5px 14px; font-size:12px` | `.online` = green border+text, `.offline` = amber |
| **Plan Pill** | `display:inline-flex; padding:4px 12px; border-radius:99px; font-size:12px; font-weight:700` | `.plan-free` = slate, `.plan-pro` = blue, `.plan-lab` = amber, `.plan-enterprise` = purple |
| **Tool Badge** | `display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600` | Per-tool colors (primer=blue, blast=green, msa=amber, docking=purple) |
| **Feature Check** | `color:#16A34A; font-weight:700` | Green checkmarks in pricing lists |
| **Tag** | `display:inline-block; font-size:12px; font-weight:700; letter-spacing:.12em; border:1px solid rgba(37,99,235,.3); padding:4px 12px; border-radius:99px` | Page-level tag above hero |
| **Popular Badge** | `position:absolute; top:-12px; left:50%; transform:translateX(-50%); background:var(--blue); color:#fff; font-size:12px; font-weight:700; text-transform:uppercase; border-radius:99px; padding:4px 16px` | Pricing card highlight |
| **Rank Badge** | `width:30px; height:30px; border-radius:50%; background:var(--primary); color:#fff; font-size:12px; font-weight:800; display:flex; align-items:center; justify-content:center` | Result ranking. `.top` = green |

### 8.4 Modals & Overlays

#### Auth Modal
```
┌──────────────────────────────────────┐
│                                      │
│         Welcome back                 │
│  Sign in to your VigyanLLM account.  │
│                                      │
│  ┌─ Google Sign-In ───────────────┐  │
│  │  Sign in with Google           │  │
│  └────────────────────────────────┘  │
│                                      │
│  ────────────── or ──────────────    │
│                                      │
│  Email                              │
│  ┌────────────────────────────────┐  │
│  │ researcher@lab.edu             │  │
│  └────────────────────────────────┘  │
│                                      │
│  Password                           │
│  ┌────────────────────────────────┐  │
│  │ ********                       │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │         Sign In                │  │
│  └────────────────────────────────┘  │
│                                      │
│  Don't have an account? Create one   │
│                                      │
└──────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Overlay | Fixed inset, `rgba(0,0,0,.5)`, `backdrop-filter: blur(4px)` |
| Card | White, 16px border-radius, `max-width:400px`, `90%` width |
| Card shadow | `0 20px 60px rgba(0,0,0,.3)` |
| Card padding | 36px 32px |
| Title | Montserrat 24px 700, centered |
| Subtitle | 13px `var(--text2)`, centered, margin-bottom 24px |
| Close | Not rendered by JS (click overlay to dismiss) |

#### Upgrade Gate Modal
```
┌──────────────────────────────────────┐
│                                      │
│              🔒                      │
│       Upgrade to Access              │
│                                      │
│  This feature requires a Pro         │
│  subscription. Upgrade to unlock     │
│  batch processing, API access, and   │
│  PDF/PPT export.                     │
│                                      │
│     [Upgrade to Pro →]   [Cancel]   │
│                                      │
└──────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Z-index | 99999 |
| Animation | `gateIn` — scale .95→1, translateY 10px→0, opacity 0→1, 0.25s ease |
| Lock icon | 40px font-size, 12px margin-bottom |

#### User Popup
```
┌──────────────────────────────────────┐
│              [AB]                    │
│          user@email.com              │
│              [Pro]                   │
│                                      │
│           Dashboard                  │
│                                      │
│       🔒 Team Collaboration  Lab     │
│       🔒 API Access           Pro    │
│       🔒 Admin Panel          Lab    │
│                                      │
│      [Upgrade to Lab →]              │
│                                      │
│           Sign out                    │
└──────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Max-width | 340px |
| Shadow | `0 24px 64px rgba(0,0,0,.25)` |
| Avatar | 52px circle, cyan-to-blue gradient |
| Items | 14px, `#334155`, hover `#F1F5F9` bg |
| Logout | `#EF4444`, hover `#FEF2F2` bg |

### 8.5 Tables

#### Pricing Comparison Table
```
┌──────────────────────────────────────────────────────┐
│ Feature              Free    Pro     Lab     Enterp.  │
│ ──────────────────────────────────────────────────── │
│ Daily analyses       5       100     500     ∞       │
│ Batch processing     —       50 seq  200 seq  ∞      │
│ API access           —       1K/mo   10K/mo  ∞       │
│ PDF/PPT export       —       ✓       ✓       ✓       │
│ ...                                                      │
└──────────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Font size | 13px (12px headers) |
| Header | `#F8FAFC` bg, uppercase, `.05em` letter-spacing |
| Cells | `var(--text2)` color |
| Hover row | `#FAFBFC` |
| Highlight row | `#EFF6FF`, `var(--primary)` text, 600 weight |
| Highlight col | `#EFF6FF`, `var(--primary)` text, 700 weight |

#### Dashboard Results Table
```
┌────────────────────────────────────────────────────────────────┐
│ Tool     Title             Date              Actions           │
│ ────────────────────────────────────────────────────────────── │
│ Primer   BRCA1 primers    Jul 26, 2026      [Delete] [View]   │
│ BLAST    Query results    Jul 25, 2026      [Delete] [View]   │
└────────────────────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Header | 12px uppercase, `.04em` letter-spacing, `var(--muted)`, bottom border 2px |
| Rows | 8px 12px padding, `var(--slate-border)` bottom border |
| Hover | `var(--slate2)` bg |
| Action buttons | 4px 10px, `var(--slate-border)` border, hover `var(--error)` |

### 8.6 FAQ Accordion

```
┌──────────────────────────────────────────────────┐
│  ▼ What is a melting temperature (Tm)?           │
├──────────────────────────────────────────────────┤
│  The melting temperature is the temperature at   │
│  which half of the DNA duplex dissociates...     │
│                                                  │
│  — SantaLucia 1998, Proc Natl Acad Sci USA       │
└──────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Container | `1px solid var(--outline)`, 12px border-radius |
| Question | `display:flex; justify-content:space-between; padding:16px 20px; cursor:pointer; font-size:14px; font-weight:600; background:var(--surface-alt)` |
| Answer | Hidden by default, shown when `.open` class added |
| Chevron | CSS/Unicode arrow that rotates on open |
| Bottom space | 10px margin between items |

### 8.7 Progress / Usage Bars

```css
.usage-bar { height: 8px; background: var(--slate); border-radius: 4px; overflow: hidden }
.usage-bar-fill { height: 100%; background: var(--primary); border-radius: 4px; transition: width .4s }
.usage-bar-fill.warning { background: var(--orange) }
.usage-bar-fill.danger { background: var(--error) }
```

### 8.8 Pipeline Step Indicator

```
┌──────────────────────────────────────────────────────┐
│ ✅ Transcript Isoform Filter                          │
│ ✅ Exon-Intron Junction Mapping                       │
│ 🔄 Bisulfite Conversion Simulation  ← Running (pulse)│
│ ⏳ Degenerate Base Parsing                            │
│ ⏳ Repeat Masking                                     │
│ ...                                                   │
└──────────────────────────────────────────────────────┘
```

| State | Border | Background | Animation |
|-------|--------|------------|-----------|
| **Done** | `rgba(5,150,105,.3)` | `var(--bio-soft)` | None |
| **Running** | `rgba(26,86,255,.4)` | `var(--primary-soft)` | `step-pulse` (opacity 1↔0.6, 1.5s) |
| **Fail** | `rgba(220,38,38,.3)` | `var(--red-soft)` | None |

### 8.9 Spinner

```css
.spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,.3);
           border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite }
@keyframes spin { to { transform: rotate(360deg) } }
```

### 8.10 Callout Box

```
┌──────────────────────────────────────────────────┐
│ 🎓 Academic Discount: Verified .edu / .ac.in    │
│ email holders get 30% off Pro and Lab plans.    │
│ Your discount is applied automatically at       │
│ checkout.                                       │
└──────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Background | `#EFF6FF` |
| Border-left | `4px solid var(--primary)` |
| Border-radius | `0 12px 12px 0` |
| Padding | 20px 24px |
| Font | 14px, `var(--text2)`, 1.7 line-height |

---

## 9. Form Elements

### 9.1 Text Input

```
┌───────────────────────────────────────────────┐
│                                               │
└───────────────────────────────────────────────┘
```

| State | Border | Shadow |
|-------|--------|--------|
| Default | `1px solid var(--outline)` / `var(--slate-border)` | None |
| Focus | `var(--blue)` / `var(--primary)` | `0 0 0 3px rgba(21,101,192,.1)` |
| Disabled | `opacity: .5` | `cursor: not-allowed` |

- **Padding:** 10–12px vertical, 13–16px horizontal
- **Border-radius:** 8px
- **Font:** Open Sans 13–14px
- **Transition:** `border-color .15s, box-shadow .15s`

### 9.2 Textarea

```
┌───────────────────────────────────────────────┐
│                                               │
│  ATGCGTACGTAGCTAGCTAGCTACGATC                 │
│  GATCGATCGATCGATCGATCGATCGAT                  │
│                                               │
│                                               │
└───────────────────────────────────────────────┘
```

- **Same styling as text input**
- **Font:** Monospace 13px (for sequence data)
- **Min-height:** 120px
- **Resize:** Vertical only

### 9.3 Select Dropdown

```
┌───────────────────────────────────────────────┐
│  Select organism ▼                             │
└───────────────────────────────────────────────┘
```

- **Same styling as text input**
- **`cursor: pointer`**
- Custom chevron via browser default or CSS

### 9.4 Toggle Switch (Billing)

```
Monthly  [━━━━━●━━━━━━]  Yearly  Save ~28%
```

```css
#toggle-track { position: absolute; inset: 0; background: #CBD5E1; border-radius: 13px; transition: .3s }
#toggle-knob { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px;
               background: #fff; border-radius: 50%; transition: .3s; box-shadow: 0 1px 3px rgba(0,0,0,.2) }
/* Checked state: */
#toggle-track { background: #1565C0 }
#toggle-knob { left: 25px }
```

- **Labels:** 15px, clickable, active = `var(--text)` 600, inactive = `var(--muted)` 500
- **Wrapper:** 48px wide, 26px tall, inline-block, relative

### 9.5 Labels

```css
.form-label { font-family: var(--font-h); font-size: 12px; font-weight: 700; color: var(--text2);
              text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px;
              display: flex; align-items: center; justify-content: space-between }
```

### 9.6 Tooltip

```
Primer GC %  ⓘ
             ┌──────────────────────────────────┐
             │ The GC content of a primer should│
             │ ideally be between 40-60% for    │
             │ optimal PCR efficiency.          │
             └──────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Trigger | `ⓘ` icon (12px, `var(--muted)`, `cursor: help`) |
| Box | `#0d1117` bg, `#e2e8f0` text, 12px, 8px 12px padding, 6px radius |
| Position | Above trigger, centered, `bottom: calc(100%+6px)` |
| Width | 260px |
| Show | `.tooltip-wrap:hover .tooltip-box { display: block }` |

---

## 10. Interactive States

### 10.1 Hover States

| Element | Default | Hover |
|---------|---------|-------|
| Primary button | `var(--blue)` bg | `opacity: .9` or `#124a8c` |
| Nav link | 70% white | 100% white |
| Dropdown item | `var(--text2)` | `var(--blue-bg)` bg, `var(--blue)` text, left-pad +4px |
| Card | No shadow | `0 4px 20px rgba(0,0,0,.08)`, translateY(-2px) |
| Footer link | 50% white | 100% white |
| Footer social icon | Gray, 50% opacity | Full color, 100% opacity, translateY(-2px) |
| Nav CTA | White bg, navy text | Blue-light bg, white text, blue glow |
| Nav login | Transparent, 25% white border | Full white border, 6% white bg |
| Table row | Default | `#FAFBFC` or `var(--slate2)` bg |
| Result card | Default | `0 4px 20px rgba(0,0,0,.07)` |
| Badge/Plan pill | Default | Slight darken (opacity or bg change) |
| Logo image | No rotation | `rotate(-10deg)` |

### 10.2 Focus States

| Element | Focus Ring |
|---------|-----------|
| Text input | `0 0 0 3px rgba(21,101,192,.1)` + `border-color: var(--blue)` |
| Textarea | `0 0 0 3px rgba(21,101,192,.1)` + `border-color: var(--blue)` |
| Select | Same as text input |
| Button | Browser default or custom ring |

### 10.3 Active/Checked States

| Element | Style |
|---------|-------|
| Active tab | `var(--navy)` text, 2px `var(--navy)` bottom border, 700 weight |
| Checked toggle | Track: `#1565C0`, Knob: `left: 25px` |
| Active nav item | `#fff` text color |
| Open FAQ item | Chevron rotates, answer panel visible |

### 10.4 Disabled States

| Element | Opacity | Cursor |
|---------|---------|--------|
| Button | .45 | `not-allowed` |
| Input | .5 | `not-allowed` |
| Pricing card feature | — | Text dimmed if not available |

---

## 11. Animations & Transitions

### 11.1 Duration Map

| Duration | Used For |
|----------|----------|
| 150ms | Button hovers, link hovers, auth transitions, tab switches, focus rings |
| 200ms | Card hovers, nav button hovers, dropdown menus, pricing card toggles, AI widget panel |
| 250ms | Gate modal entrance |
| 300ms | Logo rotation, hamburger animation, toggle switch, control labels, card hover transforms, footer social icons, accordion max-height |
| 400ms | Usage bar fill width |
| 600ms | Scroll reveal animations |
| 700ms | Spinner rotation (infinite) |
| 800ms | Hero section fade-up on page load |

### 11.2 Keyframe Animations

```css
/* Hero entrance */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px) }
  to   { opacity: 1; transform: translateY(0) }
}

/* Content fade-in */
@keyframes fadeIn {
  from { opacity: 0 }
  to   { opacity: 1 }
}

/* Gate modal entrance */
@keyframes gateIn {
  from { opacity: 0; transform: scale(.95) translateY(10px) }
  to   { opacity: 1; transform: scale(1) translateY(0) }
}

/* Loading spinner */
@keyframes spin {
  from { transform: rotate(0deg) }
  to   { transform: rotate(360deg) }
}

/* Pipeline step running pulse */
@keyframes step-pulse {
  0%, 100% { opacity: 1 }
  50%      { opacity: .6 }
}

/* (Landing page) Scroll reveal - used with IntersectionObserver */
.reveal { opacity: 0; transform: translateY(24px); transition: all .6s ease }
.reveal.visible { opacity: 1; transform: translateY(0) }
```

### 11.3 Staggered Animations

Landing page uses staggered entrance for cards and sections:
```css
/* Each card section gets progressively longer delay via inline style */
style="transition-delay: 0.1s"  /* First card */
style="transition-delay: 0.2s"  /* Second card */
style="transition-delay: 0.3s"  /* Third card */
```

---

## 12. Responsive Design

### 12.1 Breakpoints

| Breakpoint | Name | Key Changes |
|------------|------|-------------|
| **≤1100px** | Desktop-small | Hide right sidebar (`.tool-right`) |
| **≤1024px** | Tablet-landscape | 2-column grids collapse, hero may adjust |
| **≤900px** | Tablet | Search input narrows (200→120px), results dropdown width reduces (360→280px) |
| **≤800px** | Tablet-portrait | 3-col→vertical layout, primer-grid→1-col, pricing-grid→2-col, all 1-col grids collapse |
| **≤768px** | Mobile-large | Nav: hide links, show hamburger. Hero: stack vertically, hide right panel. Search hidden. Footer: 2-col grid. All multi-col grids → 1-col |
| **≤640px** | Mobile-medium | Comparison cards → 1-col |
| **≤500px** | Mobile-small | pricing-grid → 1-col, two-col → 1-col |
| **≤480px** | Mobile-tiny | Tighter nav spacing, free-grid → 1-col, smaller page headings |

### 12.2 Responsive Patterns

```
Desktop (>768px):
┌─────────────────────────────────────────────┐
│  Nav Links  │  Search  │  Sign in  │  CTA   │
├─────────────────────────────────────────────┤
│  3-column hero: text + graphic              │
│  3-column card grids                         │
│  5-column footer                             │
└─────────────────────────────────────────────┘

Mobile (<768px):
┌─────────────────────┐
│ [Logo]         ☰   │
├─────────────────────┤
│ Hero: stacked       │
│ All grids: 1-col    │
│ Footer: 2-col       │
└─────────────────────┘
```

### 12.3 Mobile Navigation

```css
@media (max-width: 768px) {
  .nav-links { display: none }
  .nav-inner { padding: 0 16px }
  .hamburger { display: flex }
  .nav-search-wrap { display: none }
  .mobile-menu.open { display: block }
}
```

### 12.4 Responsive Typography

Headings use `clamp()` for fluid sizing:
```css
.hero-left h1 { font-size: clamp(2rem, 4.5vw, 3rem) }
.ph-title { font-size: clamp(1.6rem, 3.5vw, 2.2rem) }
.hero h1 { font-size: clamp(2rem, 5vw, 3rem) }
.page h1 { font-size: 2rem }  /* Fixed on pricing */
```

---

## 13. Shadow System

| Level | Shadow | Usage |
|-------|--------|-------|
| Flat | None | Page content, tool inputs |
| Card | `0 1px 3px rgba(0,0,0,.1)` | Default cards |
| Card hover | `0 4px 20px rgba(0,0,0,.08)` | Card hover states |
| Dropdown | `0 12px 40px rgba(0,0,0,.12)` | Nav dropdowns |
| Search | `0 12px 48px rgba(0,0,0,.25)` | Search results |
| Popup | `0 24px 64px rgba(0,0,0,.25)` | User popup, gate modal |
| Auth modal | `0 20px 60px rgba(0,0,0,.3)` | Auth overlay |
| Widget | `0 4px 20px rgba(15,23,42,.3)` | AI widget toggle |
| CTA glow | `0 4px 20px rgba(21,101,192,.35)` | Primary button hover |
| Pricing hover | `0 8px 32px rgba(0,0,0,.08)` | Pricing card hover |
| Toggle knob | `0 1px 3px rgba(0,0,0,.2)` | Billing toggle |

---

## 14. Z-Index Layers

| Level | Z-index | Elements |
|-------|---------|----------|
| Base | auto | Page content, cards, forms |
| Mobile menu | 999 | `.mobile-menu` |
| Nav | 1000 | `.nav` (sticky header) |
| Dropdown | 1001 | `.drop-menu` (nav dropdowns) |
| Tooltip | 50 | `.tooltip-box` |
| Sticky sidebar | — | In-page sticky positioning |
| Referral overlay | 9997 | `.referral-overlay` |
| History overlay | 9998 | `.history-overlay` |
| Auth overlay | 9999 | `.auth-overlay`, `.user-popup-overlay` |
| Widget | 9999 | `#ai-widget` |
| Gate overlay | 99999 | `.gate-overlay` (upgrade modals) |

---

## 15. Iconography & Graphics

### 15.1 Approach

- **No icon font libraries** (no Font Awesome, Material Icons, etc.)
- **Inline SVGs** for all custom icons (social media, search, decorative)
- **Emoji characters** for status indicators, badges, and empty states
- **Logo:** Custom SVG (`frontend/logo.svg`) — DNA/structure icon with VigyanLLM wordmark

### 15.2 Available Graphics

| File | Path | Usage |
|------|------|-------|
| Logo | `frontend/logo.svg` | Nav bar, footer, favicon |
| OG Poster | `frontend/poster.png` | Social share image (1200×630) |
| Secondary SVG | `frontend/2DxRE.svg` | Decorative on some pages |

### 15.3 Social Media Icons (Footer)

```html
<a href="#" aria-label="Twitter">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">...</svg>
</a>
```

- **Size:** 36×36px container, 16×16px SVG
- **Container:** `1px solid rgba(255,255,255,.12)`, 8px border-radius
- **Icons:** Grayscale (`filter: grayscale(1)`), 50% opacity
- **Hover:** Full color, 100% opacity, translateY(-2px)
- **Included platforms:** X/Twitter, LinkedIn, YouTube, GitHub

---

## 16. Data Visualization

### 16.1 Usage/Stats Display

```css
.stat-value { font-family: var(--font-h); font-size: 24px; font-weight: 800; color: var(--text) }
.stat-label { font-size: 12px; color: var(--muted); margin-top: 2px }
```

### 16.2 Progress Bars

```
Daily Usage
[████████░░░░░░░░░░░░]  3/5 analyses  (60%)
```

- **Height:** 8px
- **Border-radius:** 4px
- **Track:** `var(--slate)` (#F8FAFC)
- **Fill:** `var(--primary)` (#2563EB)
- **Warning fill:** `var(--orange)` (#F59E0B) when >80%
- **Danger fill:** `var(--error)` (#EF4444) when >95%
- **Transition:** `.4s` ease on width change

### 16.3 Result Ranking

```
🥇 #1 — Forward: 5'-ATGCGTACG...-3'     Reverse: 5'-TACGATCGA...-3'
         GC: 55% | Tm: 62.4°C | Score: 92/100  ✅ Pass
         
🥈 #2 — Forward: 5'-CGATCGATC...-3'     Reverse: 5'-GCTAGCTAG...-3'
         GC: 52% | Tm: 60.1°C | Score: 85/100  ⚠️ Marginal
```

- **Rank badge:** 30px circle, `var(--primary)` bg, #1 gets `var(--bio)` green
- **Border-left color:** Forward = green (`var(--bio)`), Reverse = amber (`var(--amber)`)
- **Score:** Out of 100, color-coded pass/warning/fail

### 16.4 BLAST/Alignment Viewer

- Monospace sequence rendering
- Color-coded base pairs (A/T/G/C)
- Match/mismatch highlighting
- Scrollable horizontal overflow

---

## 17. Accessibility

### 17.1 Standards

- **Semantic HTML5** — `nav`, `main`, `section`, `article`, `footer`, `h1-h6`
- **ARIA attributes** where needed (`aria-label`, `role`)
- **Skip link** — `.skip-link` with z-index 10000
- **Keyboard navigation** — All interactive elements are focusable
- **Color contrast** — High contrast ratios (dark text on light backgrounds, white text on navy)

### 17.2 Focus Management

- Visible focus rings on all interactive elements
- `outline: none` only when custom focus style is provided
- Focus ring: `3px solid rgba(21,101,192,.1)` + blue border

### 17.3 Screen Reader Support

```css
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
           overflow: hidden; clip: rect(0,0,0,0); border: 0 }
```

### 17.4 Reduced Motion

Animations use `transition` and `@keyframes` which respect the user's `prefers-reduced-motion` setting in modern browsers.

---

## 18. UX Patterns

### 18.1 Progressive Disclosure

1. **Tool form first** — Show results only after submission
2. **Advanced options collapsed** — Hide advanced parameters behind toggle
3. **Gated features hidden** — Show upgrade modal only when user tries to use a locked feature
4. **FAQ accordion** — Show answers only on click

### 18.2 Loading & Feedback

| Action | Feedback |
|--------|----------|
| Form submission | Button shows spinner, disabled state |
| Pipeline running | Step-by-step progress with pulsing animation |
| Payment processing | Full-screen loading overlay with spinner + "Processing payment..." |
| Error | Red error card/message near the relevant control |
| Success | Green success indicator, result container appears |
| Empty state | Emoji + descriptive text ("No results yet. Run your first analysis.") |

### 18.3 Error Handling

- **Form validation errors** — Inline below the field, red text
- **API errors** — Alert box at top of form or result area
- **Network errors** — "Server unavailable. Please try again." with retry option
- **404 pages** — Custom branded 404 page with navigation

### 18.4 Gate Flow

```
User clicks "Batch Processing" toggle (Free user)
  └─ feature-gate.js: requireFeature('batch')
      ├─ FEATURE_TIER['batch'] === 'pro'
      ├─ fetch /api/payments/status
      ├─ plan === 'free' → tier index 0 < 1 (pro)
      ├─ showUpgradeGate('batch')
      │   └─ Gate modal appears:
      │      ┌──────────────────────────┐
      │      │ 🔒 Upgrade to Access     │
      │      │ Batch processing requires│
      │      │ a Pro subscription.      │
      │      │                          │
      │      │ [Upgrade to Pro →] Cancel│
      │      └──────────────────────────┘
      └─ User clicks "Upgrade" → redirect to /pricing
```

### 18.5 Conversion Flow

```
Free user on tool page
  └─ Clicks gated feature
      └─ Upgrade modal
          └─ Clicks "Upgrade to Pro →"
              └─ /pricing page
                  └─ Subscribes to Pro
                      └─ Razorpay checkout
                          └─ Success → /payment-success
                              └─ "Start Using Tools" → back to tool page
```

### 18.6 Mobile Touch Targets

- Buttons: minimum 44px height (touch-friendly)
- Form inputs: minimum 44px tap target
- Nav items: 10px padding vertical
- Accordion questions: 16px 20px padding

---

## Appendix

### A. Design Token File (`design-tokens.css`)

```css
:root {
  /* Colors */
  --blue: #1565C0;
  --blue-light: #42A5F5;
  --blue-bg: #E3F2FD;
  --navy: #0F172A;
  --navy-light: #1E293B;
  --black: #0A0A0F;
  --surface: #FFFFFF;
  --surface-alt: #F5F7FA;
  --outline: #E2E5EA;
  --text: #0A0A0F;
  --text2: #4A4A6A;
  --muted: #7A7A9A;
  --primary: #2563EB;
  --success: #10B981;
  --warning: #F59E0B;
  --error: #EF4444;
  --amber: #F59E0B;
  --bio: #059669;
  --accent: #22D3EE;
  --indigo: #667EEA;

  /* Typography */
  --font-h: 'Montserrat', sans-serif;
  --font-b: 'Open Sans', sans-serif;

  /* Spacing */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
  --space-4: 16px; --space-5: 20px; --space-6: 24px;
  --space-8: 32px; --space-10: 40px; --space-12: 48px;
  --space-16: 64px; --space-20: 80px; --space-24: 96px;

  /* Layout */
  --max-w: 1200px;
  --sidebar-l: 280px;
  --sidebar-r: 260px;

  /* Shadows */
  --card-shadow: 0 1px 3px rgba(0,0,0,.1);
  --card-hover-shadow: 0 4px 20px rgba(0,0,0,.08);

  /* Gradients */
  --hero-bg: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%);
}
```

### B. Key File Locations

| Resource | Path |
|----------|------|
| Design tokens | `frontend/design-tokens.css` |
| Shared tool styles | `frontend/tools.css` |
| Content styles | `frontend/content-styles.css` |
| Admin CMS styles | `frontend/admin/cms/css/admin.css` |
| Auth UI JavaScript | `frontend/auth-shared.js` |
| Feature gate JavaScript | `frontend/feature-gate.js` |
| Batch UI JavaScript | `frontend/batch-ui.js` |
| Results UI JavaScript | `frontend/results-ui.js` |
| Logo | `frontend/logo.svg` |
| OG poster | `frontend/poster.png` |

### C. Browser Support

- **Modern browsers:** Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **No IE11 support** — CSS custom properties and modern layout not polyfilled
- **Mobile:** iOS Safari 14+, Android Chrome 90+

---

*This document is maintained as part of the VigyanLLM codebase. Update when design tokens or UI patterns change. All CSS values reference the canonical `design-tokens.css` file.*
