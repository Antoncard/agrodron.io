---
app: AgroDron — Ingeniería Agronómica & Visión Artificial (Universidad de Caldas)
feature: Corrección de Plan de Vuelo (H1: 30 m → 25 m) y Auditoría Óptica Laplaciana (CA1–CA5)
style: feature-demo
target: desktop
output_file: output/web/panel_agrodron.html
---

# Design Language
- Background: `#F4F1EA` (Piedra cálida / papel topográfico de campo)
- Surface: `#FCFBF7` (Marfil técnico)
- Surface dark (telemetría / consola): `#16231B` (Verde bosque profundo)
- Border: `#D6D0C4` (Línea de plano topográfico 1px)
- Accent: `#2D6A4F` (Verde follaje cafetalero)
- Accent secondary: `#B84A27` (Terracota / arcilla volcánica para alertas y Hallazgo H1)
- Text: `#18221B` (Tinta carbón)
- Text dim: `#5C665E` (Gris pizarra)
- Heading font: `'Instrument Serif', Georgia, serif`
- Body font: `'Plus Jakarta Sans', system-ui, sans-serif`
- Mono font: `'JetBrains Mono', monospace`
- Border radius: `6px` (Estética de instrumento técnico, sin bordes inflados de IA)
- Additional colors:
  - `q1-norte`: `#2D6A4F`
  - `q2-este`: `#1D5B79`
  - `q3-sur`: `#B84A27`
  - `q4-oeste`: `#6C4AB6`
  - `status-ok`: `#1E6F43`
  - `status-reject`: `#B42318`

# Layout (Desktop)
- Stage: `960x620px` (Escenario interactivo CSS Animation `Before → Action → After` + conmutador a Mapa Satelital Rural Vereda La Cabaña)
- Barra superior técnica (`960x52px`, origen `0,0`): coordenadas GNSS `5°05'42"N 75°35'21"W · 1.417 msnm`, estado de criterios `CA1–CA5` y botón de acción `"Recalibrar 25 m + Auditar QA"`.
- Lienzo topográfico izquierdo (`580x536px`, origen `16,68`):
  - Polígono de la parcela de 1,0 ha (`440x440px`, origen `70,48` dentro del lienzo) dividido diagonalmente en `Q1 (Norte)`, `Q2 (Este)`, `Q3 (Sur · Desnivel 8%)` y `Q4 (Oeste)`.
  - Estacas demarcadoras en las 4 esquinas y el centro `(290, 268)`.
  - Nodos de captura fotográfica posicionados geométricamente en bordes y líneas de barrido, más anillo circular de calibración GNSS (`centro (290, 268)`, `R = 165px`, 8 nodos satelitales/telemetría de `28x28px` calculados por trigonometría `left = cx + R*cos(θ) - 14`, `top = cy + R*sin(θ) - 14`).
- Panel derecho de telemetría e inspección (`332x536px`, origen `612,68`):
  - Visor de toma aérea activa (`308x200px`), métricas `GSD`, `Altura AGL`, `Varianza Laplaciana`, `Intervalo de disparo` y estado del manifiesto `AWS S3`.

# Animation Plan

## Style: Before → Action → After

### Before State (`default`)
- Plan de vuelo en configuración original de **30,0 m AGL**:
  - `GSD = 1,125 cm/px` resaltado en terracota/rojo (`INCUMPLE CA3 >= 1,0 cm/px`).
  - Líneas de barrido separadas a `11,25 m` (10 líneas, 160 fotos teóricas).
  - Nodos de captura en giros de cabecera marcados con alerta de desenfoque (`Laplaciano < 120`).
  - Nodos de telemetría dispersos fuera del perímetro de calibración.

### Action (`clicking` → `processing`)
- Cursor técnico se desplaza hacia el botón `"Aplicar Corrección 25 m + QA"` (`500ms`), ejecuta pulso de clic (`900ms`) y activa el barrido óptico Laplaciano sobre los 4 cuadrantes de la Vereda La Cabaña (`1500ms`).

### After State (`optimized` → `complete`)
- Los nodos de captura y telemetría se reposicionan con `cubic-bezier(0.34, 1.56, 0.64, 1)` y `transition-delay` escalonado (`0.05s` por nodo):
  - Altura ajustada a **25,0 m AGL** (`GSD = 0,938 cm/px < 1,0 cm/px — CUMPLE CA3`).
  - Paso lateral ajustado a `9,38 m` (12 líneas, 228 fotos teóricas, cobertura `100,0 %`).
  - Las capturas borrosas en giros de cabecera se filtran automáticamente y aparece la insignia técnica de lote certificado para `s3://agrodron-manizales-prod-us-east-2`.

### Timing
- Total loop: `6.8s` (con opción de pausar/congelar en `ANTES (30 m)`, `PROCESANDO` o `DESPUÉS (25 m)` para inspección estática).
- Before hold: `0.5s`
- Click & scan: `0.9s`
- Spring transition: `1.2s` con `cubic-bezier(0.34, 1.56, 0.64, 1)`
- Final hold: `2.8s`
