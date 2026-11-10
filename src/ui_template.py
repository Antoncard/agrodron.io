# Plantilla HTML/CSS de AgroDron con diseno editorial-tecnico (sin cliches de IA)
# e integracion de CSS Animation Walkthrough (960x620px) + Mapa Rural Vereda La Cabana.

PLANTILLA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgroDron · Cuaderno Técnico de Telemetría y Auditoría Óptica — Vereda La Cabaña</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

  :root {
    --bg: #F4F1EA;
    --surface: #FCFBF7;
    --surface-alt: #EDE8DC;
    --surface-dark: #16231B;
    --border: #D6D0C4;
    --border-strong: #B5ADA0;
    --text: #18221B;
    --text-dim: #5C665E;
    --accent: #2D6A4F;
    --accent-light: #E3F0E9;
    --terracotta: #B84A27;
    --terracotta-light: #FCECE7;
    --amber: #9A6700;
    --amber-light: #FEF3C7;
    --q1: #2D6A4F;
    --q2: #1D5B79;
    --q3: #B84A27;
    --q4: #6C4AB6;
    --radius: 6px;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  /* Barra superior estilo instrumento topografico */
  .top-bar {
    background: var(--surface-dark);
    color: #F4F1EA;
    padding: 12px 28px;
    border-bottom: 2px solid var(--accent);
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }
  .brand-block { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
  .brand-title {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 1.65rem;
    font-weight: 400;
    letter-spacing: 0.2px;
    margin: 0;
    color: #FCFBF7;
  }
  .brand-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    color: #A7B8AD;
    border-left: 1px solid #354A3D;
    padding-left: 12px;
  }
  .ca-strip { display: flex; gap: 6px; flex-wrap: wrap; }
  .ca-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.71rem;
    padding: 4px 9px;
    border-radius: 4px;
    background: #213328;
    border: 1px solid #354E3E;
    color: #D2E3D8;
  }
  .ca-tag.ok { border-color: #2D6A4F; color: #95D5B2; }
  .ca-tag.warn { border-color: #B84A27; color: #F4A28C; }

  .page-wrap { max-width: 1480px; margin: 0 auto; padding: 22px 28px 40px; }

  /* Cinta de metricas de ingenieria */
  .metrics-ribbon {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 22px;
  }
  @media (max-width: 1100px) { .metrics-ribbon { grid-template-columns: repeat(3, 1fr); } }
  @media (max-width: 640px) { .metrics-ribbon { grid-template-columns: 1fr 1fr; } }
  .metric-cell {
    padding: 13px 16px;
    border-right: 1px solid var(--border);
  }
  .metric-cell:last-child { border-right: none; }
  .metric-cell .m-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    font-weight: 600;
  }
  .metric-cell .m-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.18rem;
    font-weight: 700;
    color: var(--text);
    margin-top: 3px;
  }
  .metric-cell .m-sub {
    font-size: 0.74rem;
    color: var(--text-dim);
    margin-top: 2px;
  }

  /* Conmutador de modo principal */
  .section-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 14px;
  }
  .section-title {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 1.45rem;
    font-weight: 400;
    margin: 0;
    color: var(--text);
  }
  .tab-group {
    display: inline-flex;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 3px;
    gap: 4px;
  }
  .tab-btn {
    border: none;
    background: transparent;
    color: var(--text-dim);
    font-family: inherit;
    font-size: 0.8rem;
    font-weight: 600;
    padding: 6px 13px;
    border-radius: 4px;
    cursor: pointer;
  }
  .tab-btn.active {
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  }

  /* ==========================================================================
     STAGE CSS ANIMATION (960x620px) - Reglas estrictas de SKILL (4).md
     ========================================================================== */
  .walkthrough-wrapper {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px;
    margin-bottom: 24px;
    overflow-x: auto;
  }
  .walkthrough-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    max-width: 960px;
    margin: 0 auto 12px;
  }
  .state-pills { display: flex; gap: 6px; flex-wrap: wrap; }
  .btn-tech {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border-strong);
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    font-family: 'Plus Jakarta Sans', sans-serif;
  }
  .btn-tech:hover { background: var(--surface-alt); }
  .btn-tech.primary {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }
  .btn-tech.active-state {
    background: var(--surface-dark);
    color: #fff;
    border-color: var(--surface-dark);
  }

  .stage {
    position: relative;
    width: 960px;
    height: 620px;
    margin: 0 auto;
    background: #F7F4ED;
    border: 1px solid var(--border-strong);
    border-radius: 12px;
    overflow: hidden;
    user-select: none;
  }

  /* Header interno del stage (960x52px) */
  .st-header {
    position: absolute;
    left: 0; top: 0; width: 960px; height: 52px;
    background: #16231B;
    color: #F4F1EA;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    border-bottom: 1px solid #2D4436;
  }
  .st-header-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.03em;
  }
  .st-cta {
    position: relative;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 4px;
    background: var(--terracotta);
    color: #fff;
    border: 1px solid #D96B43;
    transition: background 0.4s ease, transform 0.2s ease;
  }
  .stage.clicking .st-cta {
    transform: scale(0.94);
    background: #94381B;
  }
  .stage.optimized .st-cta {
    background: var(--accent);
    border-color: #52B788;
  }

  /* Lienzo topografico izquierdo dentro del stage (580x536px en 16,68) */
  .st-field {
    position: absolute;
    left: 16px; top: 68px; width: 580px; height: 536px;
    background: #EAE4D7;
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    overflow: hidden;
  }
  /* Curvas de nivel decorativas SVG */
  .st-contours {
    position: absolute;
    inset: 0;
    opacity: 0.35;
    pointer-events: none;
  }

  /* Poligono de la parcela 100x100 m centrado en (290, 260), tamano 320x320 (origen 130, 100) */
  .st-parcela {
    position: absolute;
    left: 130px; top: 100px; width: 320px; height: 320px;
    background: #28412E;
    border: 2px solid #16231B;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.15);
  }
  .st-parcela::before, .st-parcela::after {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
  }
  .st-q-label {
    position: absolute;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    color: rgba(255,255,255,0.78);
    background: rgba(22,35,27,0.65);
    padding: 2px 6px;
    border-radius: 3px;
  }

  /* Anillo de calibracion GNSS: centro (290, 260), R = 175px -> diametro 350px (left 115, top 85) */
  .st-ring {
    position: absolute;
    left: 115px; top: 85px; width: 350px; height: 350px;
    border: 1px dashed #6B7B6E;
    border-radius: 50%;
    pointer-events: none;
    transition: border-color 0.8s ease;
  }
  .stage.optimized .st-ring { border-color: var(--accent); }

  /* 8 nodos satelitales/telemetria (28x28px) posicionados por trigonometria:
     left = 290 + 175*cos(angle) - 14, top = 260 + 175*sin(angle) - 14 */
  .sat-node {
    position: absolute;
    width: 28px; height: 28px;
    border-radius: 50%;
    background: var(--surface);
    border: 1.5px solid var(--terracotta);
    color: var(--terracotta);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.64rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    transition: left 1.1s cubic-bezier(0.34, 1.56, 0.64, 1),
                top 1.1s cubic-bezier(0.34, 1.56, 0.64, 1),
                border-color 0.6s ease,
                background-color 0.6s ease,
                color 0.6s ease;
  }
  /* Estado BEFORE: ligeramente desfasados antes de recalibrar */
  .sat-0 { left: 276px; top: 48px;  transition-delay: 0.04s; }
  .sat-1 { left: 422px; top: 102px; transition-delay: 0.08s; }
  .sat-2 { left: 476px; top: 246px; transition-delay: 0.12s; }
  .sat-3 { left: 422px; top: 392px; transition-delay: 0.16s; }
  .sat-4 { left: 276px; top: 444px; transition-delay: 0.20s; }
  .sat-5 { left: 130px; top: 392px; transition-delay: 0.24s; }
  .sat-6 { left: 76px;  top: 246px; transition-delay: 0.28s; }
  .sat-7 { left: 130px; top: 102px; transition-delay: 0.32s; }

  /* Estado AFTER (stage.optimized): posiciones trigonometricas exactas sobre R=175px */
  .stage.optimized .sat-node {
    border-color: var(--accent);
    background: var(--accent-light);
    color: var(--accent);
  }
  .stage.optimized .sat-0 { left: 276px; top: 71px; }   /* -90 deg */
  .stage.optimized .sat-1 { left: 400px; top: 122px; }  /* -45 deg */
  .stage.optimized .sat-2 { left: 451px; top: 246px; }  /*   0 deg */
  .stage.optimized .sat-3 { left: 400px; top: 370px; }  /*  45 deg */
  .stage.optimized .sat-4 { left: 276px; top: 421px; }  /*  90 deg */
  .stage.optimized .sat-5 { left: 152px; top: 370px; }  /* 135 deg */
  .stage.optimized .sat-6 { left: 101px; top: 246px; }  /* 180 deg */
  .stage.optimized .sat-7 { left: 152px; top: 122px; }  /* -135 deg */

  /* Nodos de captura fotografica dentro de la parcela (26x26px) */
  .shot-node {
    position: absolute;
    width: 26px; height: 26px;
    border-radius: 4px;
    background: rgba(252, 251, 247, 0.92);
    border: 1.5px solid #B84A27;
    color: #B84A27;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: left 1.2s cubic-bezier(0.34, 1.56, 0.64, 1),
                top 1.2s cubic-bezier(0.34, 1.56, 0.64, 1),
                background-color 0.5s ease,
                border-color 0.5s ease,
                color 0.5s ease,
                transform 0.5s ease;
  }
  /* Posiciones BEFORE (vuelo a 30 m con menor densidad, 3x4) */
  .sh-0  { left: 148px; top: 122px; transition-delay: 0.04s; }
  .sh-1  { left: 234px; top: 122px; transition-delay: 0.08s; }
  .sh-2  { left: 320px; top: 122px; transition-delay: 0.12s; }
  .sh-3  { left: 406px; top: 122px; transition-delay: 0.16s; }
  .sh-4  { left: 148px; top: 247px; transition-delay: 0.20s; }
  .sh-5  { left: 234px; top: 247px; transition-delay: 0.24s; }
  .sh-6  { left: 320px; top: 247px; transition-delay: 0.28s; }
  .sh-7  { left: 406px; top: 247px; transition-delay: 0.32s; }
  .sh-8  { left: 148px; top: 372px; transition-delay: 0.36s; }
  .sh-9  { left: 234px; top: 372px; transition-delay: 0.40s; }
  .sh-10 { left: 320px; top: 372px; transition-delay: 0.44s; }
  .sh-11 { left: 406px; top: 372px; transition-delay: 0.48s; }

  /* Nodos borrosos en giros de cabecera */
  .shot-node.blur-cabecera {
    background: #FCECE7;
    border-color: #B42318;
    color: #B42318;
  }

  /* Posiciones AFTER (25 m: paso lateral mas cerrado y cobertura 100% validada) */
  .stage.optimized .shot-node {
    background: #E3F0E9;
    border-color: #1E6F43;
    color: #1E6F43;
  }
  .stage.optimized .sh-0  { left: 162px; top: 142px; }
  .stage.optimized .sh-1  { left: 238px; top: 142px; }
  .stage.optimized .sh-2  { left: 314px; top: 142px; }
  .stage.optimized .sh-3  { left: 390px; top: 142px; }
  .stage.optimized .sh-4  { left: 162px; top: 247px; }
  .stage.optimized .sh-5  { left: 238px; top: 247px; }
  .stage.optimized .sh-6  { left: 314px; top: 247px; }
  .stage.optimized .sh-7  { left: 390px; top: 247px; }
  .stage.optimized .sh-8  { left: 162px; top: 352px; }
  .stage.optimized .sh-9  { left: 238px; top: 352px; }
  .stage.optimized .sh-10 { left: 314px; top: 352px; }
  .stage.optimized .sh-11 { left: 390px; top: 352px; }

  /* Los nodos borrosos de giro se marcan como filtrados por QA en el estado optimizado */
  .stage.optimized .shot-node.blur-cabecera {
    background: #FCECE7;
    border-color: #B42318;
    color: #B42318;
    transform: scale(0.86);
  }

  /* Escaner optico durante stage.processing (Regla 9: visibility + opacity) */
  .st-scanner {
    position: absolute;
    left: 130px; top: 100px; width: 320px; height: 320px;
    background: linear-gradient(180deg, rgba(45,106,79,0.0) 0%, rgba(45,106,79,0.32) 50%, rgba(45,106,79,0.0) 100%);
    border-top: 2px solid #52B788;
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transition: opacity 0.3s ease, visibility 0s 0.3s;
  }
  .stage.processing .st-scanner {
    opacity: 1;
    visibility: visible;
    transition: opacity 0.2s ease, visibility 0s 0s;
    animation: scanSweep 0.9s ease-in-out infinite;
  }
  @keyframes scanSweep {
    0%   { transform: translateY(-140px); }
    100% { transform: translateY(140px); }
  }

  /* Insignia de certificacion final (Regla 9: visibility + opacity) */
  .optimized-badge {
    position: absolute;
    left: 145px; top: 492px;
    background: #16231B;
    color: #95D5B2;
    border: 1px solid #2D6A4F;
    border-radius: 6px;
    padding: 7px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    opacity: 0;
    visibility: hidden;
    transform: translateY(8px);
    transition: opacity 0.45s ease-out, transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1), visibility 0s 0.45s;
  }
  .stage.complete .optimized-badge {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
    transition: opacity 0.45s ease-out, transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1), visibility 0s 0s;
  }

  /* Panel derecho dentro del stage (332x536px en 612, 68) */
  .st-side {
    position: absolute;
    left: 612px; top: 68px; width: 332px; height: 536px;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .st-side h3 {
    margin: 0 0 8px 0;
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 1.2rem;
    font-weight: 400;
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
  }
  .st-spec-row {
    display: flex;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px dashed var(--border);
    font-size: 0.8rem;
  }
  .st-spec-val {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
  }
  .st-status-box {
    padding: 10px 12px;
    border-radius: 6px;
    background: var(--terracotta-light);
    border: 1px solid #E6B3A3;
    color: var(--terracotta);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    transition: background-color 0.5s ease, color 0.5s ease, border-color 0.5s ease;
  }
  .stage.optimized .st-status-box {
    background: var(--accent-light);
    border-color: #95D5B2;
    color: var(--accent);
  }

  /* Cursor tecnico animado */
  .cursor {
    position: absolute;
    left: 480px; top: 310px;
    width: 22px; height: 22px;
    border-radius: 50%;
    border: 2px solid #16231B;
    background: rgba(255, 255, 255, 0.85);
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    pointer-events: none;
    z-index: 30;
    transition: left 0.45s cubic-bezier(0.34, 1.56, 0.64, 1),
                top 0.45s cubic-bezier(0.34, 1.56, 0.64, 1),
                transform 0.2s ease;
  }
  .cursor::after {
    content: "";
    position: absolute;
    left: 7px; top: 7px;
    width: 4px; height: 4px;
    border-radius: 50%;
    background: var(--terracotta);
  }
  .stage.clicking .cursor,
  .stage.processing .cursor {
    left: 835px; top: 24px;
  }
  .stage.clicking .cursor {
    transform: scale(0.75);
  }
  .stage.optimized .cursor,
  .stage.complete .cursor {
    left: 910px; top: 575px;
  }

  /* ==========================================================================
     SECCION MAPA RURAL INTERACTIVO + TELEMETRIA DE CAMPO
     ========================================================================== */
  .workspace-grid {
    display: grid;
    grid-template-columns: 1.42fr 1fr;
    gap: 20px;
  }
  @media (max-width: 1120px) { .workspace-grid { grid-template-columns: 1fr; } }

  .panel-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    margin-bottom: 18px;
  }
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
    margin-bottom: 12px;
  }
  .panel-header h2 {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 1.28rem;
    font-weight: 400;
    margin: 0;
    color: var(--text);
  }
  .panel-header .meta-note {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.73rem;
    color: var(--text-dim);
  }

  #map-wrap {
    position: relative;
    height: 475px;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid var(--border-strong);
    background: #1B2A20;
  }
  #map, #canvas-map { width: 100%; height: 100%; }
  #canvas-map { display: none; }

  .flight-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    padding: 10px 12px;
    background: var(--surface-alt);
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  .flight-controls input[type=range] {
    flex: 1;
    min-width: 130px;
    accent-color: var(--accent);
  }
  select.tech-select {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border-strong);
    padding: 5px 10px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.76rem;
  }

  /* Visor de camara y telemetria */
  .inspector-grid {
    display: grid;
    grid-template-columns: 230px 1fr;
    gap: 14px;
    align-items: start;
  }
  @media (max-width: 600px) { .inspector-grid { grid-template-columns: 1fr; } }
  .cam-frame {
    width: 100%;
    aspect-ratio: 4/3;
    border: 1px solid var(--border-strong);
    border-radius: 4px;
    object-fit: cover;
    background: #16231B;
  }
  .tel-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .tel-item {
    background: var(--bg);
    border: 1px solid var(--border);
    padding: 7px 10px;
    border-radius: 4px;
  }
  .tel-item .t-lbl {
    display: block;
    font-size: 0.69rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-dim);
  }
  .tel-item .t-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 600;
  }

  .status-pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 3px;
  }
  .status-pill.ACEPTADA {
    background: var(--accent-light);
    color: var(--accent);
    border: 1px solid #95D5B2;
  }
  .status-pill.RECHAZADA {
    background: var(--terracotta-light);
    color: var(--terracotta);
    border: 1px solid #E6B3A3;
  }

  /* Galeria de la microSD */
  .sd-gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(122px, 1fr));
    gap: 8px;
    max-height: 340px;
    overflow-y: auto;
    padding-right: 4px;
  }
  .sd-item {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 5px;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
  }
  .sd-item:hover { border-color: var(--accent); }
  .sd-item.active {
    border: 2px solid var(--accent);
    background: var(--accent-light);
  }
  .sd-item.RECHAZADA {
    border-color: #D97757;
    background: var(--terracotta-light);
  }
  .sd-item img {
    width: 100%;
    aspect-ratio: 4/3;
    object-fit: cover;
    border-radius: 2px;
    display: block;
  }

  /* Tablas tecnicas */
  table.tech-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.81rem;
  }
  table.tech-table th, table.tech-table td {
    padding: 7px 9px;
    border-bottom: 1px solid var(--border);
    text-align: left;
  }
  table.tech-table th {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-dim);
    background: var(--bg);
  }
  table.tech-table td.mono { font-family: 'JetBrains Mono', monospace; }

  .drone-marker-pin {
    width: 26px; height: 26px;
    background: #16231B;
    color: #FCFBF7;
    border: 2px solid #52B788;
    border-radius: 50%;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.35);
  }
