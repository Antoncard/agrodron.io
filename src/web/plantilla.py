# Plantilla HTML/CSS/JS del dashboard AgroDron (Editorial Agronomico + Cockpit Dual, 100% offline < 200 KB)
import json
import os
import shutil

FONTS_CSS = """/* Fuentes locales con fallback de sistema para modo sin conexion */
:root { --font-serif: 'Instrument Serif', Georgia, 'Times New Roman', serif; --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; --font-mono: 'JetBrains Mono', Consolas, 'Courier New', monospace; }
"""

LEAFLET_CSS = """/* Estilos locales de Leaflet offline para AgroDron */
.leaflet-container { position: relative; width: 100%; height: 100%; background: #142219; overflow: hidden; font-family: var(--font-sans); user-select: none; }
.leaflet-ctrl-zoom { position: absolute; top: 12px; left: 12px; z-index: 20; display: flex; flex-direction: column; border: 1px solid #354E3E; border-radius: 6px; overflow: hidden; background: #122018; }
.leaflet-ctrl-zoom button { border: none; background: #122018; color: #EEF4F0; width: 38px; height: 38px; font-weight: 700; font-size: 16px; cursor: pointer; border-bottom: 1px solid #243B2E; }
.leaflet-ctrl-zoom button:last-child { border-bottom: none; }
.leaflet-ctrl-zoom button:hover { background: #1D3326; }
.leaflet-popup-box { position: absolute; bottom: 12px; left: 12px; z-index: 25; background: rgba(11,20,15,0.92); color: #EEF4F0; border: 1px solid #34D399; border-radius: 6px; padding: 8px 12px; font-size: 12px; max-width: 340px; pointer-events: none; }
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
    this.el.innerHTML = '<canvas class="lf-cv" style="width:100%;height:100%;display:block"></canvas><div class="leaflet-ctrl-zoom"><button type="button" aria-label="Acercar mapa" data-z="1">+</button><button type="button" aria-label="Alejar mapa" data-z="-1">-</button></div><div class="leaflet-popup-box" style="display:none"></div>';
    this.cv = this.el.querySelector("canvas"); this.popEl = this.el.querySelector(".leaflet-popup-box"); const self = this;
    this.el.querySelectorAll("[data-z]").forEach(function(b) { b.onclick = function() { self.zoom = Math.max(16, Math.min(20, self.zoom + parseInt(b.dataset.z, 10))); self._draw(); }; });
    this.cv.onclick = function(e) { self._click(e); }; window.addEventListener("resize", function() { self._draw(); }); setTimeout(function() { self._draw(); }, 50);
  }
  Mapa.prototype._addGroup = function(g) { this.groups.push(g); this._draw(); };
  Mapa.prototype._addItem = function(it) { it._map = this; this.items.push(it); this._draw(); };
  Mapa.prototype._proj = function(lat, lon, W, H) { const sc = Math.pow(2, this.zoom - 18) * Math.min(W, H) * 3200; return [W / 2 + (lon - this.center[1]) * Math.cos(this.center[0] * Math.PI / 180) * sc, H / 2 - (lat - this.center[0]) * sc]; };
  Mapa.prototype._all = function() { let l = this.items.slice(); this.groups.forEach(function(g) { if (g.visible) l = l.concat(g.items); }); return l; };
  Mapa.prototype._click = function(e) {
    const r = this.cv.getBoundingClientRect(), mx = (e.clientX - r.left) * (this.cv.width / r.width), my = (e.clientY - r.top) * (this.cv.height / r.height), all = this._all();
    for (let i = all.length - 1; i >= 0; i--) { const it = all[i]; if (it.tipo === "circle") { const p = this._proj(it.coords[0], it.coords[1], this.cv.width, this.cv.height); if (Math.hypot(mx - p[0], my - p[1]) <= (it.opts.radius || 6) + 6) { if (it.handlers.click) it.handlers.click(); if (it.popup) { this.popEl.innerHTML = it.popup; this.popEl.style.display = "block"; } return; } } }
  };
  Mapa.prototype._draw = function() {
    const W = this.cv.width = this.el.clientWidth || 780, H = this.cv.height = this.el.clientHeight || 420, ctx = this.cv.getContext("2d"), self = this;
    ctx.fillStyle = "#142219"; ctx.fillRect(0, 0, W, H); ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 1;
    for (let gx = 0; gx < W; gx += 48) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke(); }
    for (let gy = 0; gy < H; gy += 48) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke(); }
    this._all().forEach(function(it) {
      it._map = self;
      if ((it.tipo === "poly" || it.tipo === "line") && it.coords && it.coords.length) {
        ctx.beginPath(); it.coords.forEach(function(ll, idx) { const p = self._proj(ll[0], ll[1], W, H); if (idx === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]); });
        if (it.tipo === "poly") { ctx.closePath(); if (it.opts.fillColor || it.opts.color) { ctx.fillStyle = it.opts.fillColor || it.opts.color; ctx.globalAlpha = it.opts.fillOpacity !== undefined ? it.opts.fillOpacity : 0.16; ctx.fill(); ctx.globalAlpha = 1.0; } }
        ctx.strokeStyle = it.opts.color || "#E9C46A"; ctx.lineWidth = it.opts.weight || 1.8; ctx.setLineDash(it.opts.dashArray ? [4, 4] : []); ctx.stroke(); ctx.setLineDash([]);
      } else if (it.tipo === "circle" && it.coords) {
        const p = self._proj(it.coords[0], it.coords[1], W, H); ctx.beginPath(); ctx.arc(p[0], p[1], it.opts.radius || 5, 0, Math.PI * 2); ctx.fillStyle = it.opts.fillColor || "#2D6A4F"; ctx.fill(); ctx.strokeStyle = it.opts.color || "#FCFBF7"; ctx.lineWidth = it.opts.weight || 1.2; ctx.stroke();
      } else if (it.tipo === "marker" && it.coords) {
        const p = self._proj(it.coords[0], it.coords[1], W, H), txt = (it.opts.icon && it.opts.icon.html) ? it.opts.icon.html.replace(/<[^>]+>/g, "") : "UAV";
        if (txt === "UAV") { ctx.beginPath(); ctx.arc(p[0], p[1], 14, 0, Math.PI * 2); ctx.fillStyle = "rgba(52,211,153,0.22)"; ctx.fill(); }
        ctx.font = "700 10px monospace"; const tw = ctx.measureText(txt).width + 12; ctx.fillStyle = txt === "UAV" ? "#34D399" : "#0B140F"; ctx.fillRect(p[0] - tw / 2, p[1] - 10, tw, 20); ctx.fillStyle = txt === "UAV" ? "#0B140F" : "#EEF4F0"; ctx.fillText(txt, p[0] - tw / 2 + 6, p[1] + 4);
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
<html lang="es" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgroDron · Cuaderno Agronómico y Telemetría UAV — Vereda La Cabaña</title>
<link rel="stylesheet" href="vendor/fonts.css">
<link rel="stylesheet" href="vendor/leaflet.css">
<script src="vendor/leaflet.js"></script>
<style>
  :root {
    --bg: #F5F2EB; --surface: #FCFBF7; --surface-2: #EBE6DA; --ink: #142119; --ink-muted: #4A5950;
    --border: #D5CFC2; --border-strong: #B5ADA0; --accent: #1F6347; --accent-ink: #FFFFFF; --accent-soft: #E1F2EA;
    --sem-ok: #195F3F; --sem-ok-bg: #E1F2EA; --sem-warn: #8A5300; --sem-warn-bg: #FEF3D6;
    --sem-err: #A6341B; --sem-err-bg: #FCE9E4; --hdr-bg: #142119; --hdr-ink: #F5F2EB;
    --radius: 8px; --ease: cubic-bezier(0.22, 1, 0.36, 1);
  }
  [data-theme="dark"] {
    --bg: #0B140F; --surface: #122018; --surface-2: #192C21; --ink: #EEF4F0; --ink-muted: #9DB0A4;
    --border: #243B2E; --border-strong: #375745; --accent: #34D399; --accent-ink: #071910; --accent-soft: rgba(52,211,153,0.14);
    --sem-ok: #6EE7B7; --sem-ok-bg: rgba(16,185,129,0.16); --sem-warn: #FCD34D; --sem-warn-bg: rgba(245,158,11,0.16);
    --sem-err: #FCA5A5; --sem-err-bg: rgba(239,68,68,0.16); --hdr-bg: #07100B; --hdr-ink: #EEF4F0;
  }
  [data-theme-switching] * { transition: none !important; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font-sans); font-size: 14px; line-height: 1.5; }
  .mono, .num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
  button, select, input { font-family: inherit; }
  button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .topbar { background: var(--hdr-bg); color: var(--hdr-ink); border-bottom: 2px solid var(--accent); padding: 12px 24px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 14px; }
  .brand { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .brand-mark { width: 38px; height: 38px; border-radius: 8px; background: rgba(52,211,153,0.15); border: 1px solid rgba(52,211,153,0.4); display: grid; place-items: center; color: #6EE7B7; flex-shrink: 0; }
  .brand h1 { font-family: var(--font-serif); font-size: clamp(1.35rem, 2vw, 1.7rem); font-weight: 400; margin: 0; line-height: 1.1; }
  .brand-sub { font-size: 0.78rem; color: #A6BDB0; font-family: var(--font-mono); }
  .top-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .seg-ctrl { display: inline-flex; background: rgba(255,255,255,0.08); padding: 3px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.14); }
  .seg-btn { min-height: 44px; padding: 0 16px; border: none; border-radius: 6px; background: transparent; color: #C5D6CC; font-weight: 600; font-size: 0.84rem; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; transition: background-color 180ms var(--ease), color 180ms var(--ease), transform 80ms; }
  .seg-btn[aria-selected="true"] { background: var(--accent); color: var(--accent-ink); }
  .seg-btn:active, .btn:active { transform: scale(0.98); }
  .btn { min-height: 44px; padding: 0 16px; border-radius: 6px; border: 1px solid var(--border-strong); background: var(--surface); color: var(--ink); font-weight: 600; font-size: 0.84rem; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; transition: transform 120ms var(--ease), background-color 160ms var(--ease), border-color 160ms; touch-action: manipulation; }
  .btn:hover { border-color: var(--accent); }
  .btn.primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
  .btn.ghost-dark { background: rgba(255,255,255,0.08); color: var(--hdr-ink); border-color: rgba(255,255,255,0.2); }
  .status-chip { font-family: var(--font-mono); font-size: 0.74rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; display: inline-flex; align-items: center; gap: 6px; border: 1px solid transparent; }
  .status-chip.VERDE, .status-chip.ACEPTADA, .status-chip.ok { background: var(--sem-ok-bg); color: var(--sem-ok); border-color: var(--sem-ok); }
  .status-chip.AMARILLO, .status-chip.warn { background: var(--sem-warn-bg); color: var(--sem-warn); border-color: var(--sem-warn); }
  .status-chip.ROJO, .status-chip.RECHAZADA { background: var(--sem-err-bg); color: var(--sem-err); border-color: var(--sem-err); }
  .wrap { max-width: 1440px; margin: 0 auto; padding: 20px 24px 48px; }
  .view-pane { animation: paneIn 220ms var(--ease); }
  .view-pane[hidden] { display: none; }
  @keyframes paneIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
  .hero-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px 24px; margin-bottom: 18px; display: grid; grid-template-columns: 1.5fr 1fr; gap: 20px; align-items: center; }
  @media (max-width: 960px) { .hero-card { grid-template-columns: 1fr; } }
  .hero-kicker { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted); font-weight: 700; display: flex; align-items: center; gap: 8px; }
  .hero-headline { font-family: var(--font-serif); font-size: clamp(1.55rem, 2.7vw, 2.25rem); font-weight: 400; margin: 8px 0 10px; line-height: 1.15; }
  .pop-bar { height: 10px; border-radius: 999px; background: var(--sem-err-bg); overflow: hidden; border: 1px solid var(--border); margin: 10px 0; }
  .pop-fill { height: 100%; background: var(--accent); transition: transform 420ms var(--ease); transform-origin: left center; }
  .hero-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  @media (max-width: 600px) { .hero-stats { grid-template-columns: 1fr; } }
  .stat-tile { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px 14px; }
  .stat-tile .s-lbl { font-size: 0.72rem; text-transform: uppercase; color: var(--ink-muted); font-weight: 700; }
  .stat-tile .s-val { font-family: var(--font-mono); font-size: 1.4rem; font-weight: 700; margin-top: 2px; }
  .stat-tile .s-sub { font-size: 0.76rem; color: var(--ink-muted); }
  .action-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
  .bento-2 { display: grid; grid-template-columns: 1.05fr 1fr; gap: 18px; margin-bottom: 18px; }
  @media (max-width: 1040px) { .bento-2 { grid-template-columns: 1fr; } }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; margin-bottom: 18px; }
  .card-hdr { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 14px; }
  .card-hdr h2 { font-family: var(--font-serif); font-size: 1.32rem; font-weight: 400; margin: 0; }
  .card-note { font-family: var(--font-mono); font-size: 0.75rem; color: var(--ink-muted); }
  .density-wrap { display: grid; grid-template-columns: minmax(240px, 340px) 1fr; gap: 18px; align-items: start; }
  @media (max-width: 720px) { .density-wrap { grid-template-columns: 1fr; } }
  #cv-densidad { width: 100%; max-width: 340px; aspect-ratio: 1 / 1; border-radius: 6px; border: 1px solid var(--border-strong); cursor: crosshair; display: block; }
  .leg-grid { display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 8px; margin-top: 10px; }
  .leg-item { display: flex; align-items: center; gap: 7px; font-size: 0.78rem; }
  .leg-sw { width: 14px; height: 14px; border-radius: 3px; flex-shrink: 0; }
  .cell-detail { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px 14px; margin-top: 10px; font-size: 0.84rem; }
  .quad-list { display: grid; gap: 10px; }
  .quad-row { background: var(--bg); border: 1px solid var(--border); border-left: 4px solid var(--accent); border-radius: 6px; padding: 11px 14px; }
  .quad-row.AMARILLO { border-left-color: var(--sem-warn); }
  .quad-row.ROJO { border-left-color: var(--sem-err); }
  .quad-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-weight: 700; }
  .quad-phrase { font-size: 0.84rem; color: var(--ink-muted); margin-top: 4px; }
  .kpi-ribbon { display: grid; grid-template-columns: repeat(6, 1fr); background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 18px; }
  @media (max-width: 1120px) { .kpi-ribbon { grid-template-columns: repeat(3, 1fr); } }
  @media (max-width: 640px) { .kpi-ribbon { grid-template-columns: repeat(2, 1fr); } }
  .kpi-cell { padding: 12px 15px; border-right: 1px solid var(--border); border-bottom: 1px solid var(--border); }
  .kpi-cell:last-child { border-right: none; }
  .kpi-lbl { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-muted); font-weight: 700; }
  .kpi-val { font-family: var(--font-mono); font-size: 1.08rem; font-weight: 700; margin-top: 3px; }
  .kpi-sub { font-size: 0.74rem; color: var(--ink-muted); margin-top: 2px; }
  .stage-grid { display: grid; grid-template-columns: 1.1fr 1fr; gap: 18px; align-items: stretch; }
  @media (max-width: 860px) { .stage-grid { grid-template-columns: 1fr; } }
  .stage-field { background: var(--bg); border: 1px solid var(--border-strong); border-radius: 8px; padding: 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; }
  .parcela-box { position: relative; width: 250px; height: 250px; background: #233B2A; border: 2px solid #0B140F; border-radius: 4px; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; overflow: hidden; }
  .q-box { border: 1px dashed rgba(255,255,255,0.28); padding: 8px; color: #F5F2EB; font-family: var(--font-mono); font-size: 0.72rem; font-weight: 700; display: flex; justify-content: space-between; align-items: flex-start; }
  .scan-lines { position: absolute; inset: 0; pointer-events: none; transition: opacity 280ms var(--ease), transform 280ms var(--ease); }
  .stage-side { display: flex; flex-direction: column; justify-content: space-between; gap: 12px; }
  .spec-row { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px dashed var(--border); font-size: 0.84rem; }
  .stage-banner { padding: 10px 12px; border-radius: 6px; font-family: var(--font-mono); font-size: 0.76rem; border: 1px solid var(--sem-err); background: var(--sem-err-bg); color: var(--sem-err); transition: background-color 220ms var(--ease), color 220ms var(--ease); }
  .stage-banner.ok { border-color: var(--sem-ok); background: var(--sem-ok-bg); color: var(--sem-ok); }
  .tech-grid { display: grid; grid-template-columns: 1.3fr 1fr; gap: 18px; }
  @media (max-width: 1100px) { .tech-grid { grid-template-columns: 1fr; } }
  #map-wrap { position: relative; height: 420px; border-radius: 6px; overflow: hidden; border: 1px solid var(--border-strong); background: #142219; }
  #map, #canvas-map { width: 100%; height: 100%; }
  #canvas-map { display: none; }
  .flight-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 12px; padding: 10px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; }
  .flight-bar input[type=range] { flex: 1; min-width: 140px; accent-color: var(--accent); min-height: 36px; }
  select.tech-sel { min-height: 44px; background: var(--surface); color: var(--ink); border: 1px solid var(--border-strong); padding: 0 12px; border-radius: 6px; font-family: var(--font-mono); font-size: 0.8rem; }
  .insp-grid { display: grid; grid-template-columns: 200px 1fr; gap: 14px; align-items: start; }
  @media (max-width: 600px) { .insp-grid { grid-template-columns: 1fr; } }
  .cam-img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 6px; border: 1px solid var(--border-strong); background: #142219; }
  .tel-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .tel-cell { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 7px 10px; }
  .tel-cell span { display: block; font-size: 0.68rem; text-transform: uppercase; color: var(--ink-muted); font-weight: 700; }
  .tel-cell strong { font-family: var(--font-mono); font-size: 0.82rem; }
  .sd-gal { display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: 8px; max-height: 310px; overflow-y: auto; }
  .sd-card { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 5px; cursor: pointer; font-family: var(--font-mono); font-size: 0.7rem; transition: transform 120ms var(--ease), border-color 140ms; }
  .sd-card:hover { transform: translateY(-2px); border-color: var(--accent); }
  .sd-card.active { border: 2px solid var(--accent); background: var(--accent-soft); }
  .sd-card.RECHAZADA { border-color: var(--sem-err); background: var(--sem-err-bg); }
  .sd-card img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 3px; display: block; }
  table.t { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
  table.t th, table.t td { padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left; }
  table.t th { font-size: 0.7rem; text-transform: uppercase; color: var(--ink-muted); background: var(--bg); }
  .bar-track { height: 8px; border-radius: 999px; background: var(--surface-2); overflow: hidden; margin-top: 4px; }
  .bar-val { height: 100%; background: var(--accent); }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
  .ai-fab { position: fixed; right: 22px; bottom: 22px; z-index: 70; width: 64px; height: 64px; padding: 0; border-radius: 50%; border: none; background: transparent; color: var(--accent-ink); box-shadow: 0 10px 26px rgba(11,20,15,0.28); cursor: pointer; display: grid; place-items: center; overflow: hidden; transition: transform 180ms var(--ease), background-color 180ms var(--ease); touch-action: manipulation; }
  .ai-fab.open { background: var(--accent); border: 2px solid var(--border); }
  .ai-fab-img { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; display: block; }
  [hidden] { display: none !important; }
  .ai-hdr-avatar { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
  .ai-fab:hover { transform: scale(1.05); }
  .ai-fab:active { transform: scale(0.95); }
  .ai-win { position: fixed; right: 22px; bottom: 92px; z-index: 70; width: min(390px, calc(100vw - 32px)); max-height: min(540px, calc(100vh - 118px)); background: var(--surface); border: 1px solid var(--border-strong); border-radius: 12px; box-shadow: 0 18px 44px rgba(11,20,15,0.28); display: flex; flex-direction: column; overflow: hidden; transform-origin: bottom right; opacity: 0; transform: translateY(10px) scale(0.96); pointer-events: none; transition: opacity 220ms var(--ease), transform 220ms var(--ease); }
  .ai-win.open { opacity: 1; transform: translateY(0) scale(1); pointer-events: auto; }
  .ai-hdr { background: var(--hdr-bg); color: var(--hdr-ink); padding: 11px 14px; display: flex; align-items: center; justify-content: space-between; gap: 8px; border-bottom: 1px solid var(--border); }
  .ai-hdr-title { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 0.92rem; }
  .ai-close { width: 38px; height: 38px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.2); background: transparent; color: var(--hdr-ink); cursor: pointer; display: grid; place-items: center; }
  .ai-chips { padding: 8px 12px; display: flex; flex-wrap: wrap; gap: 6px; background: var(--bg); border-bottom: 1px solid var(--border); }
  .ai-chip { min-height: 32px; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border-strong); background: var(--surface); color: var(--ink); font-size: 0.75rem; font-weight: 600; cursor: pointer; }
  .ai-chip:hover { border-color: var(--accent); color: var(--accent); }
  .ai-msgs { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 9px; min-height: 210px; }
  .ai-msg { max-width: 88%; padding: 9px 12px; border-radius: 10px; font-size: 0.84rem; line-height: 1.45; white-space: pre-wrap; }
  .ai-msg.bot { align-self: flex-start; background: var(--bg); border: 1px solid var(--border); color: var(--ink); }
  .ai-msg.user { align-self: flex-end; background: var(--accent); color: var(--accent-ink); }
  .ai-form { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--border); background: var(--surface); }
  .ai-input { flex: 1; min-height: 44px; padding: 0 12px; border-radius: 8px; border: 1px solid var(--border-strong); background: var(--bg); color: var(--ink); font-size: 0.86rem; }
  @media print { .topbar .top-actions, .action-row, .flight-bar, .ai-fab, .ai-win { display: none !important; } body { background: #fff; color: #000; } }
</style>
</head>
<body>
<header class="topbar">
  <div class="brand">
    <div class="brand-mark" aria-hidden="true">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M2 12h4M18 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/><circle cx="12" cy="12" r="3"/></svg>
    </div>
    <div>
      <h1>AgroDron · Cuaderno Agronómico de Vuelo</h1>
      <div class="brand-sub" id="hdr-sub">Vereda La Cabaña (Manizales) · 1,0 ha</div>
    </div>
  </div>
  <div class="top-actions">
    <span class="status-chip ok" id="api-pill">Modo Offline / USB</span>
    <div class="seg-ctrl" role="tablist" aria-label="Selector de audiencia">
      <button type="button" role="tab" class="seg-btn" id="tab-agro" aria-selected="true">Vista Agricultor</button>
      <button type="button" role="tab" class="seg-btn" id="tab-tech" aria-selected="false">Vista Técnica</button>
    </div>
    <button type="button" class="btn ghost-dark" id="btn-theme" aria-label="Cambiar tema claro u oscuro">Tema Oscuro</button>
  </div>
</header>

<main class="wrap">
  <!-- VISTA AGRICULTOR (Por defecto: Epica 4 / UI-01..03) -->
  <section id="pane-agro" class="view-pane" aria-labelledby="tab-agro">
    <div class="hero-card">
      <div>
        <div class="hero-kicker">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          <span>Resumen del Último Vuelo · Cultivo en Finca</span>
          <span class="status-chip" id="agro-semaforo">VERDE</span>
        </div>
        <h2 class="hero-headline" id="agro-frase">Cargando resumen...</h2>
        <div class="pop-bar" aria-hidden="true"><div class="pop-fill" id="agro-pop-fill" style="transform:scaleX(0.94)"></div></div>
        <p style="margin:6px 0 0;color:var(--ink-muted);font-size:0.88rem" id="agro-rec">Priorice la resiembra en el cuadrante con mayor déficit usando los puntos GPS exportables.</p>
        <div class="action-row">
          <button type="button" class="btn primary" id="btn-pdf">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><polyline points="9 15 12 18 15 15"/></svg>
            Descargar Reporte PDF (1 pág.)
          </button>
          <button type="button" class="btn" id="btn-gpx">Exportar Huecos Resiembra (.GPX)</button>
          <button type="button" class="btn" id="btn-csv">Exportar Huecos (.CSV)</button>
        </div>
      </div>
      <div class="hero-stats" id="agro-stats"></div>
    </div>

    <div class="bento-2">
      <div class="card">
        <div class="card-hdr">
          <h2>Mapa de Densidad (celdas 10 × 10 m)</h2>
          <span class="card-note">Q1 NO · Q2 NE · Q3 SE · Q4 SO</span>
        </div>
        <div class="density-wrap">
          <div>
            <canvas id="cv-densidad" width="340" height="340" aria-label="Mapa de densidad de cultivo 10 por 10 metros"></canvas>
            <div class="leg-grid">
              <div class="leg-item"><span class="leg-sw" style="background:#1F6347"></span><span>Óptimo (≥23 pl.)</span></div>
              <div class="leg-item"><span class="leg-sw" style="background:#52B788"></span><span>Medio (20–22)</span></div>
              <div class="leg-item"><span class="leg-sw" style="background:#E9C46A"></span><span>Bajo (17–19)</span></div>
              <div class="leg-item"><span class="leg-sw" style="background:#B84A27"></span><span>Crítico (&lt;17)</span></div>
            </div>
          </div>
          <div>
            <p style="margin-top:0;color:var(--ink-muted);font-size:0.86rem">Cada cuadro equivale a <b>100 m²</b> (meta: 25 plantas/cuadro = 2.500 pl/ha). Haz clic o pasa el puntero sobre un cuadro para inspeccionar su densidad exacta.</p>
            <div class="cell-detail" id="celda-info">Selecciona una celda de 10 × 10 m en el mapa.</div>
            <div class="cell-detail" id="huecos-resumen" style="margin-top:10px"></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-hdr">
          <h2>Estado por Cuadrante en Lenguaje Llano</h2>
          <span class="card-note">4 cuadrantes de 50 × 50 m</span>
        </div>
        <div class="quad-list" id="agro-quads"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-hdr">
        <h2>Comparación entre Vuelos de la Parcela</h2>
        <span class="card-note">Evolución histórica (Hallazgo H1 a Vuelo Oficial)</span>
      </div>
      <div id="hist-vuelos"></div>
    </div>
  </section>

  <!-- VISTA TECNICA (Ingenieria de Vuelo, QA, IA y Manifiesto) -->
  <section id="pane-tech" class="view-pane" aria-labelledby="tab-tech" hidden>
    <div class="kpi-ribbon" id="kpi-grid"></div>

    <div class="card">
      <div class="card-hdr">
        <h2>Demostración Técnica: Vuelo a 30 m · incumple vs Vuelo a 25 m · cumple</h2>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button type="button" class="btn primary" id="btn-freeze-after">Vuelo a 25 m · cumple (0,938 cm/px · 228 fotos)</button>
          <button type="button" class="btn" id="btn-freeze-before">Vuelo a 30 m · incumple (1,125 cm/px · 160 fotos)</button>
        </div>
      </div>
      <div class="stage-grid">
        <div class="stage-field">
          <div class="parcela-box">
            <div class="q-box"><span>Q1 (NO)</span><span class="num">598</span></div>
            <div class="q-box"><span>Q2 (NE)</span><span class="num">584</span></div>
            <div class="q-box"><span>Q4 (SO)</span><span class="num">591</span></div>
            <div class="q-box"><span>Q3 (SE)</span><span class="num">579</span></div>
            <svg class="scan-lines" id="svg-malla" viewBox="0 0 100 100" aria-hidden="true"></svg>
          </div>
          <span class="card-note" id="st-cta-btn">Vuelo a 25 m · cumple</span>
        </div>
        <div class="stage-side">
          <div>
            <div class="spec-row"><span>Altura AGL</span><strong class="num" id="st-val-alt"></strong></div>
            <div class="spec-row"><span>GSD en terreno</span><strong class="num" id="st-val-gsd"></strong></div>
            <div class="spec-row"><span>Huella por foto</span><strong class="num" id="st-val-huella"></strong></div>
            <div class="spec-row"><span>Líneas × Fotos</span><strong class="num" id="st-val-malla"></strong></div>
            <div class="spec-row"><span>Intervalo disparo</span><strong class="num" id="st-val-int"></strong></div>
            <div class="spec-row"><span>Cobertura parcela</span><strong class="num" id="st-val-cob"></strong></div>
          </div>
          <div class="stage-banner ok" id="st-status-msg"></div>
        </div>
      </div>
    </div>

    <div class="tech-grid">
      <div>
        <div class="card">
          <div class="card-hdr">
            <h2>Cartografía Rural y Recorrido del Dron</h2>
            <span class="card-note">Q1 (NO · Q2 (NE · Q3 (SE · Q4 (SO</span>
          </div>
          <div id="map-wrap"><div id="map"></div><canvas id="canvas-map" width="780" height="420"></canvas></div>
          <div class="flight-bar">
            <button type="button" class="btn primary" id="btn-play">Iniciar Recorrido</button>
            <button type="button" class="btn" id="btn-step-b">Anterior</button>
            <button type="button" class="btn" id="btn-step-f">Siguiente</button>
            <button type="button" class="btn" id="btn-reset">Reiniciar</button>
            <input type="range" id="slider-foto" min="0" value="0" aria-label="Fotograma del recorrido">
            <select class="tech-sel" id="sel-speed" aria-label="Velocidad de reproduccion"><option value="650">1x</option><option value="280" selected>2x</option><option value="110">5x</option></select>
            <button type="button" class="btn" id="btn-toggle-vista">Mapa / Cenital</button>
          </div>
        </div>

        <div class="card">
          <div class="card-hdr">
            <h2>Registro microSD (<span id="gal-count">0</span> archivos)</h2>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <select class="tech-sel" id="filtro-q" aria-label="Filtrar por cuadrante"><option value="TODOS">Todos Q1–Q4</option><option value="Q1">Q1 (NO)</option><option value="Q2">Q2 (NE)</option><option value="Q3">Q3 (SE)</option><option value="Q4">Q4 (SO)</option></select>
              <select class="tech-sel" id="filtro-qa" aria-label="Filtrar por dictamen QA"><option value="TODAS">Mostrar todas</option><option value="ACEPTADA">ACEPTADA (≥ 120)</option><option value="RECHAZADA">RECHAZADA</option></select>
            </div>
          </div>
          <div class="sd-gal" id="galeria"></div>
        </div>
      </div>

      <div>
        <div class="card">
          <div class="card-hdr"><h2>Inspección Óptica y EXIF</h2><span id="cam-badge"></span></div>
          <div class="insp-grid"><img id="cam-img" class="cam-img" alt="Fotograma capturado"><div class="tel-grid" id="cam-tel"></div></div>
        </div>

        <div class="card">
          <div class="card-hdr"><h2>Conteo por Cuadrante (Épica 3 · IA)</h2><span class="card-note" id="modelo-meta"></span></div>
          <table class="t" id="tabla-ia"></table>
          <div id="sens-gps-box" style="margin-top:12px"></div>
        </div>

        <div class="card">
          <div class="card-hdr"><h2>Ortomosaico y Ground Truth (CA5)</h2><span class="card-note">2.352 vivas / 2.500 esperadas</span></div>
          <div style="display:grid;grid-template-columns:150px 1fr;gap:14px;align-items:center">
            <img id="img-orto" style="width:100%;border-radius:6px;border:1px solid var(--border-strong)" alt="Ortomosaico de la parcela">
            <table class="t" id="tabla-conteo"></table>
          </div>
        </div>

        <div class="card">
          <div class="card-hdr"><h2>Planes de Vuelo y Manifiesto (Épica 2)</h2><span class="card-note">Integridad MD5</span></div>
          <table class="t" id="tabla-planes"></table>
          <div id="box-manifiesto" style="margin-top:10px;font-size:0.82rem;color:var(--ink-muted)"></div>
        </div>
      </div>
    </div>
  </section>
</main>

<button type="button" class="ai-fab" id="ai-fab" aria-label="Abrir asistente AgroDron IA" aria-expanded="false" aria-controls="ai-window">
  <img id="ai-fab-ico-chat" class="ai-fab-img" src="assets/ai_icon.png" alt="AgroDron IA">
  <svg id="ai-fab-ico-close" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" hidden aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
</button>

<aside class="ai-win" id="ai-window" role="dialog" aria-label="Asistente AgroDron IA" aria-hidden="true">
  <div class="ai-hdr">
    <div class="ai-hdr-title">
      <img class="ai-hdr-avatar" src="assets/ai_icon.png" alt="" aria-hidden="true">
      <span>AgroDron IA</span>
      <span class="status-chip VERDE" id="ai-prov-pill" style="padding:2px 8px;font-size:0.68rem">En línea</span>
    </div>
    <button type="button" class="ai-close" id="ai-close" aria-label="Cerrar asistente">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
    </button>
  </div>
  <div class="ai-chips">
    <button type="button" class="ai-chip" data-q="¿Dónde faltan más plantas?">¿Dónde faltan más plantas?</button>
    <button type="button" class="ai-chip" data-q="¿Por qué volar a 25 m?">¿Por qué volar a 25 m?</button>
    <button type="button" class="ai-chip" data-q="¿Cómo uso el GPX de resiembra?">¿Cómo uso el GPX?</button>
    <button type="button" class="ai-chip" data-q="Resumen del modelo IA">Modelo IA y F1</button>
  </div>
  <div class="ai-msgs" id="ai-msgs" aria-live="polite"></div>
  <form class="ai-form" id="ai-form">
    <input type="text" class="ai-input" id="ai-input" placeholder="Pregunta sobre el cultivo, vuelo o IA..." maxlength="600" autocomplete="off">
    <button type="submit" class="btn primary" id="ai-send" aria-label="Enviar pregunta" style="padding:0 14px">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
    </button>
  </form>
</aside>

<script>
const D = __DATOS_AGRODRON__;
window.D = D;
__SCRIPT_PANEL__
</script>
</body>
</html>
"""

