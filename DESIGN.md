# DESIGN.md — Sistema Visual "Editorial Agronómico de Campo"

> **Inspiración & Estándares:** `skills/impeccable.md`, `skills/SKILL (9).md` (ui-ux-pro-max), `skills/SKILL (4).md` (ui-animation), `skills/SKILL (3).md` (css-animation).

## 1. Dirección Estética y Anti-Patrones Prohibidos
* **Identidad:** Cartografía técnica y cuaderno agronómico de precisión. Nada de degradados violeta genéricos, tarjetas anidadas en cascada, bordes neón ni estética genérica SaaS.
* **Cero emojis como iconos:** Toda iconografía funcional usa SVG inline nítidos con `aria-hidden="true"`.
* **Modo Dual de Lectura:**
  * **Claro Solar (por defecto):** Papel topográfico cálido (`#F5F2EB`), tarjetas marfil (`#FCFBF7`), tinta bosque profunda (`#142119`) para máxima legibilidad bajo sol en finca.
  * **Cockpit Oscuro (conmutable):** Obsidiana vegetal (`#0C1611`), superficies (`#13221A`), bordes sutiles esmeralda (`#233D2E`), texto hueso (`#EFF4F0`).

## 2. Tokens Semánticos (CSS Custom Properties)

### Tema Claro (Default)
| Token | Valor | Uso | Contraste vs `--surface` |
|---|---|---|---|
| `--bg` | `#F5F2EB` | Lienzo principal | — |
| `--surface` | `#FCFBF7` | Tarjetas y tablas | — |
| `--surface-2` | `#EBE6DA` | Controles y bandas secundarias | — |
| `--ink` | `#142119` | Títulos y cifras | `15.2:1` (AAA) |
| `--ink-muted` | `#4A5950` | Etiquetas y metadatos | `6.8:1` (AA+) |
| `--border` | `#D5CFC2` | Separadores hairline 1 px | — |
| `--accent` | `#1F6347` | Acción primaria y foco | `7.1:1` (AA+) |
| `--sem-ok` / `--sem-ok-bg` | `#195F3F` / `#E1F2EA` | Semáforo VERDE (<= 5% total / <= 10% Q) | `7.4:1` |
| `--sem-warn` / `--sem-warn-bg` | `#8A5300` / `#FEF3D6` | Semáforo AMARILLO | `5.8:1` |
| `--sem-err` / `--sem-err-bg` | `#A6341B` / `#FCE9E4` | Semáforo ROJO / Hallazgo H1 | `6.1:1` |

### Tema Oscuro (`[data-theme="dark"]`)
| Token | Valor |
|---|---|
| `--bg` | `#0B140F` |
| `--surface` | `#122018` |
| `--surface-2` | `#192C21` |
| `--ink` | `#EEF4F0` |
| `--ink-muted` | `#9DB0A4` |
| `--border` | `#243B2E` |
| `--accent` | `#34D399` |

## 3. Tipografía y Escala Numérica
* **Display / Títulos:** `'Instrument Serif', Georgia, serif`
* **Cuerpo / UI:** `'Plus Jakarta Sans', system-ui, sans-serif` (mínimo `14px` cuerpo, `12px` metadatos)
* **Datos / Coordenadas / Conteos:** `'JetBrains Mono', Consolas, monospace` + **`font-variant-numeric: tabular-nums`** para alineación vertical estricta en tablas y KPIs.

## 4. Espaciado, Densidad y Accesibilidad
* **Targets táctiles:** Todos los botones, selectores de vista y pills tienen `min-height: 44px` (`padding: 0 16px`).
* **Foco visible:** `:focus-visible` con anillo `2px solid var(--accent)` y `outline-offset: 2px`.
* **Sin solo-color:** Todo semáforo y nivel de densidad combina **color + etiqueta textual + indicador geométrico/icono**.
* **Grid:** Bento Grid responsivo sin desbordamiento horizontal (`max-width: 1440px`, `clamp()` en encabezados).

## 5. Reglas de Movimiento (`ui-animation` & `css-animation`)
* **Propiedades permitidas:** Exclusivamente `transform` y `opacity` (aceleración GPU; nunca animar `width`, `height`, `top`, `left`).
* **Curvas:**
  * Entradas / transiciones de vista: `220ms cubic-bezier(0.22, 1, 0.36, 1)`
  * Respuesta de pulsación (`:active`): `0ms`, `transform: scale(0.98)`
  * Cambio de tema: `[data-theme-switching] * { transition: none !important; }` + reflow forzado para evitar parpadeos.
* **Reduced Motion:** `@media (prefers-reduced-motion: reduce)` desactiva transiciones y animaciones de recorrido.