</style>
</head>
<body>

<header class="top-bar">
  <div class="brand-block">
    <h1 class="brand-title">AgroDron · Estación de Fotogrametría y Auditoría Óptica</h1>
    <span class="brand-meta" id="hdr-sub"></span>
  </div>
  <div class="ca-strip" id="hdr-badges"></div>
</header>

<div class="page-wrap">
  <div class="metrics-ribbon" id="kpi-grid"></div>

  <!-- SECCION 1: WALKTHROUGH ANIMADO CSS (960x620px) SEGUN SKILL (4).md -->
  <div class="section-bar">
    <h2 class="section-title">Demostración Técnica: Corrección de Altura (H1) y Filtrado Laplaciano</h2>
    <div class="state-pills">
      <button class="btn-tech primary" id="btn-anim-loop">Reproducir Ciclo Automático</button>
      <button class="btn-tech" id="btn-freeze-before">1. Estado Inicial (30 m · H1)</button>
      <button class="btn-tech" id="btn-freeze-action">2. Escaneo Óptico QA</button>
      <button class="btn-tech" id="btn-freeze-after">3. Estado Corregido (25 m · QA)</button>
    </div>
  </div>

  <div class="walkthrough-wrapper">
    <div class="stage" id="stage">
      <div class="st-header">
        <span class="st-header-title" id="st-top-caption">VEREDA LA CABAÑA · 5°05'42"N 75°35'21"W · 1.417 MSNM</span>
        <div class="st-cta" id="st-cta-btn">Recalibrar a 25 m + Auditar QA</div>
      </div>

      <div class="st-field">
        <svg class="st-contours" viewBox="0 0 580 536" fill="none" stroke="#8C8270" stroke-width="1">
          <path d="M-20 90 Q 180 140 360 70 T 600 110"/>
          <path d="M-20 210 Q 210 260 410 190 T 600 240"/>
          <path d="M-20 350 Q 160 390 380 330 T 600 370"/>
          <path d="M-20 460 Q 240 500 440 440 T 600 480"/>
        </svg>

        <div class="st-ring"></div>

        <div class="st-parcela">
          <svg width="320" height="320" style="position:absolute;inset:0;opacity:0.28">
            <line x1="0" y1="0" x2="320" y2="320" stroke="#FCFBF7" stroke-width="1.5" stroke-dasharray="4,4"/>
            <line x1="320" y1="0" x2="0" y2="320" stroke="#FCFBF7" stroke-width="1.5" stroke-dasharray="4,4"/>
          </svg>
          <span class="st-q-label" style="left:124px;top:8px">Q1 NORTE · 598</span>
          <span class="st-q-label" style="right:8px;top:148px">Q2 ESTE · 584</span>
          <span class="st-q-label" style="left:108px;bottom:8px">Q3 SUR (-8%) · 579</span>
          <span class="st-q-label" style="left:8px;top:148px">Q4 OESTE · 591</span>
        </div>

        <!-- 8 nodos satelitales GNSS posicionados por trigonometria (centro 290,260, R=175) -->
        <div class="sat-node sat-0">S01</div>
        <div class="sat-node sat-1">S03</div>
        <div class="sat-node sat-2">S06</div>
        <div class="sat-node sat-3">S09</div>
        <div class="sat-node sat-4">S12</div>
        <div class="sat-node sat-5">S14</div>
        <div class="sat-node sat-6">S16</div>
        <div class="sat-node sat-7">S18</div>

        <!-- 12 nodos de captura fotografica -->
        <div class="shot-node sh-0 blur-cabecera">B1</div>
        <div class="shot-node sh-1">F02</div>
        <div class="shot-node sh-2">F03</div>
        <div class="shot-node sh-3">F04</div>
        <div class="shot-node sh-4">F05</div>
        <div class="shot-node sh-5">F06</div>
        <div class="shot-node sh-6">F07</div>
        <div class="shot-node sh-7">F08</div>
        <div class="shot-node sh-8">F09</div>
        <div class="shot-node sh-9">F10</div>
        <div class="shot-node sh-10">F11</div>
        <div class="shot-node sh-11 blur-cabecera">B2</div>

        <div class="st-scanner"></div>
        <div class="optimized-badge" id="st-badge">LOTE CERTIFICADO · GSD 0,938 cm/px · COBERTURA 100%</div>
      </div>

      <div class="st-side">
        <div>
          <h3>Parámetros de Misión y Auditoría</h3>
          <div class="st-spec-row"><span>Altura de vuelo AGL</span><span class="st-spec-val" id="st-val-alt">30,0 m</span></div>
          <div class="st-spec-row"><span>Resolución GSD (req &lt; 1,0)</span><span class="st-spec-val" id="st-val-gsd">1,125 cm/px</span></div>
          <div class="st-spec-row"><span>Huella por captura</span><span class="st-spec-val" id="st-val-huella">45,0 × 33,75 m</span></div>
          <div class="st-spec-row"><span>Malla (líneas × fotos)</span><span class="st-spec-val" id="st-val-malla">10 × 16 (160)</span></div>
          <div class="st-spec-row"><span>Intervalo de disparo</span><span class="st-spec-val" id="st-val-int">1,50 s</span></div>
          <div class="st-spec-row"><span>Satélites / Obturación</span><span class="st-spec-val">18 GNSS · 1/1000 s</span></div>
          <div class="st-spec-row"><span>Filtro Laplaciano (≥ 120)</span><span class="st-spec-val" id="st-val-qa">Sin aplicar (giros borrosos)</span></div>
          <div class="st-spec-row"><span>Ground Truth (4 cuadrantes)</span><span class="st-spec-val">2.352 / 2.500 (-5,92%)</span></div>
        </div>
        <div class="st-status-box" id="st-status-msg">
          HALLAZGO H1 ACTIVO: A 30 m el GSD es 1,125 cm/px e incumple CA3. Se requiere recalibrar a 25 m AGL.
        </div>
      </div>

      <div class="cursor"></div>
    </div>
  </div>

  <!-- SECCION 2: SIMULADOR CARTOGRAFICO EN VIVO SOBRE LA VEREDA LA CABANA -->
  <div class="workspace-grid">
    <div>
      <div class="panel-card">
        <div class="panel-header">
          <h2>Cartografía Rural y Recorrido del Dron — Vereda La Cabaña</h2>
          <span class="meta-note" id="modo-mapa">Ortofoto Satelital + Cuadrantes Q1–Q4</span>
        </div>
        <div id="map-wrap">
          <div id="map"></div>
          <canvas id="canvas-map" width="820" height="475"></canvas>
        </div>
        <div class="flight-controls">
          <button class="btn-tech primary" id="btn-play">Iniciar Recorrido</button>
          <button class="btn-tech" id="btn-step-b">Anterior</button>
          <button class="btn-tech" id="btn-step-f">Siguiente</button>
          <button class="btn-tech" id="btn-reset">Reiniciar</button>
          <input type="range" id="slider-foto" min="0" value="0">
          <select class="tech-select" id="sel-speed">
            <option value="900"> Cadencia 1x </option>
            <option value="420" selected> Cadencia 2x </option>
            <option value="160"> Cadencia 5x </option>
          </select>
          <button class="btn-tech" id="btn-toggle-vista">Alternar Satélite / Plano Técnico</button>
        </div>
      </div>

      <div class="panel-card">
        <div class="panel-header">
          <h2>Registro de Capturas en Tarjeta microSD (<span id="gal-count">0</span> archivos)</h2>
          <select class="tech-select" id="filtro-qa">
            <option value="TODAS">Mostrar todas las capturas</option>
            <option value="ACEPTADA">Dictamen: ACEPTADA (≥ 120)</option>
            <option value="RECHAZADA">Dictamen: RECHAZADA (borrosa en giro)</option>
          </select>
        </div>
        <div class="sd-gallery" id="galeria"></div>
      </div>
    </div>

    <div>
      <div class="panel-card">
        <div class="panel-header">
          <h2>Inspección Óptica de Fotograma y Telemetría EXIF</h2>
          <span id="cam-badge"></span>
        </div>
        <div class="inspector-grid">
          <img id="cam-img" class="cam-frame" alt="Fotograma capturado">
          <div class="tel-grid" id="cam-tel"></div>
        </div>
      </div>

      <div class="panel-card">
        <div class="panel-header">
          <h2>Comparativa Técnica de Planificación (Hallazgo H1)</h2>
          <span class="meta-note">Sensor 13,2 mm · Focal 8,8 mm · 4000×3000 px</span>
        </div>
        <table class="tech-table" id="tabla-planes"></table>
      </div>

      <div class="panel-card">
        <div class="panel-header">
          <h2>Conteo de Referencia en Tierra (Ground Truth · CA5)</h2>
          <span class="meta-note">4 cuadrantes · 2.500 m² c/u</span>
        </div>
        <div style="display:grid;grid-template-columns:155px 1fr;gap:14px;align-items:center">
          <img id="img-orto" style="width:100%;border-radius:4px;border:1px solid var(--border-strong)" alt="Ortomosaico del lote">
          <table class="tech-table" id="tabla-conteo"></table>
        </div>
      </div>

      <div class="panel-card">
        <div class="panel-header">
          <h2>Manifiesto del lote (Épica 2)</h2>
          <span class="meta-note">Verificación MD5 local</span>
        </div>
        <div id="box-manifiesto" style="font-size:0.81rem;color:var(--text-dim)"></div>
      </div>
    </div>
  </div>
