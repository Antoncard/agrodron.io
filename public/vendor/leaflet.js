/* Motor cartografico local compatible con API L (Leaflet offline) */
window.L = (function() {
  function LayerGroup() { this.items = []; this.visible = true; }
  LayerGroup.prototype.addTo = function(m) { m._addGroup(this); return this; };
  function Elemento(tipo, coords, opts) { this.tipo = tipo; this.coords = coords; this.opts = opts || {}; this.popup = ""; this.handlers = {}; }
  Elemento.prototype.addTo = function(dest) { if (dest.items) dest.items.push(this); else if (dest._addItem) dest._addItem(this); return this; };
  Elemento.prototype.bindPopup = function(txt) { this.popup = txt; return this; };
  Elemento.prototype.on = function(ev, fn) { this.handlers[ev] = fn; return this; };
  Elemento.prototype.setLatLng = function(ll) { this.coords = ll; if (this._map) this._map._draw(); };
  Elemento.prototype.setLatLngs = function(lls) { this.coords = lls; if (this._map) this._map._draw(); };
  Elemento.prototype.setStyle = function(st) { Object.assign(this.opts, st); if (this._map) this._map._draw(); };
  function Mapa(id, opts) {
    this.el = document.getElementById(id);
    this.center = (opts && opts.center) || [5.0949, -75.5891];
    this.zoom = (opts && opts.zoom) || 18;
    this.groups = []; this.items = [];
    this.el.classList.add("leaflet-container");
    this.el.innerHTML = '<canvas class="lf-cv" style="width:100%;height:100%;display:block"></canvas><div class="leaflet-ctrl-zoom"><button type="button" data-z="1">+</button><button type="button" data-z="-1">−</button></div><div class="leaflet-popup-box" style="display:none"></div>';
    this.cv = this.el.querySelector("canvas");
    this.popEl = this.el.querySelector(".leaflet-popup-box");
    const self = this;
    this.el.querySelectorAll("[data-z]").forEach(function(b) {
      b.onclick = function() { self.zoom = Math.max(16, Math.min(20, self.zoom + parseInt(b.dataset.z, 10))); self._draw(); };
    });
    this.cv.onclick = function(e) { self._click(e); };
    window.addEventListener("resize", function() { self._draw(); });
    setTimeout(function() { self._draw(); }, 40);
  }
  Mapa.prototype._addGroup = function(g) { this.groups.push(g); this._draw(); };
  Mapa.prototype._addItem = function(it) { it._map = this; this.items.push(it); this._draw(); };
  Mapa.prototype._proj = function(lat, lon, W, H) {
    const sc = Math.pow(2, this.zoom - 18) * Math.min(W, H) * 3200;
    return [W / 2 + (lon - this.center[1]) * Math.cos(this.center[0] * Math.PI / 180) * sc, H / 2 - (lat - this.center[0]) * sc];
  };
  Mapa.prototype._all = function() {
    let list = this.items.slice();
    this.groups.forEach(function(g) { if (g.visible) list = list.concat(g.items); });
    return list;
  };
  Mapa.prototype._click = function(e) {
    const r = this.cv.getBoundingClientRect(), mx = (e.clientX - r.left) * (this.cv.width / r.width), my = (e.clientY - r.top) * (this.cv.height / r.height), all = this._all();
    for (let i = all.length - 1; i >= 0; i--) {
      const it = all[i];
      if (it.tipo === "circle") {
        const p = this._proj(it.coords[0], it.coords[1], this.cv.width, this.cv.height);
        if (Math.hypot(mx - p[0], my - p[1]) <= (it.opts.radius || 6) + 5) {
          if (it.handlers.click) it.handlers.click();
          if (it.popup) { this.popEl.innerHTML = it.popup; this.popEl.style.display = "block"; }
          return;
        }
      }
    }
  };
  Mapa.prototype._draw = function() {
    const W = this.cv.width = this.el.clientWidth || 800, H = this.cv.height = this.el.clientHeight || 440, ctx = this.cv.getContext("2d"), self = this;
    ctx.fillStyle = "#1B2A20"; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(255,255,255,0.06)"; ctx.lineWidth = 1;
    for (let gx = 0; gx < W; gx += 48) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke(); }
    for (let gy = 0; gy < H; gy += 48) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke(); }
    this._all().forEach(function(it) {
      it._map = self;
      if ((it.tipo === "poly" || it.tipo === "line") && it.coords && it.coords.length) {
        ctx.beginPath();
        it.coords.forEach(function(ll, idx) { const p = self._proj(ll[0], ll[1], W, H); if (idx === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]); });
        if (it.tipo === "poly") {
          ctx.closePath();
          if (it.opts.fillColor || it.opts.color) { ctx.fillStyle = it.opts.fillColor || it.opts.color; ctx.globalAlpha = it.opts.fillOpacity !== undefined ? it.opts.fillOpacity : 0.15; ctx.fill(); ctx.globalAlpha = 1.0; }
        }
        ctx.strokeStyle = it.opts.color || "#E9C46A"; ctx.lineWidth = it.opts.weight || 1.8;
        ctx.setLineDash(it.opts.dashArray ? [4, 4] : []); ctx.stroke(); ctx.setLineDash([]);
      } else if (it.tipo === "circle" && it.coords) {
        const p = self._proj(it.coords[0], it.coords[1], W, H);
        ctx.beginPath(); ctx.arc(p[0], p[1], it.opts.radius || 5, 0, Math.PI * 2);
        ctx.fillStyle = it.opts.fillColor || "#2D6A4F"; ctx.fill();
        ctx.strokeStyle = it.opts.color || "#FCFBF7"; ctx.lineWidth = it.opts.weight || 1.2; ctx.stroke();
      } else if (it.tipo === "marker" && it.coords) {
        const p = self._proj(it.coords[0], it.coords[1], W, H), txt = (it.opts.icon && it.opts.icon.html) ? it.opts.icon.html.replace(/<[^>]+>/g, "") : "UAV";
        ctx.font = "700 10px monospace"; const tw = ctx.measureText(txt).width + 10;
        ctx.fillStyle = txt === "UAV" ? "#52B788" : "#16231B"; ctx.fillRect(p[0] - tw / 2, p[1] - 9, tw, 18);
        ctx.fillStyle = txt === "UAV" ? "#16231B" : "#FCFBF7"; ctx.fillText(txt, p[0] - tw / 2 + 5, p[1] + 3);
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