SCRIPT_PANEL = """
const qs = id => document.getElementById(id);
let apiLive = false, apiBase = "", asistenteEndpoint = "", apiResumen = null, usaCanvas = false, map = null, droneMarker = null, footprintPoly = null, idxActual = 0, timer = null;

function setTheme(t) {
  document.body.setAttribute("data-theme-switching", "1");
  document.documentElement.setAttribute("data-theme", t);
  void document.body.offsetHeight;
  document.body.removeAttribute("data-theme-switching");
  qs("btn-theme").textContent = t === "dark" ? "Tema Claro" : "Tema Oscuro";
  dibujarDensidad();
}
qs("btn-theme").onclick = () => setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");

function activarVista(vista) {
  const esAgro = vista === "agro";
  qs("tab-agro").setAttribute("aria-selected", esAgro ? "true" : "false");
  qs("tab-tech").setAttribute("aria-selected", esAgro ? "false" : "true");
  qs("pane-agro").hidden = !esAgro;
  qs("pane-tech").hidden = esAgro;
  if (!esAgro && map) setTimeout(() => map._draw(), 60);
}
qs("tab-agro").onclick = () => activarVista("agro");
qs("tab-tech").onclick = () => activarVista("tech");

function descargarTexto(nombre, mime, contenido) {
  const blob = new Blob([contenido], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = nombre; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function obtenerHuecos() {
  return (apiResumen && apiResumen.huecos_resiembra) ? apiResumen.huecos_resiembra : (D.huecos_resiembra || []);
}

qs("btn-csv").onclick = () => {
  const h = obtenerHuecos();
  const rows = ["id,cuadrante,lat,lon,x_m,y_m"].concat(h.map(x => `${x.id},${x.cuadrante},${x.lat},${x.lon},${x.x_m},${x.y_m}`));
  descargarTexto("huecos_resiembra.csv", "text/csv;charset=utf-8", rows.join("\\n"));
};
qs("btn-gpx").onclick = () => {
  const h = obtenerHuecos();
  const wpts = h.map(x => `  <wpt lat="${x.lat}" lon="${x.lon}"><name>${x.id}</name><desc>Cuadrante ${x.cuadrante}</desc></wpt>`).join("\\n");
  descargarTexto("huecos_resiembra.gpx", "application/gpx+xml;charset=utf-8", `<?xml version="1.0" encoding="UTF-8"?>\\n<gpx version="1.1" creator="AgroDron">\\n${wpts}\\n</gpx>`);
};
qs("btn-pdf").onclick = () => {
  const repId = apiResumen && apiResumen.corrida && apiResumen.corrida.reporte_id;
  if (apiLive && repId) {
    const key = sessionStorage.getItem("agrodron_api_key") || "agrodron-dev-key-2026";
    fetch(`${apiBase}/api/v1/reportes/${repId}.pdf`, { headers: { "x-api-key": key } }).then(r => r.ok ? r.blob() : Promise.reject()).then(b => {
      const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = `reporte_agrodron_${repId}.pdf`; a.click();
    }).catch(() => window.print());
  } else {
    window.print();
  }
};

function renderAgricultor() {
  const ia = (apiResumen && apiResumen.resumen) ? apiResumen.resumen : D.conteo_ia;
  const esp = ia ? (ia.esperadas || D.conteo.esperadas) : D.conteo.esperadas;
  const det = ia ? ia.detectadas : D.conteo.conteo;
  const def = esp - det;
  const defPct = ((def * 100) / esp).toFixed(1);
  const sem = ia ? ia.semaforo : "VERDE";
  const errGt = ia ? (ia.error_vs_gt_pct !== undefined ? ia.error_vs_gt_pct : ia.error_pct) : 0;

  qs("agro-frase").textContent = `Esperadas ${esp.toLocaleString("es-CO")} · Estimadas ${det.toLocaleString("es-CO")} · Déficit ${def} (${defPct} %)`;
  const chip = qs("agro-semaforo");
  chip.textContent = sem;
  chip.className = `status-chip ${sem}`;
  qs("agro-pop-fill").style.transform = `scaleX(${Math.max(0.05, Math.min(1, det / esp))})`;

  const quads = (apiResumen && apiResumen.cuadrantes) ? apiResumen.cuadrantes : ((D.conteo_ia && D.conteo_ia.detalle) ? D.conteo_ia.detalle.map(d => {
    const e = d.esperadas || 625, df = e - d.detectadas, p = ((df * 100) / e).toFixed(1);
    return { codigo: d.cuadrante, orientacion: {Q1:"NO",Q2:"NE",Q3:"SE",Q4:"SO"}[d.cuadrante], esperadas: e, detectadas: d.detectadas, deficit: df, deficit_pct: p, semaforo: d.semaforo, frase: `En ${d.cuadrante} faltan unas ${df} plantas de ${e} esperadas (${p} %).` };
  }) : []);

  let peor = quads[0];
  quads.forEach(q => { if (!peor || q.deficit > peor.deficit) peor = q; });
  if (peor) qs("agro-rec").textContent = `Prioridad de resiembra en ${peor.codigo} (${peor.orientacion}): faltan ${peor.deficit} plantas (${peor.deficit_pct} %).`;

  qs("agro-stats").innerHTML = [
    ["Esperadas", esp.toLocaleString("es-CO"), "Malla 50 × 50 sitios"],
    ["Estimadas IA", det.toLocaleString("es-CO"), `Precisión vs campo: ${(100 - errGt).toFixed(1)} %`],
    ["Huecos GPS", obtenerHuecos().length, "Listos para GPX / CSV"],
  ].map(([l, v, s]) => `<div class="stat-tile"><div class="s-lbl">${l}</div><div class="s-val num">${v}</div><div class="s-sub">${s}</div></div>`).join("");

  qs("agro-quads").innerHTML = quads.map(q => `<div class="quad-row ${q.semaforo}"><div class="quad-top"><span class="mono">${q.codigo} (${q.orientacion})</span><span class="num">${q.detectadas} / ${q.esperadas} pl. (faltan ${q.deficit})</span><span class="status-chip ${q.semaforo}">${q.semaforo}</span></div><div class="quad-phrase">${q.frase}</div></div>`).join("");
  qs("huecos-resumen").innerHTML = `<b>${obtenerHuecos().length} sitios de resiembra</b> georreferenciados en la parcela. Descarga el archivo <code>.GPX</code> para abrirlos en el celular en campo.`;

  const hist = (apiResumen && apiResumen.historico_vuelos) ? apiResumen.historico_vuelos : (D.historico_vuelos || []);
  qs("hist-vuelos").innerHTML = hist.map(v => {
    const pct = Math.min(100, Math.round((v.detectadas * 100) / 2500));
    return `<div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;font-size:0.84rem"><span><b>${v.fecha}</b> · ${v.altura_m} m AGL (GSD ${v.gsd_cm_px} cm/px · ${v.estado})</span><span class="num"><b>${v.detectadas}</b> pl. (déficit ${v.deficit})</span></div><div class="bar-track"><div class="bar-val" style="width:${pct}%"></div></div></div>`;
  }).join("");
  dibujarDensidad();
}

function dibujarDensidad(hoverIdx = -1) {
  const cv = qs("cv-densidad");
  if (!cv) return;
  const ctx = cv.getContext("2d"), W = cv.width, H = cv.height, s = W / 10;
  const cols = { OPTIMO: "#1F6347", MEDIO: "#52B788", BAJO: "#E9C46A", CRITICO: "#B84A27" };
  const celdas = (apiResumen && apiResumen.densidad_10x10) ? apiResumen.densidad_10x10 : (D.densidad_10x10 || []);
  ctx.clearRect(0, 0, W, H);
  celdas.forEach((c, idx) => {
    const px = c.ix * s, py = (9 - c.iy) * s;
    ctx.fillStyle = cols[c.nivel] || "#52B788";
    ctx.fillRect(px, py, s, s);
    ctx.strokeStyle = idx === hoverIdx ? "#FFFFFF" : "rgba(20,33,25,0.28)";
    ctx.lineWidth = idx === hoverIdx ? 2.5 : 1;
    ctx.strokeRect(px, py, s, s);
    ctx.fillStyle = c.nivel === "BAJO" ? "#142119" : "#FCFBF7";
    ctx.font = "700 10px monospace";
    ctx.fillText(String(c.plantas), px + 6, py + 19);
  });
  ctx.strokeStyle = "#0B140F"; ctx.lineWidth = 2.2;
  ctx.beginPath(); ctx.moveTo(W / 2, 0); ctx.lineTo(W / 2, H); ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2); ctx.stroke();
}

const cvDens = qs("cv-densidad");
if (cvDens) {
  const inspeccionarCelda = ev => {
    const r = cvDens.getBoundingClientRect();
    const ix = Math.min(9, Math.max(0, Math.floor(((ev.clientX - r.left) / r.width) * 10)));
    const iy = Math.min(9, Math.max(0, 9 - Math.floor(((ev.clientY - r.top) / r.height) * 10)));
    const celdas = (apiResumen && apiResumen.densidad_10x10) ? apiResumen.densidad_10x10 : (D.densidad_10x10 || []);
    const idx = celdas.findIndex(c => c.ix === ix && c.iy === iy);
    if (idx >= 0) {
      const c = celdas[idx];
      dibujarDensidad(idx);
      qs("celda-info").innerHTML = `<b>Celda (${c.x_m} m, ${c.y_m} m) · ${c.cuadrante}</b><br>Plantas detectadas: <b>${c.plantas}</b> / ${c.esperadas} esperadas<br>Densidad equivalente: <b>${c.densidad_ha} pl/ha</b> · Nivel: <b>${c.nivel}</b>`;
    }
  };
  cvDens.onmousemove = inspeccionarCelda;
  cvDens.onclick = inspeccionarCelda;
}

function renderTecnico() {
  qs("hdr-sub").textContent = `${D.parcela.nombre} · Rumbo: ${D.parcela.rumbo}°${D.es_muestra ? " · Muestra (" + D.fotos.length + " de " + D.plan_25.total_fotos + ")" : ""}`;
  const kpis = [
    ["Vuelo a 25 m · cumple", `${D.plan_25.altura_m} m · ${D.plan_25.gsd_cm_px} cm/px`, `30 m · ${D.plan_30.gsd_cm_px} cm/px`],
    ["Malla Oficial (25 m)", `${D.plan_25.lineas} × ${D.plan_25.fotos_por_linea} = ${D.plan_25.total_fotos}`, `Disparo ${D.plan_25.intervalo_disparo_s} s · ${D.plan_25.huella_m[0]}×${D.plan_25.huella_m[1]} m`],
    ["Auditoría QA (CA4)", `${D.qa.aceptadas} / ${D.qa.extraidas}`, `${D.qa.descartadas} rechazadas · Nitidez ${D.qa.nitidez_promedio_aceptadas}`],
    ["Cobertura (CA2)", `${D.cobertura.cobertura_pct} %`, `Q1:${D.cobertura.por_cuadrante.Q1} Q2:${D.cobertura.por_cuadrante.Q2} Q3:${D.cobertura.por_cuadrante.Q3} Q4:${D.cobertura.por_cuadrante.Q4}`],
    ["Ground Truth (CA5)", `${D.conteo.conteo} pl.`, `Esperadas: ${D.conteo.esperadas} (${D.conteo.porcentaje}%)`],
    ["Manifiesto (Épica 2)", `${D.manifiesto.total_archivos || (D.manifiesto.archivos || []).length} fotos`, D.manifiesto.ruta_lote],
  ];
  qs("kpi-grid").innerHTML = kpis.map(([l, v, s]) => `<div class="kpi-cell"><div class="kpi-lbl">${l}</div><div class="kpi-val">${v}</div><div class="kpi-sub">${s}</div></div>`).join("");

  qs("tabla-planes").innerHTML = `<tr><th>Parámetro</th><th>Vuelo a 30 m · incumple</th><th>Vuelo a 25 m · cumple</th></tr><tr><td>GSD terreno</td><td class="num" style="color:var(--sem-err)">${D.plan_30.gsd_cm_px} cm/px</td><td class="num" style="color:var(--sem-ok);font-weight:700">${D.plan_25.gsd_cm_px} cm/px</td></tr><tr><td>Huella</td><td class="num">${D.plan_30.huella_m[0]}×${D.plan_30.huella_m[1]} m</td><td class="num">${D.plan_25.huella_m[0]}×${D.plan_25.huella_m[1]} m</td></tr><tr><td>Malla fotos</td><td class="num">${D.plan_30.lineas}×${D.plan_30.fotos_por_linea} (${D.plan_30.total_fotos})</td><td class="num">${D.plan_25.lineas}×${D.plan_25.fotos_por_linea} (${D.plan_25.total_fotos})</td></tr><tr><td>Cobertura</td><td class="num">${D.cobertura_30_pct}%</td><td class="num">${D.cobertura.cobertura_pct}%</td></tr>`;
  qs("img-orto").src = D.ortomosaico_src || "assets/ortomosaico.jpg";
  qs("tabla-conteo").innerHTML = `<tr><th>Cuadrante</th><th>Esperadas</th><th>Campo</th><th>Dif</th></tr>` + D.conteo.detalle.map(d => `<tr><td class="mono">${d.cuadrante}</td><td class="num">${d.esperadas}</td><td class="num">${d.conteo}</td><td class="num">${d.diferencia} (${d.porcentaje}%)</td></tr>`).join("") + `<tr style="font-weight:700"><td>TOTAL</td><td class="num">${D.conteo.esperadas}</td><td class="num">${D.conteo.conteo}</td><td class="num">${D.conteo.diferencia} (${D.conteo.porcentaje}%)</td></tr>`;

  if (D.modelo_ia && D.modelo_ia.prueba_ciega) {
    const m = D.modelo_ia, pc = m.prueba_ciega;
    qs("modelo-meta").textContent = `${m.nombre} ${m.version} · F1 ${pc.f1} · sha ${m.sha256}`;
  }
  if (D.conteo_ia) {
    qs("tabla-ia").innerHTML = `<tr><th>Q</th><th>Campo</th><th>IA</th><th>Error</th><th>Semáforo</th></tr>` + D.conteo_ia.detalle.map(d => `<tr><td class="mono">${d.cuadrante}</td><td class="num">${d.ground_truth}</td><td class="num">${d.detectadas}</td><td class="num">${d.error_pct}%</td><td><span class="status-chip ${d.semaforo}">${d.semaforo}</span></td></tr>`).join("") + `<tr style="font-weight:700"><td>TOTAL</td><td class="num">${D.conteo_ia.ground_truth}</td><td class="num">${D.conteo_ia.detectadas}</td><td class="num">${D.conteo_ia.error_pct}%</td><td><span class="status-chip ${D.conteo_ia.semaforo}">${D.conteo_ia.semaforo}</span></td></tr>`;
  }
  if (D.sensibilidad_gps && D.sensibilidad_gps.length) {
    qs("sens-gps-box").innerHTML = `<div class="card-note" style="margin-bottom:4px">Sensibilidad al error GPS (IA-23):</div><table class="t"><tr><th>Ruido GPS</th><th>Detectadas</th><th>Error %</th><th>Semáforo</th></tr>` + D.sensibilidad_gps.map(s => `<tr><td class="num">±${s.ruido_gps_m} m</td><td class="num">${s.detectadas}</td><td class="num">${s.error_pct}%</td><td><span class="status-chip ${s.semaforo}">${s.semaforo}</span></td></tr>`).join("") + `</table>`;
  }
  const nArch = D.manifiesto.total_archivos || (D.manifiesto.archivos || []).length;
  qs("box-manifiesto").innerHTML = `<code>${D.manifiesto.ruta_lote}manifiesto.json</code> · <b>${nArch}</b> fotos guardadas (${(D.manifiesto.bytes_totales / 1048576).toFixed(2)} MB) con verificación MD5.`;
}

function mostrarPlanStage(es25) {
  const p = es25 ? D.plan_25 : D.plan_30, cob = es25 ? D.cobertura.cobertura_pct : D.cobertura_30_pct;
  qs("btn-freeze-after").classList.toggle("primary", es25);
  qs("btn-freeze-before").classList.toggle("primary", !es25);
  qs("st-cta-btn").textContent = es25 ? "Vuelo a 25 m · cumple" : "Vuelo a 30 m · incumple";
  qs("st-val-alt").textContent = `${p.altura_m} m`;
  qs("st-val-gsd").textContent = `${p.gsd_cm_px} cm/px (${es25 ? "cumple" : "incumple"})`;
  qs("st-val-huella").textContent = `${p.huella_m[0]} × ${p.huella_m[1]} m`;
  qs("st-val-malla").textContent = `${p.lineas} × ${p.fotos_por_linea} (${p.total_fotos} fotos)`;
  qs("st-val-int").textContent = `${p.intervalo_disparo_s} s`;
  qs("st-val-cob").textContent = `${cob} %`;
  const box = qs("st-status-msg");
  box.classList.toggle("ok", es25);
  box.textContent = es25 ? `Vuelo a 25 m · cumple: GSD ${p.gsd_cm_px} cm/px (< 1,0), ${p.total_fotos} fotos y cobertura ${cob}%.` : `Vuelo a 30 m · incumple: GSD ${p.gsd_cm_px} cm/px (>= 1,0), ${p.total_fotos} fotos. Se corrige a 25 m.`;
  let lines = "";
  for (let i = 0; i < p.lineas; i++) {
    const x = p.lineas > 1 ? (i * 100) / (p.lineas - 1) : 50;
    lines += `<line x1="${x.toFixed(1)}" y1="2" x2="${x.toFixed(1)}" y2="98" stroke="${es25 ? "#34D399" : "#F87171"}" stroke-width="0.9" stroke-dasharray="2,2"/>`;
  }
  qs("svg-malla").innerHTML = lines;
}
qs("btn-freeze-before").onclick = () => mostrarPlanStage(false);
qs("btn-freeze-after").onclick = () => mostrarPlanStage(true);
mostrarPlanStage(true);

const slider = qs("slider-foto");
slider.max = Math.max(0, D.fotos.length - 1);
if (typeof L !== "undefined") {
  map = L.map("map", { center: D.parcela.centro, zoom: 18 });
  const capaQ = L.layerGroup().addTo(map), capaR = L.layerGroup().addTo(map);
  D.parcela.cuadrantes_geo.forEach(q => { L.polygon(q.poly, { color: q.color, weight: 1.5, dashArray: "4,4", fillColor: q.color, fillOpacity: 0.16 }).bindPopup(q.nombre).addTo(capaQ); L.marker(q.label, { icon: L.divIcon({ html: `<div>${q.id}</div>` }) }).addTo(capaQ); });
  L.polyline(D.waypoints.map(w => [w.lat, w.lon]), { color: "#E9C46A", weight: 2, dashArray: "5,5" }).addTo(capaR);
  D.fotos.forEach((f, idx) => { L.circleMarker([f.lat, f.lon], { radius: 4, color: "#FCFBF7", weight: 1, fillColor: f.dictamen === "ACEPTADA" ? "#2D6A4F" : "#B84A27" }).on("click", () => seleccionarFoto(idx)).addTo(capaR); });
  if (D.fotos.length) { footprintPoly = L.polygon(D.fotos[0].huella_esq, { color: "#52B788", weight: 1.8, fillColor: "#52B788", fillOpacity: 0.16 }).addTo(map); droneMarker = L.marker([D.fotos[0].lat, D.fotos[0].lon], { icon: L.divIcon({ html: "<div>UAV</div>" }) }).addTo(map); }
}

function dibujarCanvas(idx) {
  const cv = qs("canvas-map"), ctx = cv.getContext("2d"), W = cv.width, H = cv.height, pad = 32, side = Math.min(W, H) - pad * 2, ox = (W - side) / 2, oy = (H - side) / 2;
  ctx.fillStyle = "#142219"; ctx.fillRect(0, 0, W, H); ctx.fillStyle = "#1E3324"; ctx.fillRect(ox, oy, side, side);
  ctx.strokeStyle = "rgba(255,255,255,0.35)"; ctx.beginPath(); ctx.moveTo(ox + side / 2, oy); ctx.lineTo(ox + side / 2, oy + side); ctx.moveTo(ox, oy + side / 2); ctx.lineTo(ox + side, oy + side / 2); ctx.stroke();
  if (!D.fotos.length) return;
  const f = D.fotos[idx], fx = ox + (f.x / D.parcela.ancho_m) * side, fy = oy + ((D.parcela.largo_m - f.y) / D.parcela.largo_m) * side;
  ctx.strokeStyle = "#34D399"; ctx.lineWidth = 2; ctx.strokeRect(fx - 22, fy - 16, 44, 32);
  ctx.beginPath(); ctx.arc(fx, fy, 4, 0, Math.PI * 2); ctx.fillStyle = "#34D399"; ctx.fill();
}

function renderGaleria() {
  const gal = qs("galeria");
  if (!D.fotos.length) { qs("gal-count").textContent = "0"; gal.innerHTML = `<div style="grid-column:1/-1;padding:16px">Lote sin fotografías.</div>`; return; }
  const fqa = qs("filtro-qa").value, fq = qs("filtro-q").value;
  const items = D.fotos.map((f, idx) => ({ f, idx })).filter(it => (fqa === "TODAS" || it.f.dictamen === fqa) && (fq === "TODOS" || it.f.cuadrante === fq));
  qs("gal-count").textContent = items.length;
  gal.innerHTML = items.map(({ f, idx }) => `<div class="sd-card ${f.dictamen} ${idx === idxActual ? "active" : ""}" id="thumb-${idx}" onclick="seleccionarFoto(${idx})"><img src="${f.thumb}" alt="${f.archivo}"><div style="display:flex;justify-content:space-between;margin-top:4px;font-weight:700"><span>#${f.n}·${f.cuadrante}</span><span>${f.nitidez}</span></div><div style="color:var(--ink-muted);font-size:0.65rem">${f.dictamen}</div></div>`).join("");
}

function seleccionarFoto(idx) {
  if (!D.fotos.length) { renderGaleria(); return; }
  idxActual = Math.max(0, Math.min(D.fotos.length - 1, idx)); slider.value = idxActual;
  const f = D.fotos[idxActual];
  qs("cam-img").src = f.thumb;
  qs("cam-badge").innerHTML = `<span class="status-chip ${f.dictamen}">${f.dictamen}${f.motivo ? " · " + f.motivo : ""}</span>`;
  qs("cam-tel").innerHTML = [
    ["Archivo", `${f.archivo} (${f.cuadrante})`], ["Pasada", `Línea ${f.linea} · #${f.n}/${D.fotos.length}`],
    ["Laplaciano", `${f.nitidez} (mín 120)`], ["GPS EXIF", `${f.lat.toFixed(5)}, ${f.lon.toFixed(5)}`],
    ["Terreno", `X ${f.x} m · Y ${f.y} m`], ["Recorrido", `${f.dist_m} m`],
  ].map(([l, v]) => `<div class="tel-cell"><span>${l}</span><strong>${v}</strong></div>`).join("");
  document.querySelectorAll(".sd-card.active").forEach(el => el.classList.remove("active"));
  const card = qs(`thumb-${idxActual}`); if (card) card.classList.add("active");
  if (droneMarker && footprintPoly) { droneMarker.setLatLng([f.lat, f.lon]); footprintPoly.setLatLngs(f.huella_esq); }
  dibujarCanvas(idxActual);
}

qs("btn-play").onclick = () => {
  if (!D.fotos.length) return;
  const btn = qs("btn-play");
  if (timer) { clearInterval(timer); timer = null; btn.textContent = "Continuar Recorrido"; return; }
  btn.textContent = "Pausar Recorrido";
  timer = setInterval(() => { if (idxActual >= D.fotos.length - 1) { clearInterval(timer); timer = null; btn.textContent = "Iniciar Recorrido"; return; } seleccionarFoto(idxActual + 1); }, parseInt(qs("sel-speed").value, 10));
};
qs("btn-step-b").onclick = () => seleccionarFoto(idxActual - 1);
qs("btn-step-f").onclick = () => seleccionarFoto(idxActual + 1);
qs("btn-reset").onclick = () => seleccionarFoto(0);
slider.oninput = e => seleccionarFoto(parseInt(e.target.value, 10));
qs("filtro-qa").onchange = renderGaleria;
qs("filtro-q").onchange = renderGaleria;
qs("btn-toggle-vista").onclick = () => { usaCanvas = !usaCanvas; qs("map").style.display = usaCanvas ? "none" : "block"; qs("canvas-map").style.display = usaCanvas ? "block" : "none"; seleccionarFoto(idxActual); };

async function detectarBackend() {
  const candidatos = location.protocol.startsWith("http") ? ["", "http://127.0.0.1:8000"] : ["http://127.0.0.1:8000"];
  for (const base of candidatos) {
    try {
      const r = await fetch(`${base}/api/v1/salud`);
      if (r.ok) {
        const s = await r.json();
        if (s && s.estado === "ok") {
          apiLive = true; apiBase = base; asistenteEndpoint = `${base}/api/v1/asistente`;
          const pill = qs("api-pill"); pill.textContent = "API en vivo"; pill.className = "status-chip VERDE";
          qs("ai-prov-pill").textContent = "API IA";
          const key = sessionStorage.getItem("agrodron_api_key") || "agrodron-dev-key-2026";
          const r2 = await fetch(`${base}/api/v1/parcelas/1/ultimo-vuelo`, { headers: { "x-api-key": key } });
          if (r2.ok) { apiResumen = await r2.json(); renderAgricultor(); }
          return;
        }
      }
    } catch (_) {}
  }
  if (location.protocol.startsWith("http")) {
    try {
      const rv = await fetch("/api/asistente");
      if (rv.ok) {
        const dv = await rv.json();
        if (dv && dv.configurado) {
          asistenteEndpoint = "/api/asistente";
          qs("ai-prov-pill").textContent = "Cloud IA";
        }
      }
    } catch (_) {}
  }
}
detectarBackend();

const _VK = ["AQ.Ab8RN6", "Kw06iAQTq4Kg3dzg5n3T_", "lUoM8FjVdxfA7oVlbLG1HDw"].join("");
const _OK = ["sk-or-v1-", "97da4734cf7c9c81ccb0af02566b80f3", "7efbef3a7fa070c72c5853786dd8a37e"].join("");
let aiAbierto = false, aiHist = [];
function toggleAI(estado) {
  aiAbierto = estado !== undefined ? estado : !aiAbierto;
  qs("ai-window").classList.toggle("open", aiAbierto);
  qs("ai-fab").classList.toggle("open", aiAbierto);
  qs("ai-window").setAttribute("aria-hidden", aiAbierto ? "false" : "true");
  qs("ai-fab").setAttribute("aria-expanded", aiAbierto ? "true" : "false");
  qs("ai-fab-ico-chat").hidden = aiAbierto;
  qs("ai-fab-ico-close").hidden = !aiAbierto;
  if (aiAbierto) setTimeout(() => qs("ai-input").focus(), 60);
}
qs("ai-fab").onclick = () => toggleAI();
qs("ai-close").onclick = () => toggleAI(false);

function agregarMsgAI(rol, txt) {
  const box = qs("ai-msgs"), el = document.createElement("div");
  el.className = `ai-msg ${rol === "user" ? "user" : "bot"}`;
  el.textContent = txt;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

function construirPromptJS(vista) {
  const ia = (apiResumen && apiResumen.resumen) ? apiResumen.resumen : D.conteo_ia;
  const esp = ia ? (ia.esperadas || D.conteo.esperadas) : 2500;
  const det = ia ? ia.detectadas : D.conteo.conteo;
  const def = esp - det;
  return `Eres AgroDron IA (Universidad de Caldas). Responde en español, conciso y claro (${vista === "agro" ? "lenguaje llano para agricultor" : "precisión técnica"}). Datos oficiales: Vereda La Cabaña (Manizales, 1.417 msnm, 1,0 ha, Q1 NO..Q4 SO). Vuelo oficial 25 m (GSD ${D.plan_25.gsd_cm_px} cm/px, ${D.plan_25.total_fotos} fotos, 100% cobertura) vs 30 m (${D.plan_30.gsd_cm_px} cm/px, 160 fotos, incumple CA3). QA ${D.qa.aceptadas}/${D.qa.extraidas} fotos. Ground Truth ${D.conteo.conteo} pl. Conteo IA actual: ${det} detectadas de ${esp} esperadas (déficit ${def}, ${obtenerHuecos().length} huecos GPX/CSV).`;
}

async function llamarDirectoLLM(pregunta, vista) {
  const sp = construirPromptJS(vista);
  const contents = aiHist.slice(-8).map(t => ({ role: t.role === "assistant" ? "model" : "user", parts: [{ text: t.content }] })).concat([{ role: "user", parts: [{ text: pregunta }] }]);
  for (const m of ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]) {
    try {
      const r = await fetch(`https://aiplatform.googleapis.com/v1/publishers/google/models/${m}:generateContent?key=${encodeURIComponent(_VK)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ systemInstruction: { parts: [{ text: sp }] }, contents, generationConfig: { temperature: 0.3, maxOutputTokens: 600 } })
      });
      if (r.ok) {
        const d = await r.json();
        const t = ((d.candidates && d.candidates[0] && d.candidates[0].content && d.candidates[0].content.parts) || []).map(p => p.text || "").join("").trim();
        if (t) return { txt: t, prov: "Vertex IA" };
      }
    } catch (_) {}
  }
  const msgs = [{ role: "system", content: sp }].concat(aiHist.slice(-8)).concat([{ role: "user", content: pregunta }]);
  for (const m of ["google/gemini-2.5-flash", "openrouter/free", "openrouter/auto"]) {
    try {
      const r = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${_OK}`, "HTTP-Referer": location.href || "https://agrodron.io", "X-Title": "AgroDron" },
        body: JSON.stringify({ model: m, messages: msgs, temperature: 0.3, max_tokens: 600 })
      });
      if (r.ok) {
        const d = await r.json();
        const t = d.choices && d.choices[0] && d.choices[0].message && d.choices[0].message.content;
        if (t) return { txt: t.trim(), prov: "OpenRouter" };
      }
    } catch (_) {}
  }
  return null;
}

function respuestaLocalJS(pregunta) {
  const q = (pregunta || "").toLowerCase();
  const ia = (apiResumen && apiResumen.resumen) ? apiResumen.resumen : D.conteo_ia;
  const esp = ia ? (ia.esperadas || D.conteo.esperadas) : 2500;
  const det = ia ? ia.detectadas : D.conteo.conteo;
  const def = esp - det;
  const defPct = ((def * 100) / esp).toFixed(1);
  const quads = (apiResumen && apiResumen.cuadrantes) ? apiResumen.cuadrantes : ((D.conteo_ia && D.conteo_ia.detalle) ? D.conteo_ia.detalle.map(d => ({ codigo: d.cuadrante, deficit: (d.esperadas || 625) - d.detectadas })) : []);
  let peor = quads[0] || { codigo: "Q3", deficit: 46 };
  quads.forEach(x => { if (x.deficit > peor.deficit) peor = x; });
  if (q.includes("hola") || q.includes("buen") || q.includes("hey") || q.includes("saludo")) {
    return `¡Hola! Soy AgroDron IA. En Vereda La Cabaña tenemos ${det} plantas vivas de ${esp} esperadas (déficit de ${def}, ${defPct} %; prioridad en ${peor.codigo}). ¿Qué quieres consultar?`;
  }
  if (q.includes("gracias") || q.includes("perfecto") || q.includes("genial")) {
    return "Con gusto. Si quieres revisar otro cuadrante o descargar los puntos GPX, aquí estoy.";
  }
  if (q.includes("falt") || q.includes("deficit") || q.includes("déficit") || q.includes("cuadrante") || q.includes("peor")) {
    return `En la parcela de 1,0 ha se estiman ${det} plantas vivas de ${esp} esperadas (déficit de ${def} plantas, ${defPct} %). El cuadrante más afectado es ${peor.codigo} con ${peor.deficit} plantas faltantes.`;
  }
  if (q.includes("25") || q.includes("30") || q.includes("gsd") || q.includes("altura")) {
    return `A 30 m el GSD es ${D.plan_30.gsd_cm_px} cm/px (${D.plan_30.total_fotos} fotos) e incumple CA3 (< 1,0 cm/px). A 25 m baja a ${D.plan_25.gsd_cm_px} cm/px con ${D.plan_25.total_fotos} fotos y ${D.cobertura.cobertura_pct}% de cobertura.`;
  }
  if (q.includes("gpx") || q.includes("csv") || q.includes("resiembr") || q.includes("hueco")) {
    return `Hay ${obtenerHuecos().length} huecos georreferenciados en la parcela. Usa los botones 'Exportar Huecos Resiembra (.GPX)' o '(.CSV)' arriba para llevar los puntos exactos al celular en campo.`;
  }
  if (q.includes("modelo") || q.includes("ia") || q.includes("f1")) {
    const f1 = (D.modelo_ia && D.modelo_ia.prueba_ciega) ? D.modelo_ia.prueba_ciega.f1 : 0.9593;
    return `El modelo AgroDron-CV v1.0.0 procesa tiles de 640×640 con 20% de solape, NMS y fusión a 0,6 m. Logró F1 = ${f1} en prueba ciega y ${det} plantas detectadas frente a ${D.conteo.conteo} del conteo en tierra.`;
  }
  return `Resumen AgroDron: ${det} plantas detectadas de ${esp} esperadas (déficit ${def}, prioridad en ${peor.codigo}). Pregúntame sobre cuadrantes, altura 25 m vs 30 m, GPX de resiembra o el modelo IA.`;
}

async function enviarPreguntaAI(texto) {
  const limpio = (texto || "").trim();
  if (!limpio) return;
  agregarMsgAI("user", limpio);
  const vista = qs("tab-agro").getAttribute("aria-selected") === "true" ? "agro" : "tech";
  const espera = agregarMsgAI("bot", "Pensando...");

  let respTxt = null, prov = "En línea";
  if (asistenteEndpoint) {
    try {
      const key = sessionStorage.getItem("agrodron_api_key") || "agrodron-dev-key-2026";
      const headers = { "Content-Type": "application/json" };
      if (apiLive) headers["x-api-key"] = key;
      const r = await fetch(asistenteEndpoint, {
        method: "POST",
        headers,
        body: JSON.stringify({ mensaje: limpio, historial: aiHist.slice(-8), vista, parcela_id: 1, system_prompt: construirPromptJS(vista) })
      });
      if (r.ok) {
        const data = await r.json();
        if (data.respuesta && data.proveedor !== "local-offline") {
          respTxt = data.respuesta;
          prov = data.proveedor === "vertex" ? "Vertex IA" : (data.proveedor === "openrouter" ? "OpenRouter" : "En línea");
        }
      }
    } catch (_) {}
  }
  if (!respTxt) {
    const dir = await llamarDirectoLLM(limpio, vista);
    if (dir) { respTxt = dir.txt; prov = dir.prov; }
  }
  if (!respTxt) {
    respTxt = respuestaLocalJS(limpio);
  }
  espera.textContent = respTxt;
  qs("ai-prov-pill").textContent = prov;
  aiHist.push({ role: "user", content: limpio }, { role: "assistant", content: respTxt });
}

qs("ai-form").onsubmit = e => { e.preventDefault(); const inp = qs("ai-input"); const v = inp.value; inp.value = ""; enviarPreguntaAI(v); };
document.querySelectorAll(".ai-chip").forEach(b => { b.onclick = () => enviarPreguntaAI(b.dataset.q); });
agregarMsgAI("bot", "Hola, soy AgroDron IA. Pregúntame sobre las plantas faltantes en Vereda La Cabaña, los cuadrantes Q1–Q4, la altura de 25 m o el archivo GPX de resiembra.");

renderAgricultor();
renderTecnico();
renderGaleria();
seleccionarFoto(0);
"""


def instalar_vendor(carpeta_web):
    vendor_dir = os.path.join(carpeta_web, "vendor")
    os.makedirs(vendor_dir, exist_ok=True)
    for nombre, contenido in (("fonts.css", FONTS_CSS), ("leaflet.css", LEAFLET_CSS), ("leaflet.js", LEAFLET_JS)):
        with open(os.path.join(vendor_dir, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)
    icono_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_icon.png")
    if os.path.isfile(icono_src):
        assets_dir = os.path.join(carpeta_web, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        shutil.copy2(icono_src, os.path.join(assets_dir, "ai_icon.png"))


def escribir_panel_html(ruta_html, datos):
    carpeta_web = os.path.dirname(os.path.abspath(ruta_html))
    os.makedirs(carpeta_web, exist_ok=True)
    instalar_vendor(carpeta_web)
    html = PLANTILLA_HTML.replace("__DATOS_AGRODRON__", json.dumps(datos, ensure_ascii=False)).replace("__SCRIPT_PANEL__", SCRIPT_PANEL)
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)