</div>

<script>
const D = __DATOS_AGRODRON__;

document.getElementById("hdr-sub").textContent =
  `${D.parcela.nombre} · Rumbo líneas: ${D.parcela.rumbo}° NE`;

const badges = [
  { txt: `CA1 ${D.calibracion.satelites} SAT · ${D.calibracion.obturacion}`, ok: D.calibracion.cumple },
  { txt: `CA2 COBERTURA ${D.cobertura.cobertura_pct}%`, ok: D.cobertura.cumple_cobertura },
  { txt: `CA3 GSD ${D.plan_25.gsd_cm_px} cm/px`, ok: D.plan_25.cumple_gsd },
  { txt: `CA4 QA ${D.qa.aceptadas}/${D.qa.extraidas} OK`, ok: D.qa.aceptadas > 0 },
  { txt: `CA5 CONTEO ${D.conteo.conteo} (${D.conteo.porcentaje}%)`, ok: true }
];
document.getElementById("hdr-badges").innerHTML = badges.map(b =>
  `<span class="ca-tag ${b.ok ? 'ok' : 'warn'}">${b.txt}</span>`).join("");

const kpis = [
  { lbl: "Altura AGL / GSD", val: `${D.plan_25.altura_m} m · ${D.plan_25.gsd_cm_px}`, sub: `Límite: 26,67 m (< 1,0 cm/px)` },
  { lbl: "Auditoría Óptica (CA4)", val: `${D.qa.aceptadas} / ${D.qa.extraidas}`, sub: `${D.qa.descartadas} rechazadas · Laplaciano prom: ${D.qa.nitidez_promedio_aceptadas}` },
  { lbl: "Cobertura Efectiva (CA2)", val: `${D.cobertura.cobertura_pct} %`, sub: `Q1:${D.cobertura.por_cuadrante.Q1} Q2:${D.cobertura.por_cuadrante.Q2} Q3:${D.cobertura.por_cuadrante.Q3} Q4:${D.cobertura.por_cuadrante.Q4}` },
  { lbl: "Ground Truth (CA5)", val: `${D.conteo.conteo.toLocaleString()} pl.`, sub: `Esperadas: ${D.conteo.esperadas.toLocaleString()} (${D.conteo.diferencia})` },
  { lbl: "Autonomía Estimada", val: `${D.plan_25.tiempo_vuelo_min} min · ${D.plan_25.baterias} bat`, sub: `Trayecto: ${D.plan_25.distancia_m} m a 4,5 m/s` },
  { lbl: "Lote Almacenado", val: `${D.manifiesto.totales.COPIADO || D.manifiesto.totales.YA_EXISTE || D.manifiesto.archivos.length} archivos`, sub: `${D.manifiesto.ruta_lote}` }
];
document.getElementById("kpi-grid").innerHTML = kpis.map(k =>
  `<div class="metric-cell"><div class="m-label">${k.lbl}</div><div class="m-val">${k.val}</div><div class="m-sub">${k.sub}</div></div>`).join("");

