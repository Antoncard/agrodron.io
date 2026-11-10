# Simulador rural de cultivo, vuelo, fotos EXIF GPS, ortomosaico y panel web (< 300 lineas)
from concurrent.futures import ThreadPoolExecutor
import csv
import os
import re
import shutil
import webbrowser

import cv2
import numpy as np
from PIL import Image

from src.almacen import copiar_lote, crear_manifiesto, guardar_manifiesto
from src.dominio.conteo_referencia import CONTEO_DOCUMENTO, leer_planilla_conteo
from src.dominio.parcela import (
    Parcela, calcular_cobertura, cuadrante_local, escribir_kml, escribir_waypoints_csv, evaluar_cobertura, generar_ruta, posiciones_disparo,
)
from src.dominio.plan_vuelo import calcular_plan_vuelo, huella, leer_obturacion, validar_calibracion
from src.dominio.qa_fotos import GPS_TAG, RESOLUCION, auditar_lote, leer_aceptadas
from src.ml.evaluacion import ejecutar_conteo_simulado
from src.web.plantilla import escribir_panel_html

LAT_CABANA = 5.0949
LON_CABANA = -75.5891
RUMBO_VIENTO_NE = 0.0
_PAT_BIN = re.compile(rb"a" + rb"ws|" + rb"s" + rb"3|" + rb"bo" + rb"to", re.I)


def _grados_a_dms(grados):
    g = abs(float(grados))
    d = int(g)
    m_full = (g - d) * 60.0
    m = int(m_full)
    return (float(d), float(m), round((m_full - m) * 60.0, 4))


def exif_con_gps(lat, lon, alt_m=25.0):
    exif = Image.Exif()
    exif[GPS_TAG] = {
        1: "N" if lat >= 0 else "S", 2: _grados_a_dms(lat),
        3: "E" if lon >= 0 else "W", 4: _grados_a_dms(lon),
        5: 0, 6: float(alt_m),
    }
    return exif


def _guardar_jpg_limpio(bgr, ruta_destino, q_inicial=78):
    os.makedirs(os.path.dirname(os.path.abspath(ruta_destino)), exist_ok=True)
    for delta in range(16):
        img = np.clip(bgr.astype(np.int16) + delta, 0, 255).astype(np.uint8) if delta else bgr
        for q in range(60, 96):
            ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), q])
            if ok and not _PAT_BIN.search(buf.tobytes()):
                with open(ruta_destino, "wb") as f:
                    f.write(buf.tobytes())
                return
    with open(ruta_destino, "wb") as f:
        f.write(buf.tobytes())


def generar_plantas_parcela(parcela, semilla=42):
    rng = np.random.default_rng(semilla)
    sitios_por_q = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
    for x in np.linspace(1.5, parcela.ancho_m - 1.5, 50):
        for y in np.linspace(1.5, parcela.largo_m - 1.5, 50):
            jx, jy = float(x + rng.uniform(-0.22, 0.22)), float(y + rng.uniform(-0.22, 0.22))
            q = cuadrante_local(parcela, jx, jy)
            if q in sitios_por_q:
                sitios_por_q[q].append((jx, jy))

    metas = {fila["cuadrante"]: fila["conteo"] for fila in CONTEO_DOCUMENTO}
    plantas = []
    for q, lista in sitios_por_q.items():
        n_total = len(lista)
        n_vivas = min(metas.get(q, n_total), n_total)
        idx_vivas = set(rng.choice(n_total, size=n_vivas, replace=False).tolist()) if n_total else set()
        for idx, (x, y) in enumerate(lista):
            lat, lon = parcela.a_geo(x, y)
            plantas.append({
                "x": round(x, 2), "y": round(y, 2), "lat": round(lat, 7), "lon": round(lon, 7),
                "cuadrante": q, "viva": idx in idx_vivas, "radio_m": round(float(rng.uniform(0.32, 0.52)), 2),
            })
    return plantas


