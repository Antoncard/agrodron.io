# Plantilla HTML/CSS/JS del panel tecnico de AgroDron (sin recursos externos, < 300 lineas)
import json
import os

FONTS_CSS = """/* Fuentes locales con fallback de sistema para modo sin conexion */
:root { --font-serif: 'Instrument Serif', Georgia, 'Times New Roman', serif; --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; --font-mono: 'JetBrains Mono', Consolas, 'Courier New', monospace; }
"""

LEAFLET_CSS = """/* Estilos locales de Leaflet offline para AgroDron */
.leaflet-container { position: relative; width: 100%; height: 100%; background: #1B2A20; overflow: hidden; font-family: var(--font-sans); user-select: none; }
.leaflet-ctrl-zoom { position: absolute; top: 10px; left: 10px; z-index: 20; display: flex; flex-direction: column; border: 1px solid #B5ADA0; border-radius: 4px; overflow: hidden; background: #FCFBF7; }
.leaflet-ctrl-zoom button { border: none; background: #FCFBF7; color: #18221B; width: 28px; height: 28px; font-weight: 700; font-size: 15px; cursor: pointer; border-bottom: 1px solid #D6D0C4; }
.leaflet-ctrl-zoom button:last-child { border-bottom: none; }
.leaflet-ctrl-zoom button:hover { background: #EDE8DC; }
.leaflet-popup-box { position: absolute; bottom: 12px; left: 12px; z-index: 25; background: #16231B; color: #FCFBF7; border: 1px solid #52B788; border-radius: 4px; padding: 6px 10px; font-size: 11px; max-width: 320px; pointer-events: none; }
"""

LEAFLET_JS = """/* Motor cartografico local compatible con API L (Leaflet offline) */
window.L = (function() {
  function LayerGroup() { this.items = []; this.visible = true; }
  LayerGroup.prototype.addTo = function(m) { m._addGroup(this); return this; };
  function Elemento(tipo, coords, opts) { this.tipo = tipo; this.coords = coords; this.opts = opts || {}; this.popup = ""; this.handlers = {}; }
  Elemento.prototype.addTo = function(d) { if (d.items) d.items.push(this); else if (d._addItem) d._addItem(this); return this; };
  Elemento.prototype.bindPopup = function(t) { this.popup = t; return this; };
  Elemento.prototype.on = function(ev, fn) { this.handlers[ev] = fn; return this; };
  Elemento.prototype.setLatLng = function(ll) { this.coords = ll; if (this._map) this._map._draw(); };
  Elemento.prototype.setLatLngs = function(lls) { this.coords = lls; if (this._map) this._map._draw(); };
  function Mapa(id, opts) {
    this.el = document.getElementById(id); this.center = (opts && opts.center) || [5.0949, -75.5891]; this.zoom = (opts && opts.zoom) || 18;
    this.groups = []; this.items = []; this.el.classList.add("leaflet-container");
    this.el.innerHTML = '<canvas class="lf-cv" style="width:100%;height:100%;display:block"></canvas><div class="leaflet-ctrl-zoom"><button type="button" data-z="1">+</button><button type="button" data-z="-1">−</button></div><div class="leaflet-popup-box" style="display:none"></div>';
    this.cv = this.el.querySelector("canvas"); this.popEl = this.el.querySelector(".leaflet-popup-box"); const self = this;
    this.el.querySelectorAll("[data-z]").forEach(function(b) { b.onclick = function() { self.zoom = Math.max(16, Math.min(20, self.zoom + parseInt(b.dataset.z, 10))); self._draw(); }; });
    this.cv.onclick = function(e) { self._click(e); }; window.addEventListener("resize", function() { self._draw(); }); setTimeout(function() { self._draw(); }, 40);
  }
  Mapa.prototype._addGroup = function(g) { this.groups.push(g); this._draw(); };
  Mapa.prototype._addItem = function(it) { it._map = this; this.items.push(it); this._draw(); };
  Mapa.prototype._proj = function(lat, lon, W, H) { const sc = Math.pow(2, this.zoom - 18) * Math.min(W, H) * 3200; return [W / 2 + (lon - this.center[1]) * Math.cos(this.center[0] * Math.PI / 180) * sc, H / 2 - (lat - this.center[0]) * sc]; };
  Mapa.prototype._all = function() { let l = this.items.slice(); this.groups.forEach(function(g) { if (g.visible) l = l.concat(g.items); }); return l; };
  Mapa.prototype._click = function(e) {
    const r = this.cv.getBoundingClientRect(), mx = (e.clientX - r.left) * (this.cv.width / r.width), my = (e.clientY - r.top) * (this.cv.height / r.height), all = this._all();
    for (let i = all.length - 1; i >= 0; i--) { const it = all[i]; if (it.tipo === "circle") { const p = this._proj(it.coords[0], it.coords[1], this.cv.width, this.cv.height); if (Math.hypot(mx - p[0], my - p[1]) <= (it.opts.radius || 6) + 5) { if (it.handlers.click) it.handlers.click(); if (it.popup) { this.popEl.innerHTML = it.popup; this.popEl.style.display = "block"; } return; } } }
  };
  Mapa.prototype._draw = function() {
    const W = this.cv.width = this.el.clientWidth || 800, H = this.cv.height = this.el.clientHeight || 430, ctx = this.cv.getContext("2d"), self = this;
    ctx.fillStyle = "#1B2A20"; ctx.fillRect(0, 0, W, H); ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 1;
    for (let gx = 0; gx < W; gx += 48) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke(); }
    for (let gy = 0; gy < H; gy += 48) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke(); }
    this._all().forEach(function(it) {
      it._map = self;
      if ((it.tipo === "poly" || it.tipo === "line") && it.coords && it.coords.length) {
        ctx.beginPath(); it.coords.forEach(function(ll, idx) { const p = self._proj(ll[0], ll[1], W, H); if (idx === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]); });
        if (it.tipo === "poly") { ctx.closePath(); if (it.opts.fillColor || it.opts.color) { ctx.fillStyle = it.opts.fillColor || it.opts.color; ctx.globalAlpha = it.opts.fillOpacity !== undefined ? it.opts.fillOpacity : 0.15; ctx.fill(); ctx.globalAlpha = 1.0; } }
        ctx.strokeStyle = it.opts.color || "#E9C46A"; ctx.lineWidth = it.opts.weight || 1.8; ctx.setLineDash(it.opts.dashArray ? [4, 4] : []); ctx.stroke(); ctx.setLineDash([]);
      } else if (it.tipo === "circle" && it.coords) {
        const p = self._proj(it.coords[0], it.coords[1], W, H); ctx.beginPath(); ctx.arc(p[0], p[1], it.opts.radius || 5, 0, Math.PI * 2); ctx.fillStyle = it.opts.fillColor || "#2D6A4F"; ctx.fill(); ctx.strokeStyle = it.opts.color || "#FCFBF7"; ctx.lineWidth = it.opts.weight || 1.2; ctx.stroke();
      } else if (it.tipo === "marker" && it.coords) {
        const p = self._proj(it.coords[0], it.coords[1], W, H), txt = (it.opts.icon && it.opts.icon.html) ? it.opts.icon.html.replace(/<[^>]+>/g, "") : "UAV";
        ctx.font = "700 10px monospace"; const tw = ctx.measureText(txt).width + 10; ctx.fillStyle = txt === "UAV" ? "#52B788" : "#16231B"; ctx.fillRect(p[0] - tw / 2, p[1] - 9, tw, 18); ctx.fillStyle = txt === "UAV" ? "#16231B" : "#FCFBF7"; ctx.fillText(txt, p[0] - tw / 2 + 5, p[1] + 3);
      }
    });
  };
  return {
    map: function(id, o) { return new Mapa(id, o); }, tileLayer: function() { return { addTo: function() { return this; } }; },
    layerGroup: function() { return new LayerGroup(); }, polygon: function(c, o) { return new Elemento("poly", c, o); },
    polyline: function(c, o) { return new Elemento("line", c, o); }, circleMarker: function(c, o) { return new Elemento("circle", c, o); },
    marker: function(c, o) { return new Elemento("marker", c, o); }, divIcon: function(o) { return o; },
    control: { layers: function() { return { addTo: function() { return this; } }; } }
  };
})();
"""