document.getElementById("tabla-planes").innerHTML = `
  <tr><th>Parámetro</th><th>Registro inicial (30 m)</th><th>Plan corregido (25 m)</th></tr>
  <tr><td>GSD en terreno</td><td class="mono" style="color:var(--terracotta);font-weight:700">${D.plan_30.gsd_cm_px} cm/px (Incumple)</td><td class="mono" style="color:var(--accent);font-weight:700">${D.plan_25.gsd_cm_px} cm/px (Cumple)</td></tr>
  <tr><td>Huella por foto</td><td class="mono">${D.plan_30.huella_m[0]} × ${D.plan_30.huella_m[1]} m</td><td class="mono">${D.plan_25.huella_m[0]} × ${D.plan_25.huella_m[1]} m</td></tr>
  <tr><td>Líneas × Fotos/línea</td><td class="mono">${D.plan_30.lineas} × ${D.plan_30.fotos_por_linea} (${D.plan_30.total_fotos})</td><td class="mono">${D.plan_25.lineas} × ${D.plan_25.fotos_por_linea} (${D.plan_25.total_fotos})</td></tr>
  <tr><td>Intervalo de disparo</td><td class="mono">${D.plan_30.intervalo_disparo_s} s</td><td class="mono">${D.plan_25.intervalo_disparo_s} s</td></tr>
`;