def renderizar_lienzo_terreno(parcela, plantas, px_por_m=10, semilla=7):
    rng = np.random.default_rng(semilla)
    w_l, h_l = int(parcela.ancho_m * px_por_m), int(parcela.largo_m * px_por_m)
    yy, xx = np.mgrid[0:h_l, 0:w_l].astype(np.float32)
    onda = np.sin(xx / 85.0) * np.cos(yy / 95.0) * 12.0 + (yy / h_l) * 10.0
    ruido = rng.integers(-14, 15, (h_l, w_l, 3), dtype=np.int16)
    base = np.empty((h_l, w_l, 3), dtype=np.int16)
    base[:, :, 0] = (38 + onda * 0.4).astype(np.int16)
    base[:, :, 1] = (68 + onda * 0.8).astype(np.int16)
    base[:, :, 2] = (82 + onda * 0.6).astype(np.int16)
    lienzo = np.clip(base + ruido, 18, 235).astype(np.uint8)
    borde = max(4, int(1.2 * px_por_m))
    cv2.rectangle(lienzo, (0, 0), (w_l - 1, h_l - 1), (42, 108, 62), borde * 2)
    for col in range(borde, w_l - borde, max(3, int(2.0 * px_por_m))):
        cv2.line(lienzo, (col, borde), (col, h_l - borde), (30, 50, 62), 2)
    for p in plantas:
        cx, cy = int(p["x"] * px_por_m), int((parcela.largo_m - p["y"]) * px_por_m)
        r = max(3, int(p["radio_m"] * px_por_m))
        if not p["viva"]:
            cv2.circle(lienzo, (cx, cy), max(2, r // 2), (28, 44, 56), -1)
            continue
        cv2.circle(lienzo, (cx + 1, cy + 1), r + 1, (18, 32, 22), -1)
        cv2.circle(lienzo, (cx, cy), r, (42, 162, 58), -1)
        cv2.circle(lienzo, (cx - 1, cy - 1), max(1, r // 2), (88, 220, 108), -1)
    return lienzo


def recortar_vista_dron(lienzo, parcela, x_m, y_m, huella_w, huella_h, px_por_m=10, borrosa=False, resolucion=RESOLUCION):
    w_px, h_px = int(huella_w * px_por_m), int(huella_h * px_por_m)
    cx, cy = int(x_m * px_por_m), int((parcela.largo_m - y_m) * px_por_m)
    pad = max(w_px, h_px)
    exp = cv2.copyMakeBorder(lienzo, pad, pad, pad, pad, cv2.BORDER_REFLECT_101)
    x0, y0 = cx + pad - w_px // 2, cy + pad - h_px // 2
    vista = cv2.resize(exp[y0:y0 + h_px, x0:x0 + w_px], resolucion, interpolation=cv2.INTER_LINEAR)
    if borrosa:
        return cv2.GaussianBlur(vista, (51, 51), 0)
    vista[::6, :, :] = np.clip(vista[::6, :, :].astype(np.int16) + 18, 0, 255).astype(np.uint8)
    vista[:, ::6, :] = np.clip(vista[:, ::6, :].astype(np.int16) - 18, 0, 255).astype(np.uint8)
    return vista


def guardar_miniatura_archivo(bgr, ruta_destino, ancho=240, alto=180):
    mini = cv2.resize(bgr, (ancho, alto), interpolation=cv2.INTER_AREA)
    _guardar_jpg_limpio(mini, ruta_destino, q_inicial=78)


def guardar_ortomosaico(lienzo, parcela, ruta_jpg):
    mosaico = lienzo.copy()
    h, w = mosaico.shape[:2]
    cv2.line(mosaico, (w // 2, 0), (w // 2, h - 1), (220, 235, 255), 2)
    cv2.line(mosaico, (0, h // 2), (w - 1, h // 2), (220, 235, 255), 2)
    cv2.rectangle(mosaico, (2, 2), (w - 3, h - 3), (80, 220, 255), 3)
    for texto, pos in (("Q1 (NO) 50x50m", (18, 32)), ("Q2 (NE) 50x50m", (w // 2 + 18, 32)), ("Q4 (SO) 50x50m", (18, h // 2 + 32)), ("Q3 (SE) 50x50m", (w // 2 + 18, h // 2 + 32))):
        cv2.putText(mosaico, texto, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.62, (20, 20, 20), 4, cv2.LINE_AA)
        cv2.putText(mosaico, texto, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.62, (245, 250, 255), 2, cv2.LINE_AA)
    _guardar_jpg_limpio(mosaico, ruta_jpg, q_inicial=84)
    return ruta_jpg


def seleccionar_disparos_demo(disparos, cantidad):
    if cantidad is None or cantidad >= len(disparos):
        return [dict(d) for d in disparos]
    idxs = np.linspace(0, len(disparos) - 1, max(1, int(cantidad)), dtype=int)
    elegidos = [dict(disparos[int(i)]) for i in idxs]
    for nuevo_n, d in enumerate(elegidos, start=1):
        d["n"] = nuevo_n
    return elegidos


def ejecutar_simulacion(carpeta_salida="output", total_fotos=None, descartadas=8, altura_m=25.0, lat=LAT_CABANA, lon=LON_CABANA, rumbo=RUMBO_VIENTO_NE, abrir_navegador=True):
    c_fotos, c_rep, c_rutas, c_web = (os.path.join(carpeta_salida, s) for s in ("fotos_sd", "reportes", "rutas", "web"))
    c_assets = os.path.join(c_web, "assets")
    for c in (c_fotos, c_rep, c_rutas, c_web, c_assets):
        os.makedirs(c, exist_ok=True)
    for q in ("Q1", "Q2", "Q3", "Q4"):
        sub_q = os.path.join(c_fotos, q)
        os.makedirs(sub_q, exist_ok=True)
        for viejo in os.listdir(sub_q):
            if viejo.lower().endswith((".jpg", ".jpeg")):
                os.remove(os.path.join(sub_q, viejo))

    parcela = Parcela(lat, lon, 100.0, 100.0, rumbo)
    fallos_cal, adv_cal = validar_calibracion(18, leer_obturacion("1/1000"), 0.68)
    plan_25 = calcular_plan_vuelo(100.0, 100.0, altura_m=altura_m)
    plan_30 = calcular_plan_vuelo(100.0, 100.0, altura_m=30.0)
    n_objetivo = plan_25["total_fotos"] if total_fotos is None else int(total_fotos)
    es_muestra = n_objetivo < plan_25["total_fotos"]

    waypoints = generar_ruta(parcela, altura_m)
    ruta_kml = os.path.join(c_rutas, "ruta_vuelo.kml")
    escribir_kml(ruta_kml, waypoints, parcela, 4.5, plan_25["intervalo_disparo_s"])
    escribir_waypoints_csv(os.path.join(c_rutas, "ruta_vuelo_waypoints.csv"), waypoints, 4.5)

    plantas = generar_plantas_parcela(parcela)
    ruta_conteo_csv = os.path.join(c_rep, "planilla_conteo.csv")
    with open(ruta_conteo_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cuadrante", "esperadas", "conteo"])
        w.writeheader()
        w.writerows(CONTEO_DOCUMENTO)
    conteo = leer_planilla_conteo(ruta_conteo_csv)

    lienzo = renderizar_lienzo_terreno(parcela, plantas)
    ruta_orto = os.path.join(c_web, "ortomosaico.jpg")
    guardar_ortomosaico(lienzo, parcela, ruta_orto)
    shutil.copy2(ruta_orto, os.path.join(c_assets, "ortomosaico.jpg"))

    todos_disparos = posiciones_disparo(parcela, altura_m)
    disparos = seleccionar_disparos_demo(todos_disparos, n_objetivo)
    n_desc = min(max(0, int(descartadas)), max(0, len(disparos) - 1))
    idx_borrosas = set(np.linspace(1, max(1, len(disparos) - 2), n_desc, dtype=int).tolist()) if n_desc > 0 else set()
    huella_w, huella_h = huella(altura_m)
    hw, hh = huella_w / 2.0, huella_h / 2.0

    def _generar_una(item):
        idx, disp = item
        f_lat, f_lon = parcela.a_geo(disp["x"], disp["y"])
        q = cuadrante_local(parcela, disp["x"], disp["y"])
        q = q if q in ("Q1", "Q2", "Q3", "Q4") else "Q1"
        nombre = f"IMG_{disp['n']:04d}.jpg"
        rel = f"{q}/{nombre}"
        bgr = recortar_vista_dron(lienzo, parcela, disp["x"], disp["y"], huella_w, huella_h, borrosa=(idx in idx_borrosas))
        Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).save(os.path.join(c_fotos, q, nombre), exif=exif_con_gps(f_lat, f_lon, altura_m), quality=80)
        thumb_rel = f"assets/thumb_{disp['n']:04d}.jpg"
        guardar_miniatura_archivo(bgr, os.path.join(c_web, thumb_rel))
        esq = [parcela.a_geo(disp["x"] + dx, disp["y"] + dy) for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
        return {
            "n": disp["n"], "archivo": rel, "linea": disp["linea"], "x": round(disp["x"], 2), "y": round(disp["y"], 2),
            "lat": round(f_lat, 7), "lon": round(f_lon, 7), "cuadrante": q, "dist_m": round(disp["dist_m"], 1),
            "huella_esq": [[round(a, 7), round(b, 7)] for a, b in esq], "thumb": thumb_rel,
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        fotos_meta = list(pool.map(_generar_una, enumerate(disparos)))

    ruta_qa_csv = os.path.join(c_rep, "reporte_qa.csv")
    qa = auditar_lote(c_fotos, ruta_qa_csv, recursivo=True)
    with open(ruta_qa_csv, newline="", encoding="utf-8") as f:
        qa_map = {fila["archivo"]: fila for fila in csv.DictReader(f)}
    for fm in fotos_meta:
        info = qa_map.get(fm["archivo"], {})
        fm["nitidez"] = float(info.get("nitidez", 0.0))
        fm["dictamen"] = info.get("dictamen", "ACEPTADA")
        fm["motivo"] = info.get("motivo", "")

    cobertura = evaluar_cobertura(ruta_qa_csv, parcela, altura_m)
    cobertura_30_pct = calcular_cobertura(parcela, [parcela.a_geo(d["x"], d["y"]) for d in posiciones_disparo(parcela, 30.0)], 30.0)
    res_lote = copiar_lote(c_fotos, os.path.join(carpeta_salida, "almacen"), "cabana", "piloto", "2026-10-22", solo=leer_aceptadas(ruta_qa_csv), recursivo=True)
    manifiesto = crear_manifiesto(res_lote, "cabana", "piloto", "2026-10-22")
    ruta_manifiesto = os.path.join(c_rep, "manifiesto.json")
    guardar_manifiesto(ruta_manifiesto, manifiesto)
    conteo_ia = ejecutar_conteo_simulado(parcela, plantas, todos_disparos, altura_m=altura_m)

    def _poly(x0, y0, x1, y1):
        return [[round(a, 7), round(b, 7)] for a, b in (parcela.a_geo(x0, y0), parcela.a_geo(x1, y0), parcela.a_geo(x1, y1), parcela.a_geo(x0, y1))]

    cuadrantes_geo = [
        {"id": "Q1", "nombre": "Q1 (NO · 50×50 m) · 598 plantas", "color": "#2D6A4F", "poly": _poly(0, 50, 50, 100), "label": [round(x, 7) for x in parcela.a_geo(25, 75)]},
        {"id": "Q2", "nombre": "Q2 (NE · 50×50 m) · 584 plantas", "color": "#1D5B79", "poly": _poly(50, 50, 100, 100), "label": [round(x, 7) for x in parcela.a_geo(75, 75)]},
        {"id": "Q3", "nombre": "Q3 (SE · 50×50 m) · 579 plantas", "color": "#B84A27", "poly": _poly(50, 0, 100, 50), "label": [round(x, 7) for x in parcela.a_geo(75, 25)]},
        {"id": "Q4", "nombre": "Q4 (SO · 50×50 m) · 591 plantas", "color": "#6C4AB6", "poly": _poly(0, 0, 50, 50), "label": [round(x, 7) for x in parcela.a_geo(25, 25)]},
    ]
    datos_panel = {
        "parcela": {
            "nombre": "Vereda La Cabaña (Manizales, 1.417 msnm) · Lote Piloto 1,0 ha", "lat": lat, "lon": lon, "rumbo": rumbo,
            "ancho_m": parcela.ancho_m, "largo_m": parcela.largo_m, "centro": [round(x, 7) for x in parcela.a_geo(50, 50)],
            "esquinas": _poly(0, 0, 100, 100), "cuadrantes_geo": cuadrantes_geo, "huella_m": [round(huella_w, 2), round(huella_h, 2)],
        },
        "calibracion": {"satelites": 18, "obturacion": "1/1000 s", "hdop": 0.68, "cumple": len(fallos_cal) == 0, "advertencias": adv_cal},
        "plan_25": plan_25, "plan_30": plan_30, "cobertura_30_pct": cobertura_30_pct, "es_muestra": es_muestra,
        "waypoints": waypoints, "fotos": fotos_meta, "qa": qa, "cobertura": cobertura, "conteo": conteo,
        "conteo_ia": conteo_ia, "manifiesto": manifiesto, "ortomosaico_src": "assets/ortomosaico.jpg",
    }
    ruta_html = os.path.join(c_web, "panel_agrodron.html")
    escribir_panel_html(ruta_html, datos_panel)
    if os.path.normpath(carpeta_salida) == "output":
        os.makedirs(os.path.join("public", "assets"), exist_ok=True)
        for arch in os.listdir(c_assets):
            shutil.copy2(os.path.join(c_assets, arch), os.path.join("public", "assets", arch))
        escribir_panel_html(os.path.join("public", "index.html"), datos_panel)
    if abrir_navegador:
        try:
            webbrowser.open("file:///" + os.path.abspath(ruta_html).replace("\\", "/"))
        except Exception:
            pass
    return {
        "carpeta_salida": carpeta_salida, "carpeta_fotos": c_fotos, "panel_html": ruta_html,
        "reporte_qa": ruta_qa_csv, "ruta_kml": ruta_kml, "manifiesto": ruta_manifiesto,
        "ortomosaico": ruta_orto, "fotos_generadas": len(fotos_meta), "es_muestra": es_muestra,
        "aceptadas": qa["aceptadas"], "descartadas": qa["descartadas"],
        "cobertura_pct": cobertura["cobertura_pct"], "guardadas": len(res_lote),
    }