PLANTILLA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgroDron · Cuaderno Técnico de Telemetría y Auditoría Óptica — Vereda La Cabaña</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/leaflet.css">
<script src="vendor/leaflet.js"></script>
<style>
  head, title, meta, link, script, style { display: none !important; }
  :root { --bg: #F4F1EA; --surface: #FCFBF7; --surface-alt: #EDE8DC; --surface-dark: #16231B; --border: #D6D0C4; --border-strong: #B5ADA0; --text: #18221B; --text-dim: #5C665E; --accent: #2D6A4F; --accent-light: #E3F0E9; --terracotta: #B84A27; --terracotta-light: #FCECE7; --amber: #9A6700; --amber-light: #FEF3C7; --radius: 6px; }
  * { box-sizing: border-box; } body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--font-sans); font-size: 14px; line-height: 1.5; }
  .top-bar { background: var(--surface-dark); color: #F4F1EA; padding: 12px 28px; border-bottom: 2px solid var(--accent); display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 16px; }
  .brand-block { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; } .brand-title { font-family: var(--font-serif); font-size: 1.6rem; font-weight: 400; margin: 0; color: #FCFBF7; }
  .brand-meta { font-family: var(--font-mono); font-size: 0.74rem; color: #A7B8AD; border-left: 1px solid #354A3D; padding-left: 12px; }
  .ca-strip { display: flex; gap: 6px; flex-wrap: wrap; } .ca-tag { font-family: var(--font-mono); font-size: 0.71rem; padding: 4px 9px; border-radius: 4px; background: #213328; border: 1px solid #354E3E; color: #D2E3D8; }
  .ca-tag.ok { border-color: #2D6A4F; color: #95D5B2; } .ca-tag.warn { border-color: #B84A27; color: #F4A28C; }
  .page-wrap { max-width: 1480px; margin: 0 auto; padding: 20px 28px 40px; }
  .metrics-ribbon { display: grid; grid-template-columns: repeat(6, 1fr); background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 14px; }
  @media (max-width: 1100px) { .metrics-ribbon { grid-template-columns: repeat(3, 1fr); } }
  .metric-cell { padding: 12px 15px; border-right: 1px solid var(--border); } .metric-cell:last-child { border-right: none; }
  .metric-cell .m-label { font-size: 0.69rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); font-weight: 600; }
  .metric-cell .m-val { font-family: var(--font-mono); font-size: 1.12rem; font-weight: 700; margin-top: 3px; } .metric-cell .m-sub { font-size: 0.73rem; color: var(--text-dim); margin-top: 2px; }
  .legend-bar { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 16px; margin-bottom: 18px; font-size: 0.78rem; display: flex; flex-wrap: wrap; gap: 14px; color: var(--text-dim); }
  .legend-bar b { color: var(--text); font-family: var(--font-mono); } .section-bar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
  .section-title { font-family: var(--font-serif); font-size: 1.4rem; font-weight: 400; margin: 0; } .state-pills { display: flex; gap: 6px; flex-wrap: wrap; }
  .btn-tech { background: var(--surface); color: var(--text); border: 1px solid var(--border-strong); padding: 6px 12px; border-radius: 4px; font-size: 0.78rem; font-weight: 600; cursor: pointer; }
  .btn-tech.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
  .walkthrough-wrapper { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; margin-bottom: 20px; overflow-x: auto; }
  .stage { position: relative; width: 960px; height: 420px; margin: 0 auto; background: #F7F4ED; border: 1px solid var(--border-strong); border-radius: 10px; overflow: hidden; }
  .st-header { position: absolute; left: 0; top: 0; width: 960px; height: 46px; background: #16231B; color: #F4F1EA; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; font-family: var(--font-mono); font-size: 0.76rem; }
  .st-cta { padding: 4px 11px; border-radius: 4px; background: var(--terracotta); color: #fff; font-weight: 600; } .stage.optimized .st-cta { background: var(--accent); }
  .st-field { position: absolute; left: 16px; top: 58px; width: 560px; height: 346px; background: #EAE4D7; border: 1px solid var(--border-strong); border-radius: 8px; display: flex; align-items: center; justify-content: center; }
  .st-parcela { width: 280px; height: 280px; background: #28412E; border: 2px solid #16231B; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }
  .st-quad { border: 1px dashed rgba(252,251,247,0.35); padding: 8px; font-family: var(--font-mono); font-size: 0.69rem; color: #FCFBF7; font-weight: 700; display: flex; align-items: flex-start; justify-content: space-between; }
  .st-side { position: absolute; left: 592px; top: 58px; width: 352px; height: 346px; background: var(--surface); border: 1px solid var(--border-strong); border-radius: 8px; padding: 14px; display: flex; flex-direction: column; justify-content: space-between; }
  .st-side h3 { margin: 0 0 6px 0; font-family: var(--font-serif); font-size: 1.12rem; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  .st-spec-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dashed var(--border); font-size: 0.78rem; } .st-spec-val { font-family: var(--font-mono); font-weight: 700; }
  .st-status-box { padding: 8px 10px; border-radius: 6px; background: var(--terracotta-light); border: 1px solid #E6B3A3; color: var(--terracotta); font-family: var(--font-mono); font-size: 0.72rem; }
  .stage.optimized .st-status-box { background: var(--accent-light); border-color: #95D5B2; color: var(--accent); }
  .workspace-grid { display: grid; grid-template-columns: 1.38fr 1fr; gap: 20px; } @media (max-width: 1120px) { .workspace-grid { grid-template-columns: 1fr; } }
  .panel-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 15px 18px; margin-bottom: 18px; }
  .panel-header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 12px; }
  .panel-header h2 { font-family: var(--font-serif); font-size: 1.24rem; font-weight: 400; margin: 0; } .panel-header .meta-note { font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-dim); }
  #map-wrap { position: relative; height: 430px; border-radius: 4px; overflow: hidden; border: 1px solid var(--border-strong); background: #1B2A20; } #map, #canvas-map { width: 100%; height: 100%; } #canvas-map { display: none; }
  .flight-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 10px; padding: 9px 12px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 4px; }
  .flight-controls input[type=range] { flex: 1; min-width: 120px; accent-color: var(--accent); }
  select.tech-select { background: var(--surface); color: var(--text); border: 1px solid var(--border-strong); padding: 5px 9px; border-radius: 4px; font-family: var(--font-mono); font-size: 0.75rem; }
  .inspector-grid { display: grid; grid-template-columns: 220px 1fr; gap: 14px; align-items: start; } .cam-frame { width: 100%; aspect-ratio: 4/3; border: 1px solid var(--border-strong); border-radius: 4px; object-fit: cover; background: #16231B; }
  .tel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; } .tel-item { background: var(--bg); border: 1px solid var(--border); padding: 6px 9px; border-radius: 4px; }
  .tel-item .t-lbl { display: block; font-size: 0.68rem; text-transform: uppercase; color: var(--text-dim); } .tel-item .t-val { font-family: var(--font-mono); font-size: 0.8rem; font-weight: 600; }
  .status-pill { font-family: var(--font-mono); font-size: 0.71rem; font-weight: 700; padding: 3px 8px; border-radius: 3px; }
  .status-pill.ACEPTADA, .status-pill.VERDE { background: var(--accent-light); color: var(--accent); border: 1px solid #95D5B2; }
  .status-pill.AMARILLO { background: var(--amber-light); color: var(--amber); border: 1px solid #FCD34D; }
  .status-pill.RECHAZADA, .status-pill.ROJO { background: var(--terracotta-light); color: var(--terracotta); border: 1px solid #E6B3A3; }
  .sd-gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: 8px; max-height: 320px; overflow-y: auto; }
  .sd-item { background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 5px; cursor: pointer; font-family: var(--font-mono); font-size: 0.69rem; }
  .sd-item.active { border: 2px solid var(--accent); background: var(--accent-light); } .sd-item.RECHAZADA { border-color: #D97757; background: var(--terracotta-light); }
  .sd-item img { width: 100%; aspect-ratio: 4/3; object-fit: cover; border-radius: 2px; display: block; }
  table.tech-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; } table.tech-table th, table.tech-table td { padding: 6px 8px; border-bottom: 1px solid var(--border); text-align: left; }
  table.tech-table th { font-size: 0.69rem; text-transform: uppercase; color: var(--text-dim); background: var(--bg); } table.tech-table td.mono { font-family: var(--font-mono); }
</style>
</head>
<body>
<header class="top-bar"><div class="brand-block"><h1 class="brand-title">AgroDron · Estación de Fotogrametría y Auditoría Óptica</h1><span class="brand-meta" id="hdr-sub"></span></div><div class="ca-strip" id="hdr-badges"></div></header>
<div class="page-wrap">
  <div class="metrics-ribbon" id="kpi-grid"></div>
  <div class="legend-bar">
    <span><b>CA1</b> Calibración GNSS (≥16 sat, ≤1/1000 s)</span><span><b>CA2</b> Cobertura 100% en 4 cuadrantes (50×50 m: Q1 NO, Q2 NE, Q3 SE, Q4 SO)</span>
    <span><b>CA3</b> GSD &lt; 1,0 cm/px (Vuelo a 25 m · cumple: 0,938 cm/px | Vuelo a 30 m · incumple: 1,125 cm/px)</span><span><b>CA4</b> QA Óptico (Laplaciano ≥120 y EXIF GPS)</span>
    <span><b>CA5</b> Conteo de referencia (2.352 plantas)</span><span><b>Épica 2</b> Almacenamiento local con integridad MD5 y manifiesto del lote</span>
  </div>
  <div class="section-bar">
    <h2 class="section-title">Demostración Técnica: Vuelo a 30 m · incumple vs Vuelo a 25 m · cumple</h2>
    <div class="state-pills"><button class="btn-tech primary" id="btn-freeze-after">Vuelo a 25 m · cumple (0,938 cm/px · 228 fotos)</button><button class="btn-tech" id="btn-freeze-before">Vuelo a 30 m · incumple (1,125 cm/px · 160 fotos)</button></div>
  </div>
  <div class="walkthrough-wrapper">
    <div class="stage optimized" id="stage">
      <div class="st-header"><span>VEREDA LA CABAÑA (MANIZALES) · 4 CUADRANTES REALES DE 50×50 M (1,0 HA)</span><div class="st-cta" id="st-cta-btn">Vuelo a 25 m · cumple</div></div>
      <div class="st-field"><div class="st-parcela"><div class="st-quad"><span>Q1 (NO)</span><span>598 pl.</span></div><div class="st-quad"><span>Q2 (NE)</span><span>584 pl.</span></div><div class="st-quad"><span>Q4 (SO)</span><span>591 pl.</span></div><div class="st-quad"><span>Q3 (SE)</span><span>579 pl.</span></div></div></div>
      <div class="st-side">
        <div>
          <h3>Parámetros desde calcular_plan_vuelo</h3>
          <div class="st-spec-row"><span>Altura AGL</span><span class="st-spec-val" id="st-val-alt"></span></div><div class="st-spec-row"><span>GSD en terreno</span><span class="st-spec-val" id="st-val-gsd"></span></div>
          <div class="st-spec-row"><span>Huella por foto</span><span class="st-spec-val" id="st-val-huella"></span></div><div class="st-spec-row"><span>Líneas × Fotos</span><span class="st-spec-val" id="st-val-malla"></span></div>
          <div class="st-spec-row"><span>Intervalo disparo</span><span class="st-spec-val" id="st-val-int"></span></div><div class="st-spec-row"><span>Cobertura parcela</span><span class="st-spec-val" id="st-val-cob"></span></div>
        </div>
        <div class="st-status-box" id="st-status-msg"></div>
      </div>
    </div>
  </div>
  <div class="workspace-grid">
    <div>
      <div class="panel-card">
        <div class="panel-header"><h2>Cartografía Rural y Recorrido del Dron — Vereda La Cabaña</h2><span class="meta-note">Cuadrantes 50×50 m: Q1 NO · Q2 NE · Q3 SE · Q4 SO</span></div>
        <div id="map-wrap"><div id="map"></div><canvas id="canvas-map" width="820" height="430"></canvas></div>
        <div class="flight-controls">
          <button class="btn-tech primary" id="btn-play">Iniciar Recorrido</button><button class="btn-tech" id="btn-step-b">Anterior</button><button class="btn-tech" id="btn-step-f">Siguiente</button><button class="btn-tech" id="btn-reset">Reiniciar</button>
          <input type="range" id="slider-foto" min="0" value="0"><select class="tech-select" id="sel-speed"><option value="700">1x</option><option value="320" selected>2x</option><option value="120">5x</option></select><button class="btn-tech" id="btn-toggle-vista">Alternar Mapa / Plano Cenital</button>
        </div>
      </div>
      <div class="panel-card">
        <div class="panel-header"><h2 id="gal-title">Registro de Capturas en Tarjeta microSD (<span id="gal-count">0</span> archivos)</h2><select class="tech-select" id="filtro-qa"><option value="TODAS">Mostrar todas</option><option value="ACEPTADA">Dictamen: ACEPTADA (≥ 120)</option><option value="RECHAZADA">Dictamen: RECHAZADA</option></select></div>
        <div class="sd-gallery" id="galeria"></div>
      </div>
    </div>
    <div>
      <div class="panel-card"><div class="panel-header"><h2>Inspección Óptica y Telemetría EXIF</h2><span id="cam-badge"></span></div><div class="inspector-grid"><img id="cam-img" class="cam-frame" alt="Fotograma capturado"><div class="tel-grid" id="cam-tel"></div></div></div>
      <div class="panel-card"><div class="panel-header"><h2>Comparativa de Planes de Vuelo</h2><span class="meta-note">Sensor 13,2 mm · Focal 8,8 mm · 4000×3000 px</span></div><table class="tech-table" id="tabla-planes"></table></div>
      <div class="panel-card"><div class="panel-header"><h2>Ortomosaico y Conteo de Referencia (Ground Truth · CA5)</h2><span class="meta-note">4 cuadrantes de 50×50 m (2.500 m² c/u)</span></div><div style="display:grid;grid-template-columns:165px 1fr;gap:14px;align-items:center"><img id="img-orto" style="width:100%;border-radius:4px;border:1px solid var(--border-strong)" alt="Ortomosaico generado por simulador"><table class="tech-table" id="tabla-conteo"></table></div></div>
      <div class="panel-card"><div class="panel-header"><h2>Conteo por cuadrante (Épica 3 · IA)</h2><span class="meta-note">Semáforo provisional PO: ≤5% verde, ≤10% amarillo, &gt;10% rojo</span></div><table class="tech-table" id="tabla-ia"></table></div>
      <div class="panel-card"><div class="panel-header"><h2>Manifiesto del lote (Épica 2)</h2><span class="meta-note">Almacenamiento local + MD5</span></div><div id="box-manifiesto" style="font-size:0.81rem;color:var(--text-dim)"></div></div>
    </div>
  </div>
</div>
<script>
const D = __DATOS_AGRODRON__;
window.D = D;
__SCRIPT_PANEL__
</script>
</body>
</html>
"""

SCRIPT_PANEL = """
document.getElementById("hdr-sub").textContent = `${D.parcela.nombre} · Rumbo: ${D.parcela.rumbo}°${D.es_muestra ? ' · Muestra ('+D.fotos.length+' de '+D.plan_25.total_fotos+' fotos)' : ''}`;
const badges = [{ txt: `CA1 ${D.calibracion.satelites} SAT · ${D.calibracion.obturacion}`, ok: D.calibracion.cumple }, { txt: `CA2 COBERTURA ${D.cobertura.cobertura_pct}%`, ok: D.cobertura.cumple_cobertura }, { txt: `CA3 Vuelo a 25 m · cumple (${D.plan_25.gsd_cm_px} cm/px)`, ok: D.plan_25.cumple_gsd }, { txt: `CA4 QA ${D.qa.aceptadas}/${D.qa.extraidas} OK`, ok: D.qa.aceptadas > 0 }, { txt: `CA5 CONTEO ${D.conteo.conteo} (${D.conteo.porcentaje}%)`, ok: true }];
document.getElementById("hdr-badges").innerHTML = badges.map(b => `<span class="ca-tag ${b.ok ? 'ok' : 'warn'}">${b.txt}</span>`).join("");
const kpis = [{ lbl: "Vuelo a 25 m · cumple", val: `${D.plan_25.altura_m} m · ${D.plan_25.gsd_cm_px} cm/px`, sub: `Vuelo a 30 m · incumple (${D.plan_30.gsd_cm_px} cm/px)` }, { lbl: "Malla Oficial (25 m)", val: `${D.plan_25.lineas} × ${D.plan_25.fotos_por_linea} = ${D.plan_25.total_fotos}`, sub: `Intervalo: ${D.plan_25.intervalo_disparo_s} s · Huella: ${D.plan_25.huella_m[0]}×${D.plan_25.huella_m[1]} m` }, { lbl: "Auditoría Óptica (CA4)", val: `${D.qa.aceptadas} / ${D.qa.extraidas}`, sub: `${D.qa.descartadas} rechazadas · Nitidez: ${D.qa.nitidez_promedio_aceptadas}` }, { lbl: "Cobertura Cuadrantes (CA2)", val: `${D.cobertura.cobertura_pct} %`, sub: `Q1:${D.cobertura.por_cuadrante.Q1} Q2:${D.cobertura.por_cuadrante.Q2} Q3:${D.cobertura.por_cuadrante.Q3} Q4:${D.cobertura.por_cuadrante.Q4}` }, { lbl: "Ground Truth (CA5)", val: `${D.conteo.conteo} pl.`, sub: `Esperadas: ${D.conteo.esperadas} (${D.conteo.diferencia} / ${D.conteo.porcentaje}%)` }, { lbl: "Manifiesto del lote (Épica 2)", val: `${D.manifiesto.archivos.length} archivos`, sub: `${D.manifiesto.ruta_lote}` }];
document.getElementById("kpi-grid").innerHTML = kpis.map(k => `<div class="metric-cell"><div class="m-label">${k.lbl}</div><div class="m-val">${k.val}</div><div class="m-sub">${k.sub}</div></div>`).join("");
document.getElementById("tabla-planes").innerHTML = `<tr><th>Parámetro</th><th>Vuelo a 30 m · incumple</th><th>Vuelo a 25 m · cumple</th></tr><tr><td>GSD en terreno</td><td class="mono" style="color:var(--terracotta);font-weight:700">${D.plan_30.gsd_cm_px} cm/px (Vuelo a 30 m · incumple)</td><td class="mono" style="color:var(--accent);font-weight:700">${D.plan_25.gsd_cm_px} cm/px (Vuelo a 25 m · cumple)</td></tr><tr><td>Huella por foto</td><td class="mono">${D.plan_30.huella_m[0]} × ${D.plan_30.huella_m[1]} m</td><td class="mono">${D.plan_25.huella_m[0]} × ${D.plan_25.huella_m[1]} m</td></tr><tr><td>Líneas × Fotos/línea</td><td class="mono">${D.plan_30.lineas} × ${D.plan_30.fotos_por_linea} (${D.plan_30.total_fotos})</td><td class="mono">${D.plan_25.lineas} × ${D.plan_25.fotos_por_linea} (${D.plan_25.total_fotos})</td></tr><tr><td>Intervalo / Cobertura</td><td class="mono">${D.plan_30.intervalo_disparo_s} s · ${D.cobertura_30_pct}%</td><td class="mono">${D.plan_25.intervalo_disparo_s} s · ${D.cobertura.cobertura_pct}%</td></tr>`;
document.getElementById("img-orto").src = D.ortomosaico_src || "assets/ortomosaico.jpg";
document.getElementById("tabla-conteo").innerHTML = `<tr><th>Cuadrante</th><th>Esperadas</th><th>Ground Truth</th><th>Desviación</th></tr>` + D.conteo.detalle.map(d => `<tr><td class="mono">${d.cuadrante}</td><td class="mono">${d.esperadas}</td><td class="mono">${d.conteo}</td><td class="mono">${d.diferencia} (${d.porcentaje}%)</td></tr>`).join("") + `<tr style="font-weight:700"><td>TOTAL</td><td class="mono">${D.conteo.esperadas}</td><td class="mono">${D.conteo.conteo}</td><td class="mono">${D.conteo.diferencia} (${D.conteo.porcentaje}%)</td></tr>`;
if (D.conteo_ia) { document.getElementById("tabla-ia").innerHTML = `<tr><th>Cuadrante</th><th>Ground Truth</th><th>Detectadas IA</th><th>Error %</th><th>Semáforo</th></tr>` + D.conteo_ia.detalle.map(d => `<tr><td class="mono">${d.cuadrante}</td><td class="mono">${d.ground_truth}</td><td class="mono">${d.detectadas}</td><td class="mono">${d.error_pct}%</td><td><span class="status-pill ${d.semaforo}">${d.semaforo}</span></td></tr>`).join("") + `<tr style="font-weight:700"><td>TOTAL</td><td class="mono">${D.conteo_ia.ground_truth}</td><td class="mono">${D.conteo_ia.detectadas}</td><td class="mono">${D.conteo_ia.error_pct}%</td><td><span class="status-pill ${D.conteo_ia.semaforo}">${D.conteo_ia.semaforo}</span></td></tr>`; }
document.getElementById("box-manifiesto").innerHTML = `<div style="font-family:var(--font-mono);color:var(--text)">${D.manifiesto.ruta_lote}manifiesto.json</div><div style="margin-top:4px">Fotogramas guardados en carpeta local: <b>${D.manifiesto.archivos.length}</b> (${(D.manifiesto.bytes_totales/1024/1024).toFixed(2)} MB) · Integridad verificada con <code>MD5</code>.</div>`;
function mostrarPlanStage(es25) {
  const p = es25 ? D.plan_25 : D.plan_30, cob = es25 ? D.cobertura.cobertura_pct : D.cobertura_30_pct;
  document.getElementById("stage").classList.toggle("optimized", es25);
  document.getElementById("st-cta-btn").textContent = es25 ? "Vuelo a 25 m · cumple" : "Vuelo a 30 m · incumple";
  document.getElementById("st-val-alt").textContent = `${p.altura_m} m`; document.getElementById("st-val-gsd").textContent = `${p.gsd_cm_px} cm/px (${es25 ? 'Vuelo a 25 m · cumple' : 'Vuelo a 30 m · incumple'})`;
  document.getElementById("st-val-huella").textContent = `${p.huella_m[0]} × ${p.huella_m[1]} m`; document.getElementById("st-val-malla").textContent = `${p.lineas} × ${p.fotos_por_linea} (${p.total_fotos} fotos)`;
  document.getElementById("st-val-int").textContent = `${p.intervalo_disparo_s} s`; document.getElementById("st-val-cob").textContent = `${cob} %`;
  document.getElementById("st-status-msg").textContent = es25 ? `Vuelo a 25 m · cumple: GSD ${p.gsd_cm_px} cm/px (< 1,0), ${p.total_fotos} fotos y cobertura ${cob}%.` : `Vuelo a 30 m · incumple: GSD ${p.gsd_cm_px} cm/px (>= 1,0), ${p.total_fotos} fotos. Se corrige a 25 m.`;
}
document.getElementById("btn-freeze-before").onclick = () => mostrarPlanStage(false); document.getElementById("btn-freeze-after").onclick = () => mostrarPlanStage(true); mostrarPlanStage(true);
let usarCanvas = false, map = null, droneMarker = null, footprintPoly = null, idxActual = 0, timer = null;
const slider = document.getElementById("slider-foto"); slider.max = Math.max(0, D.fotos.length - 1);
if (typeof L !== "undefined") {
  map = L.map("map", { center: D.parcela.centro, zoom: 18 });
  const capaQ = L.layerGroup().addTo(map), capaR = L.layerGroup().addTo(map);
  D.parcela.cuadrantes_geo.forEach(q => { L.polygon(q.poly, { color: q.color, weight: 1.5, dashArray: "4,4", fillColor: q.color, fillOpacity: 0.16 }).bindPopup(q.nombre).addTo(capaQ); L.marker(q.label, { icon: L.divIcon({ html: `<div>${q.id}</div>` }) }).addTo(capaQ); });
  L.polyline(D.waypoints.map(w => [w.lat, w.lon]), { color: "#E9C46A", weight: 2, dashArray: "5,5" }).addTo(capaR);
  D.fotos.forEach((f, idx) => { L.circleMarker([f.lat, f.lon], { radius: 4, color: "#FCFBF7", weight: 1, fillColor: f.dictamen === "ACEPTADA" ? "#2D6A4F" : "#B84A27" }).on("click", () => seleccionarFoto(idx)).addTo(capaR); });
  if (D.fotos.length > 0) { footprintPoly = L.polygon(D.fotos[0].huella_esq, { color: "#52B788", weight: 1.8, fillColor: "#52B788", fillOpacity: 0.16 }).addTo(map); droneMarker = L.marker([D.fotos[0].lat, D.fotos[0].lon], { icon: L.divIcon({ html: "<div>UAV</div>" }) }).addTo(map); }
}
function dibujarCanvas(idx) {
  const cv = document.getElementById("canvas-map"), ctx = cv.getContext("2d"), W = cv.width, H = cv.height, pad = 36, side = Math.min(W, H) - pad * 2, ox = (W - side) / 2, oy = (H - side) / 2;
  ctx.fillStyle = "#1E2F23"; ctx.fillRect(0, 0, W, H); ctx.fillStyle = "#28412E"; ctx.fillRect(ox, oy, side, side);
  ctx.strokeStyle = "rgba(252,251,247,0.4)"; ctx.beginPath(); ctx.moveTo(ox + side / 2, oy); ctx.lineTo(ox + side / 2, oy + side); ctx.moveTo(ox, oy + side / 2); ctx.lineTo(ox + side, oy + side / 2); ctx.stroke();
  if (!D.fotos.length) return;
  const f = D.fotos[idx], fx = ox + (f.x / D.parcela.ancho_m) * side, fy = oy + ((D.parcela.largo_m - f.y) / D.parcela.largo_m) * side;
  ctx.strokeStyle = "#52B788"; ctx.strokeRect(fx - 24, fy - 18, 48, 36);
}
function renderGaleria() {
  const gal = document.getElementById("galeria");
  if (!D.fotos.length) {
    document.getElementById("gal-count").textContent = "0";
    gal.innerHTML = `<div style="grid-column:1/-1;padding:18px;color:var(--text-dim)">No hay fotografías en este lote. Ejecuta la captura o simulación para inspeccionar fotogramas.</div>`;
    document.getElementById("cam-badge").innerHTML = `<span class="status-pill AMARILLO">SIN FOTOS</span>`;
    document.getElementById("cam-tel").innerHTML = `<div class="tel-item" style="grid-column:1/-1">Lote vacío: sin fotogramas para mostrar veredictos QA.</div>`;
    return;
  }
  const filtro = document.getElementById("filtro-qa").value, items = D.fotos.map((f, idx) => ({ f, idx })).filter(it => filtro === "TODAS" || it.f.dictamen === filtro);
  document.getElementById("gal-count").textContent = items.length;
  gal.innerHTML = items.map(({ f, idx }) => `<div class="sd-item ${f.dictamen} ${idx === idxActual ? 'active' : ''}" id="thumb-${idx}" onclick="seleccionarFoto(${idx})"><img src="${f.thumb}" alt="${f.archivo}"><div style="display:flex;justify-content:space-between;margin-top:4px;font-weight:700"><span>#${f.n} · ${f.cuadrante}</span><span>${f.nitidez}</span></div><div style="color:var(--text-dim);font-size:0.65rem">${f.dictamen}${f.motivo ? ' · '+f.motivo : ''}</div></div>`).join("");
}
function seleccionarFoto(idx) {
  if (!D.fotos.length) { renderGaleria(); return; }
  idxActual = Math.max(0, Math.min(D.fotos.length - 1, idx)); slider.value = idxActual;
  const f = D.fotos[idxActual];
  document.getElementById("cam-img").src = f.thumb;
  document.getElementById("cam-badge").innerHTML = `<span class="status-pill ${f.dictamen}">${f.dictamen}${f.motivo ? ' · ' + f.motivo : ''}</span>`;
  document.getElementById("cam-tel").innerHTML = `<div class="tel-item"><span class="t-lbl">Archivo / Cuadrante</span><span class="t-val">${f.archivo} (${f.cuadrante})</span></div><div class="tel-item"><span class="t-lbl">Pasada / Fotograma</span><span class="t-val">Línea ${f.linea} · #${f.n}/${D.fotos.length}</span></div><div class="tel-item"><span class="t-lbl">Varianza Laplaciana</span><span class="t-val">${f.nitidez} (mín 120)</span></div><div class="tel-item"><span class="t-lbl">Coordenadas EXIF</span><span class="t-val">${f.lat.toFixed(6)}, ${f.lon.toFixed(6)}</span></div><div class="tel-item"><span class="t-lbl">Coordenada Local</span><span class="t-val">X ${f.x} m · Y ${f.y} m</span></div><div class="tel-item"><span class="t-lbl">Distancia Acumulada</span><span class="t-val">${f.dist_m} m</span></div>`;
  document.querySelectorAll(".sd-item.active").forEach(el => el.classList.remove("active"));
  const card = document.getElementById(`thumb-${idxActual}`); if (card) card.classList.add("active");
  if (droneMarker && footprintPoly) { droneMarker.setLatLng([f.lat, f.lon]); footprintPoly.setLatLngs(f.huella_esq); }
  dibujarCanvas(idxActual);
}
document.getElementById("btn-play").onclick = () => {
  if (!D.fotos.length) return;
  const btn = document.getElementById("btn-play");
  if (timer) { clearInterval(timer); timer = null; btn.textContent = "Continuar Recorrido"; return; }
  btn.textContent = "Pausar Recorrido";
  timer = setInterval(() => { if (idxActual >= D.fotos.length - 1) { clearInterval(timer); timer = null; btn.textContent = "Iniciar Recorrido"; return; } seleccionarFoto(idxActual + 1); }, parseInt(document.getElementById("sel-speed").value, 10));
};
document.getElementById("btn-step-b").onclick = () => seleccionarFoto(idxActual - 1);
document.getElementById("btn-step-f").onclick = () => seleccionarFoto(idxActual + 1);
document.getElementById("btn-reset").onclick = () => seleccionarFoto(0);
slider.oninput = e => seleccionarFoto(parseInt(e.target.value, 10));
document.getElementById("filtro-qa").onchange = renderGaleria;
document.getElementById("btn-toggle-vista").onclick = () => { usarCanvas = !usarCanvas; document.getElementById("map").style.display = usarCanvas ? "none" : "block"; document.getElementById("canvas-map").style.display = usarCanvas ? "block" : "none"; seleccionarFoto(idxActual); };
renderGaleria(); seleccionarFoto(0);
"""


def instalar_vendor(carpeta_web):
    vendor_dir = os.path.join(carpeta_web, "vendor")
    os.makedirs(vendor_dir, exist_ok=True)
    for nombre, contenido in (("fonts.css", FONTS_CSS), ("leaflet.css", LEAFLET_CSS), ("leaflet.js", LEAFLET_JS)):
        with open(os.path.join(vendor_dir, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)


def escribir_panel_html(ruta_html, datos):
    carpeta_web = os.path.dirname(os.path.abspath(ruta_html))
    os.makedirs(carpeta_web, exist_ok=True)
    instalar_vendor(carpeta_web)
    html = PLANTILLA_HTML.replace("__DATOS_AGRODRON__", json.dumps(datos, ensure_ascii=False)).replace("__SCRIPT_PANEL__", SCRIPT_PANEL)
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)