document.getElementById("img-orto").src = D.ortomosaico_b64;
document.getElementById("tabla-conteo").innerHTML = `
  <tr><th>Cuadrante</th><th>Esperadas</th><th>Conteo</th><th>Desviación</th></tr>
  ${D.conteo.detalle.map(d => `<tr><td class="mono">${d.cuadrante}</td><td class="mono">${d.esperadas}</td><td class="mono">${d.conteo}</td><td class="mono">${d.diferencia} (${d.porcentaje}%)</td></tr>`).join("")}
  <tr style="font-weight:700"><td>TOTAL LOTE</td><td class="mono">${D.conteo.esperadas}</td><td class="mono">${D.conteo.conteo}</td><td class="mono">${D.conteo.diferencia} (${D.conteo.porcentaje}%)</td></tr>
`;

document.getElementById("box-manifiesto").innerHTML = `
  <div style="font-family:'JetBrains Mono',monospace;color:var(--text)">${D.manifiesto.ruta_lote}</div>
  <div style="margin-top:4px">Fotogramas aprobados y guardados en almacén local: <b>${D.manifiesto.archivos.length}</b> (${(D.manifiesto.bytes_totales/1024/1024).toFixed(2)} MB) · Verificación de integridad <code>MD5</code>.</div>
`;

