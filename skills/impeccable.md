---
name: impeccable
description: "Use to design, redesign, critique, audit, polish or animate a frontend: websites, landing pages, dashboards, app UI, components, native iOS/Android screens, or a design system (DESIGN.md)."
version: 4.8.2
user-invocable: true
argument-hint: "[shape · audit|critique · animate|bolder|colorize|delight|layout|overdrive|quieter|typeset · adapt|clarify|distill · harden|onboard|optimize|polish · init|document|extract|live|generate] [target]"
license: Apache 2.0
---

# Impeccable — Out-of-Distribution Frontend Craft & Design Intelligence

> **Repository:** [pbakaus/impeccable](https://github.com/pbakaus/impeccable)  
> **Author:** Paul Bakaus  
> **Purpose:** Eliminate generic "AI Slop" in frontend code and elevate interfaces to production-grade, bespoke design director craft.

---

## 1. Philosophy & Core Mandate

When AI agents generate user interfaces, they tend to fall into repetitive, cookie-cutter patterns:
* Defaulting to Inter font for everything.
* Ubiquitous purple-to-blue / neon-indigo gradients.
* Cards nested inside cards with faint borders.
* Floating emoji tiles stacked above every heading.
* Cramped padding, flat typographic hierarchy, and generic 0ms state changes.

**Impeccable** gives the agent the tools, permission, and rules to build interfaces with:
1. **A Clear Point of View (POV):** Bold, authentic aesthetic matching the exact industry (e.g., AgroTech / Geospatial Cockpit), not a SaaS template.
2. **Context Persistence:** Knowing *who* the user is and *why* the product exists via `PRODUCT.md` and `DESIGN.md`.
3. **Deterministic Quality Enforcement:** Over 60 automated anti-pattern checks catching visual and accessibility defects before shipping.
4. **Targeted Vocabulary:** Actionable commands (`/impeccable polish`, `/impeccable bolder`, `/impeccable distill`) instead of vague feedback like "make it look modern".

---

## 2. Core Context Files

### `PRODUCT.md` (Product Intent & Audience)
Created with `/impeccable init`. Captures:
* **Target Audience:** Who is using this? (e.g., Drone pilot vs. Field agronomist).
* **Core Problem:** What does the user need to accomplish in 5 seconds?
* **Tone & Identity:** Utilitarian, mission-critical, rugged, premium, or playful.
* **Constraints:** Offline field operation, sunlight readability, touch-first or desktop.

### `DESIGN.md` (Visual Source of Truth)
Created with `/impeccable document`. Captures:
* **Semantic Color Tokens:** Explicit functional colors (Background, Surface, Accent, Success, Warning, Danger) with minimum 4.5:1 WCAG contrast.
* **Typography Hierarchy:** Primary display font, legible body font, monospaced data font, scale ratios.
* **Density & Spacing:** Grid systems (`--space-1` to `--space-12`), container max-widths, border radiuses.
* **Motion Tokens:** Durations ($< 300\text{ ms}$ for UI), natural bezier curves (`cubic-bezier(0.22, 1, 0.36, 1)`).

---

## 3. Anti-Patterns & Quality Rules (The 60+ Checks)

### 🚫 Visual Cliches & Generic "AI Slop" to Avoid
* **No Emoji Icons:** Never use emojis (🌿, 🛰️, ⚠️) as functional icons in buttons or headers. Use clean, accessible inline SVG with `aria-hidden="true"`.
* **No Default Inter/Purple Trap:** Avoid default Inter body font with indigo-600 buttons unless explicitly requested. Pick distinctive, industry-appropriate pairings.
* **No Nested Card Hell:** Avoid nesting cards within cards within cards. Use whitespace, subtle tint contrast, or hairline dividers (`1px solid var(--border)`) to separate sections.
* **No Orphan Headers:** Maintain visual balance; headers must have proportional spacing to their body content ($1.5\times$ distance before, $0.5\times$ distance after).

### ♿ Accessibility & Interaction (Must Have)
* **Contrast Ratio:** Text on surfaces must exceed $4.5:1$ (normal text) and $3:1$ (large text / icons).
* **Touch Targets:** Minimum $44 \times 44\text{ px}$ clickable area for buttons, tabs, and toggles.
* **Focus Rings:** Never remove `:focus` or `:focus-visible` without providing a high-contrast custom ring.
* **Immediate Active Feedback:** Buttons must react at $0\text{ ms}$ on `:active` (`transform: scale(0.98)`).

### ⚡ Performance & Motion
* **GPU-Accelerated Transforms:** Animate only `transform` and `opacity`. Never animate `width`, `height`, `top`, or `left` (causes layout reflow / jank).
* **Continuity over Teleportation:** Transitions between states (e.g., flight modes, view toggles) should morph or fade smoothly, preserving spatial context.

---

## 4. Complete Command Catalog (`/impeccable <command>`)

### 🛠️ Phase A: Plan & Setup
| Command | Purpose |
|---|---|
| `init` | Conducts a design interview, analyzes project requirements, and writes `PRODUCT.md`. |
| `document` | Scans current CSS/HTML, extracts colors, typography, and spacing into `DESIGN.md`. |
| `extract` | Pulls design tokens and component patterns out of an existing page or component. |
| `shape` | Sketches user journeys, page layouts, and wireframes before writing production code. |

### 🔍 Phase B: Review & Evaluate
| Command | Purpose |
|---|---|
| `critique` | Deep design review scored on aesthetics, hierarchy, typography, and emotion. |
| `audit` | Strict technical inspection: accessibility (WCAG AA), contrast, responsive layout, CLS, semantic HTML. |

### 🎨 Phase C: Steer & Stylize (Adjusting Visual Volume)
| Command | Purpose |
|---|---|
| `bolder` | Increases contrast, deepens typography weight, makes key focal points pop. |
| `quieter` | Softens visual noise, reduces competing borders, calms overwhelming UI elements. |
| `typeset` | Perfects font pairings, line heights, letter spacing (tracking), and reading rhythm. |
| `colorize` | Establishes a harmonious, accessible color palette matching the product identity. |
| `layout` | Re-architects structure using Bento Grids, flexible responsive columns, and balanced whitespace. |
| `animate` | Injects smooth CSS transitions, hover feedback, and spatial motion without jank. |
| `delight` | Adds subtle, tasteful micro-interactions (e.g., status pulse, hover morph, audio/visual click confirmation). |
| `overdrive` | High-impact aesthetic push for marketing, heroes, or interactive showpiece sections. |

### 🧼 Phase D: Refine & Distill
| Command | Purpose |
|---|---|
| `distill` | Removes unnecessary elements, redundant badges, and clutter. "Perfection is achieved when nothing left can be taken away." |
| `clarify` | Improves information architecture; makes complex tables or charts instantly legible. |
| `adapt` | Ensures seamless adaptation to responsive viewports (Mobile, Tablet, Desktop, Ultra-wide). |

### 🛡️ Phase E: Productionize & Harden
| Command | Purpose |
|---|---|
| `polish` | Final pass: alignment, micro-spacings, border radius consistency, loading states, empty states. |
| `harden` | Edge cases: extreme text lengths, zero-data states, error banners, offline fallbacks. |
| `onboard` | Introduces guided tours, tooltips, and empty-state hints for first-time users. |
| `optimize` | Strips bloated CSS, inlines critical tokens, minifies assets for $< 200\text{ KB}$ offline rendering. |

### ⚡ Phase F: Live Iteration
| Command | Purpose |
|---|---|
| `live` | Interactive hot-swapping and live review of component variants. |
| `generate` | Creates new cohesive components (cards, tables, badges) conforming strictly to `DESIGN.md`. |

---

## 5. Application Guide: AgroDron UI Modernization

When applying `impeccable` to **AgroDron (`agrodron.io`)**:

1. **Aesthetic Direction — Geospatial Flight Cockpit:**
   * **Backgrounds:** Deep organic obsidian/forest (`#0B1510`, `#111F17`).
   * **Surfaces:** Card containers with subtle emerald border tint (`rgba(16, 185, 129, 0.12)`).
   * **Acentuation:** Vivid agronomic emerald (`#10B981`) for flight paths and healthy vegetation.
   * **Alerts & Semaphores:** High-contrast amber (`#F59E0B`) and terracotta red (`#EF4444`) with dark backing for maximum outdoor daylight readability.

2. **Dual-View Context:**
   * **Modo Ingeniero:** Telemetría cruda, GSD ($0.938\text{ cm/px}$), varianza Laplaciana ($\ge 120$), satélites GNSS, EXIF GPS.
   * **Modo Agricultor:** Plantas vivas ($2.352$), merma en campo ($-5.92\%$), estado de cuadrantes en lenguaje agronómico sencillo.

3. **Motion & Feedback:**
   * Dron animado con estela de navegación sobre el mapa en canvas.
   * Disparo de foto con pulso lumínico en el punto GPS correspondiente.
   * Comparador interactivo (30 m vs 25 m) con morphing visual sin saltos de página.