/* ==========================================================================
   CONTROLADOR DE ANIMACION CSS (SKILL 4: Solo class toggling, sin inline styles)
   ========================================================================== */
const stage = document.getElementById("stage");
let animTimers = [];
let loopActivo = true;

function clearAnimTimers() {
  while (animTimers.length) {
    clearTimeout(animTimers.pop());
  }
}

function setStageTextBefore() {
  document.getElementById("st-cta-btn").textContent = "Recalibrar a 25 m + Auditar QA";
  document.getElementById("st-val-alt").textContent = "30,0 m";
  document.getElementById("st-val-gsd").textContent = "1,125 cm/px (NO cumple)";
  document.getElementById("st-val-huella").textContent = "45,0 × 33,75 m";
  document.getElementById("st-val-malla").textContent = "10 × 16 (160 fotos)";
  document.getElementById("st-val-int").textContent = "1,50 s";
  document.getElementById("st-val-qa").textContent = "Pendiente (giros borrosos)";
  document.getElementById("st-status-msg").textContent =
    "HALLAZGO H1 ACTIVO: A 30 m el GSD es 1,125 cm/px e incumple CA3. Se requiere bajar a 25 m AGL.";
}

function setStageTextAfter() {
  document.getElementById("st-cta-btn").textContent = "Plan 25 m + QA Validados";
  document.getElementById("st-val-alt").textContent = "25,0 m (Recomendado)";
  document.getElementById("st-val-gsd").textContent = "0,938 cm/px (< 1,0 OK)";
  document.getElementById("st-val-huella").textContent = "37,5 × 28,12 m";
  document.getElementById("st-val-malla").textContent = "12 × 19 (228 fotos)";
  document.getElementById("st-val-int").textContent = "1,25 s";
  document.getElementById("st-val-qa").textContent = `${D.qa.aceptadas} OK / ${D.qa.descartadas} rechazadas`;
  document.getElementById("st-status-msg").textContent =
    `CA1–CA5 CUMPLIDOS: Cobertura ${D.cobertura.cobertura_pct}% verificada y manifiesto local generado.`;
}

function runCycle() {
  clearAnimTimers();
  stage.classList.remove("clicking", "processing", "optimized", "complete");
  setStageTextBefore();

  animTimers.push(setTimeout(() => stage.classList.add("clicking"), 500));
  animTimers.push(setTimeout(() => {
    stage.classList.remove("clicking");
    stage.classList.add("processing");
  }, 900));
  animTimers.push(setTimeout(() => {
    stage.classList.remove("processing");
    stage.classList.add("optimized");
    setStageTextAfter();
  }, 1700));
  animTimers.push(setTimeout(() => stage.classList.add("complete"), 2900));
  if (loopActivo) {
    animTimers.push(setTimeout(runCycle, 6500));
  }
}

document.getElementById("btn-anim-loop").onclick = () => {
  loopActivo = true;
  runCycle();
};
document.getElementById("btn-freeze-before").onclick = () => {
  loopActivo = false;
  clearAnimTimers();
  stage.classList.remove("clicking", "processing", "optimized", "complete");
  setStageTextBefore();
};
document.getElementById("btn-freeze-action").onclick = () => {
  loopActivo = false;
  clearAnimTimers();
  stage.classList.remove("clicking", "optimized", "complete");
  stage.classList.add("processing");
  setStageTextBefore();
};
document.getElementById("btn-freeze-after").onclick = () => {
  loopActivo = false;
  clearAnimTimers();
  stage.classList.remove("clicking", "processing");
  stage.classList.add("optimized", "complete");
  setStageTextAfter();
};

setTimeout(runCycle, 300);

/* ==========================================================================
   MAPA RURAL VEREDA LA CABANA + RECORRIDO DE CAMPO
   ========================================================================== */
let usarCanvas = (typeof L === "undefined");
let map = null, droneMarker = null, footprintPoly = null, photoMarkers = [];

function initLeaflet() {
  if (usarCanvas) return;
  try {
    map = L.map("map", { center: D.parcela.centro, zoom: 18 });
    const sat = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Esri World Imagery · Vereda La Cabaña (Manizales)", maxZoom: 20
    });
    const topo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenTopoMap (Curvas de nivel rurales)", maxZoom: 17
    });
    const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap", maxZoom: 20
    });
    sat.addTo(map);

    const capaCuadrantes = L.layerGroup().addTo(map);
    const capaEntornoRural = L.layerGroup().addTo(map);
    const capaRuta = L.layerGroup().addTo(map);

    D.parcela.cuadrantes_geo.forEach(q => {
      L.polygon(q.poly, {
        color: q.color, weight: 1.5, dashArray: "4,4", fillColor: q.color, fillOpacity: 0.14
      }).bindPopup(`<b>${q.nombre}</b><br>Área: 2.500 m²`).addTo(capaCuadrantes);
      const lblIcon = L.divIcon({
        className: "",
        html: `<div style="background:#16231B;color:#FCFBF7;padding:2px 6px;border-radius:3px;border:1px solid ${q.color};font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;white-space:nowrap">${q.id}</div>`,
        iconSize: [30, 18], iconAnchor: [15, 9]
      });
      L.marker(q.label, { icon: lblIcon, interactive: false }).addTo(capaCuadrantes);
    });

    L.polygon(D.parcela.esquinas, { color: "#FCFBF7", weight: 2, fillOpacity: 0.03 })
      .bindPopup("<b>Lote Piloto Vereda La Cabaña</b><br>100 m × 100 m (1,0 ha) · Altitud ~1.417 msnm").addTo(capaCuadrantes);

    [...D.parcela.esquinas, D.parcela.centro].forEach((pt, i) => {
      L.circleMarker(pt, {
        radius: 4, color: "#FCFBF7", weight: 1.5, fillColor: "#B84A27", fillOpacity: 1
      }).bindPopup(`Estaca demarcadora #${i + 1}`).addTo(capaCuadrantes);
    });

    D.parcela.arboles.forEach(a => {
      L.circleMarker([a.lat, a.lon], {
        radius: 6, color: "#16231B", weight: 1.5, fillColor: "#2D6A4F", fillOpacity: 0.88
      }).bindPopup("Árbol de sombrío / lindero de la finca").addTo(capaEntornoRural);
    });

    const homeIcon = L.divIcon({
      className: "",
      html: `<div style="background:#FCFBF7;color:#16231B;padding:2px 6px;border-radius:3px;border:1.5px solid #16231B;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:10px;white-space:nowrap">BASE GNSS</div>`,
      iconSize: [74, 20], iconAnchor: [37, 10]
    });
    L.marker(D.parcela.base_dron, { icon: homeIcon })
      .bindPopup("<b>Estación de Campo y Telemetría</b><br>Punto de despegue y calibración IMU/GNSS (18 satélites)").addTo(capaEntornoRural);

    const latlngsRuta = D.waypoints.map(w => [w.lat, w.lon]);
    L.polyline(latlngsRuta, { color: "#E9C46A", weight: 2, dashArray: "5,5" }).addTo(capaRuta);

    D.fotos.forEach((f, idx) => {
      const col = f.dictamen === "ACEPTADA" ? "#2D6A4F" : "#B84A27";
      const cm = L.circleMarker([f.lat, f.lon], {
        radius: 5, color: "#FCFBF7", weight: 1.2, fillColor: col, fillOpacity: 0.95
      }).addTo(capaRuta);
      cm.on("click", () => seleccionarFoto(idx));
      photoMarkers.push(cm);
    });

    footprintPoly = L.polygon(D.fotos[0].huella_esq, {
      color: "#52B788", weight: 1.8, fillColor: "#52B788", fillOpacity: 0.16
    }).addTo(map);

    const icon = L.divIcon({ className: "", html: '<div class="drone-marker-pin">UAV</div>', iconSize: [26, 26], iconAnchor: [13, 13] });
    droneMarker = L.marker([D.fotos[0].lat, D.fotos[0].lon], { icon, zIndexOffset: 1000 }).addTo(map);

    L.control.layers(
      { "Satélite Rural (Vereda La Cabaña)": sat, "Topográfico Rural": topo, "Mapa Vial Rural": osm },
      { "Cuadrantes Q1–Q4 y Estacas": capaCuadrantes, "Árboles de Lindero y Base": capaEntornoRural, "Ruta y Disparos": capaRuta }
    ).addTo(map);
  } catch (e) {
    usarCanvas = true;
  }
}

function dibujarCanvas(idxActual) {
  const cv = document.getElementById("canvas-map");
  const ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height;

  ctx.fillStyle = "#1E2F23";
  ctx.fillRect(0, 0, W, H);

  const pad = 48;
  const side = Math.min(W, H) - pad * 2;
  const ox = (W - side) / 2, oy = (H - side) / 2;
  const toXY = (x, y) => [ox + (x / D.parcela.ancho_m) * side, oy + ((D.parcela.largo_m - y) / D.parcela.largo_m) * side];

  // Camino veredal
  ctx.strokeStyle = "#6B533B";
  ctx.lineWidth = 14;
  ctx.beginPath();
  ctx.moveTo(0, oy + side + 22);
  ctx.lineTo(W, oy + side + 18);
  ctx.stroke();

  // Parcela y surcos
  ctx.fillStyle = "#28412E";
  ctx.fillRect(ox, oy, side, side);
  ctx.strokeStyle = "rgba(22,35,27,0.65)";
  ctx.lineWidth = 1;
  for (let xm = 2; xm < 100; xm += 2) {
    const [sx] = toXY(xm, 0);
    ctx.beginPath();
    ctx.moveTo(sx, oy);
    ctx.lineTo(sx, oy + side);
    ctx.stroke();
  }

  // Diagonales de cuadrantes
  ctx.strokeStyle = "rgba(252,251,247,0.28)";
  ctx.beginPath();
  ctx.moveTo(ox, oy); ctx.lineTo(ox + side, oy + side);
  ctx.moveTo(ox + side, oy); ctx.lineTo(ox, oy + side);
  ctx.stroke();

  ctx.fillStyle = "rgba(252,251,247,0.82)";
  ctx.font = "600 11px 'JetBrains Mono', monospace";
  ctx.fillText("Q1 NORTE", ox + side / 2 - 28, oy + 18);
  ctx.fillText("Q3 SUR (DESNIVEL 8%)", ox + side / 2 - 64, oy + side - 10);
  ctx.fillText("Q4 OESTE", ox + 10, oy + side / 2);
  ctx.fillText("Q2 ESTE", ox + side - 62, oy + side / 2);

  D.parcela.arboles.forEach(a => {
    const [ax, ay] = toXY(a.x, a.y);
    ctx.beginPath();
    ctx.arc(ax, ay, 7, 0, Math.PI * 2);
    ctx.fillStyle = "#2D6A4F";
    ctx.fill();
    ctx.strokeStyle = "#16231B";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  });

  D.plantas_muestra.forEach(p => {
    const [px, py] = toXY(p.x, p.y);
    ctx.fillStyle = p.viva ? "rgba(149,213,178,0.55)" : "rgba(184,74,39,0.45)";
    ctx.fillRect(px - 1.2, py - 1.2, 2.4, 2.4);
  });

  const fAct = D.fotos[idxActual];
  const [fx, fy] = toXY(fAct.x, fAct.y);
  const fw = (D.parcela.huella_m[0] / D.parcela.ancho_m) * side;
  const fh = (D.parcela.huella_m[1] / D.parcela.largo_m) * side;
  ctx.fillStyle = fAct.dictamen === "ACEPTADA" ? "rgba(82,183,136,0.18)" : "rgba(184,74,39,0.24)";
  ctx.strokeStyle = fAct.dictamen === "ACEPTADA" ? "#52B788" : "#B84A27";
  ctx.lineWidth = 2;
  ctx.fillRect(fx - fw / 2, fy - fh / 2, fw, fh);
  ctx.strokeRect(fx - fw / 2, fy - fh / 2, fw, fh);

  ctx.strokeStyle = "rgba(233,196,106,0.75)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  D.fotos.forEach((f, i) => {
    const [x, y] = toXY(f.x, f.y);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  D.fotos.forEach((f, i) => {
    const [x, y] = toXY(f.x, f.y);
    ctx.beginPath();
    ctx.arc(x, y, i <= idxActual ? 4.5 : 3, 0, Math.PI * 2);
    ctx.fillStyle = f.dictamen === "ACEPTADA" ? "#52B788" : "#B84A27";
    ctx.fill();
    ctx.strokeStyle = "#16231B";
    ctx.stroke();
  });

  ctx.beginPath();
  ctx.arc(fx, fy, 8, 0, Math.PI * 2);
  ctx.fillStyle = "#16231B";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#52B788";
  ctx.stroke();
}

let idxActual = 0;
let timer = null;

const slider = document.getElementById("slider-foto");
slider.max = D.fotos.length - 1;

function renderGaleria() {
  const filtro = document.getElementById("filtro-qa").value;
  const gal = document.getElementById("galeria");
  const items = D.fotos.map((f, idx) => ({ f, idx }))
    .filter(it => filtro === "TODAS" || it.f.dictamen === filtro);
  document.getElementById("gal-count").textContent = items.length;
  gal.innerHTML = items.map(({ f, idx }) => `
    <div class="sd-item ${f.dictamen} ${idx === idxActual ? 'active' : ''}" id="thumb-${idx}" onclick="seleccionarFoto(${idx})">
      <img src="${f.thumb}" alt="${f.archivo}">
      <div style="display:flex;justify-content:space-between;margin-top:4px;font-weight:700">
        <span>#${f.n} · ${f.cuadrante}</span>
        <span>${f.nitidez}</span>
      </div>
      <div style="color:var(--text-dim);font-size:0.65rem">${f.dictamen}${f.motivo ? ' · '+f.motivo : ''}</div>
    </div>
  `).join("");
}

function seleccionarFoto(idx) {
  idxActual = Math.max(0, Math.min(D.fotos.length - 1, idx));
  slider.value = idxActual;
  const f = D.fotos[idxActual];

  document.getElementById("cam-img").src = f.thumb;
  document.getElementById("cam-badge").innerHTML =
    `<span class="status-pill ${f.dictamen}">${f.dictamen}${f.motivo ? ' · ' + f.motivo : ''}</span>`;
  document.getElementById("cam-tel").innerHTML = `
    <div class="tel-item"><span class="t-lbl">Archivo / Cuadrante</span><span class="t-val">${f.archivo} (${f.cuadrante})</span></div>
    <div class="tel-item"><span class="t-lbl">Pasada / Fotograma</span><span class="t-val">Línea ${f.linea} · #${f.n}/${D.fotos.length}</span></div>
    <div class="tel-item"><span class="t-lbl">Varianza Laplaciana</span><span class="t-val" style="color:${f.nitidez>=120?'var(--accent)':'var(--terracotta)'}">${f.nitidez} (mín 120)</span></div>
    <div class="tel-item"><span class="t-lbl">Coordenadas EXIF</span><span class="t-val">${f.lat.toFixed(6)}, ${f.lon.toFixed(6)}</span></div>
    <div class="tel-item"><span class="t-lbl">Coordenada Local</span><span class="t-val">X ${f.x} m · Y ${f.y} m</span></div>
    <div class="tel-item"><span class="t-lbl">Distancia Acumulada</span><span class="t-val">${f.dist_m} m</span></div>
  `;

  document.querySelectorAll(".sd-item.active").forEach(el => el.classList.remove("active"));
  const card = document.getElementById(`thumb-${idxActual}`);
  if (card) card.classList.add("active");

  if (!usarCanvas && droneMarker) {
    droneMarker.setLatLng([f.lat, f.lon]);
    footprintPoly.setLatLngs(f.huella_esq);
    const col = f.dictamen === "ACEPTADA" ? "#52B788" : "#B84A27";
    footprintPoly.setStyle({ color: col, fillColor: col });
  }
  dibujarCanvas(idxActual);
}

function togglePlay() {
  const btn = document.getElementById("btn-play");
  if (timer) {
    clearInterval(timer);
    timer = null;
    btn.textContent = "Continuar Recorrido";
    return;
  }
  btn.textContent = "Pausar Recorrido";
  const ms = parseInt(document.getElementById("sel-speed").value, 10);
  timer = setInterval(() => {
    if (idxActual >= D.fotos.length - 1) {
      clearInterval(timer);
      timer = null;
      btn.textContent = "Iniciar Recorrido";
      return;
    }
    seleccionarFoto(idxActual + 1);
  }, ms);
}

document.getElementById("btn-play").onclick = togglePlay;
document.getElementById("btn-step-b").onclick = () => seleccionarFoto(idxActual - 1);
document.getElementById("btn-step-f").onclick = () => seleccionarFoto(idxActual + 1);
document.getElementById("btn-reset").onclick = () => { if (timer) togglePlay(); seleccionarFoto(0); };
slider.oninput = (e) => seleccionarFoto(parseInt(e.target.value, 10));
document.getElementById("filtro-qa").onchange = renderGaleria;
document.getElementById("sel-speed").onchange = () => { if (timer) { togglePlay(); togglePlay(); } };
document.getElementById("btn-toggle-vista").onclick = () => {
  usarCanvas = !usarCanvas;
  document.getElementById("map").style.display = usarCanvas ? "none" : "block";
  document.getElementById("canvas-map").style.display = usarCanvas ? "block" : "none";
  document.getElementById("modo-mapa").textContent = usarCanvas ? "Plano Técnico Cenital (Offline)" : "Ortofoto Satelital + Cuadrantes Q1–Q4";
  seleccionarFoto(idxActual);
};

initLeaflet();
if (usarCanvas) {
  document.getElementById("map").style.display = "none";
  document.getElementById("canvas-map").style.display = "block";
}
renderGaleria();
seleccionarFoto(0);
</script>
</body>
</html>
"""

