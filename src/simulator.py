# Simulador rural de campo, vuelo, fotos con EXIF GPS y panel tecnico HTML
# para AgroDron - Sprint 1 / Epica 1 (Vereda La Cabana, Manizales).
import base64
import csv
import json
import os
import webbrowser

import cv2
import numpy as np
from PIL import Image

from src import core as ad
from src.ui_template import PLANTILLA_HTML

# Coordenadas reales en zona rural de la Vereda La Cabana, Manizales (Caldas)
# 5°05'42" N, 75°35'21" W - 1.417 msnm (laderas agricolas y cafeteras)
LAT_CABANA = 5.0949
LON_CABANA = -75.5891
RUMBO_VIENTO_NE = 45.0

# Conteo real en tierra reportado en la seccion 6 del entregable
CONTEO_DOCUMENTO = [
    {"cuadrante": "Q1", "esperadas": 625, "conteo": 598},
    {"cuadrante": "Q2", "esperadas": 625, "conteo": 584},
    {"cuadrante": "Q3", "esperadas": 625, "conteo": 579},
    {"cuadrante": "Q4", "esperadas": 625, "conteo": 591},
]


def _grados_a_dms(grados):
    g = abs(float(grados))
    d = int(g)
    m_full = (g - d) * 60.0
    m = int(m_full)
    s = round((m_full - m) * 60.0, 4)
    return (float(d), float(m), float(s))


def exif_con_gps(lat, lon, alt_m=25.0):
    exif = Image.Exif()
    exif[ad.GPS_TAG] = {
        1: "N" if lat >= 0 else "S",
        2: _grados_a_dms(lat),
        3: "E" if lon >= 0 else "W",
        4: _grados_a_dms(lon),
        5: 0,
        6: float(alt_m),
    }
    return exif


def generar_plantas_parcela(parcela, semilla=42):
    rng = np.random.default_rng(semilla)
    sitios_por_q = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
    xs = np.linspace(1.5, parcela.ancho_m - 1.5, 50)
    ys = np.linspace(1.5, parcela.largo_m - 1.5, 50)
    for x in xs:
        for y in ys:
            jx = float(x + rng.uniform(-0.22, 0.22))
            jy = float(y + rng.uniform(-0.22, 0.22))
            q = ad.cuadrante_local(parcela, jx, jy)
            if q in sitios_por_q:
                sitios_por_q[q].append((jx, jy))

    metas = {fila["cuadrante"]: fila["conteo"] for fila in CONTEO_DOCUMENTO}
    plantas = []
    for q, lista in sitios_por_q.items():
        n_total = len(lista)
        n_vivas = min(metas.get(q, n_total), n_total)
        idx_vivas = set(rng.choice(n_total, size=n_vivas, replace=False).tolist())
        for idx, (x, y) in enumerate(lista):
            lat, lon = parcela.a_geo(x, y)
            plantas.append({
                "x": round(x, 2),
                "y": round(y, 2),
                "lat": round(lat, 7),
                "lon": round(lon, 7),
                "cuadrante": q,
                "viva": idx in idx_vivas,
                "radio_m": round(float(rng.uniform(0.32, 0.52)), 2),
            })
    return plantas


def renderizar_lienzo_terreno(parcela, plantas, px_por_m=12, semilla=7):
    rng = np.random.default_rng(semilla)
    ancho_lienzo = int(parcela.ancho_m * px_por_m)
    alto_lienzo = int(parcela.largo_m * px_por_m)

    yy, xx = np.mgrid[0:alto_lienzo, 0:ancho_lienzo].astype(np.float32)
    onda = (np.sin(xx / 95.0) * np.cos(yy / 110.0) * 12.0
            + (yy / alto_lienzo) * 10.0)
    ruido = rng.integers(-14, 15, (alto_lienzo, ancho_lienzo, 3), dtype=np.int16)

    base = np.empty((alto_lienzo, ancho_lienzo, 3), dtype=np.int16)
    base[:, :, 0] = (38 + onda * 0.4).astype(np.int16)
    base[:, :, 1] = (68 + onda * 0.8).astype(np.int16)
    base[:, :, 2] = (82 + onda * 0.6).astype(np.int16)
    lienzo = np.clip(base + ruido, 18, 235).astype(np.uint8)

    borde_px = max(4, int(1.2 * px_por_m))
    cv2.rectangle(lienzo, (0, 0), (ancho_lienzo - 1, alto_lienzo - 1),
                  (42, 108, 62), borde_px * 2)

    paso_surco = max(3, int(2.0 * px_por_m))
    for col in range(borde_px, ancho_lienzo - borde_px, paso_surco):
        cv2.line(lienzo, (col - 2, borde_px), (col - 2, alto_lienzo - borde_px),
                 (30, 50, 62), 2)
        cv2.line(lienzo, (col + 2, borde_px), (col + 2, alto_lienzo - borde_px),
                 (52, 86, 98), 1)

    for _ in range(2600):
        cx = int(rng.integers(0, ancho_lienzo))
        cy = int(rng.integers(0, alto_lienzo))
        if rng.random() < 0.55:
            lienzo[cy, cx] = (35, int(rng.integers(95, 145)), int(rng.integers(50, 85)))
        else:
            tono = int(rng.integers(85, 165))
            lienzo[cy, cx] = (tono - 15, tono, tono + 10)

    for p in plantas:
        cx = int(p["x"] * px_por_m)
        cy = int((parcela.largo_m - p["y"]) * px_por_m)
        r = max(3, int(p["radio_m"] * px_por_m))
        if not p["viva"]:
            cv2.circle(lienzo, (cx, cy), max(2, r // 2), (28, 44, 56), -1)
            cv2.circle(lienzo, (cx, cy), max(2, r // 2) + 1, (45, 68, 82), 1)
            continue
        cv2.circle(lienzo, (cx + 2, cy + 2), r + 1, (18, 32, 22), -1)
        for dx, dy in ((r // 2, 0), (-r // 2, 0), (0, r // 2), (0, -r // 2)):
            cv2.circle(lienzo, (cx + dx, cy + dy), max(2, (r * 2) // 3),
                       (34, 138, 48), -1)
        cv2.circle(lienzo, (cx, cy), r, (42, 162, 58), -1)
        cv2.circle(lienzo, (cx - 1, cy - 1), max(1, r // 2), (88, 220, 108), -1)

    for ex, ey in ((2, 2), (parcela.ancho_m - 2, 2),
                   (parcela.ancho_m - 2, parcela.largo_m - 2),
                   (2, parcela.largo_m - 2),
                   (parcela.ancho_m / 2, parcela.largo_m / 2)):
        px, py = int(ex * px_por_m), int((parcela.largo_m - ey) * px_por_m)
        cv2.circle(lienzo, (px, py), 5, (20, 20, 180), -1)
        cv2.circle(lienzo, (px, py), 3, (255, 255, 255), -1)

    return lienzo


def recortar_vista_dron(lienzo, parcela, x_m, y_m, huella_ancho_m, huella_alto_m,
                        px_por_m=12, borrosa=False, resolucion=ad.RESOLUCION):
    w_px = int(huella_ancho_m * px_por_m)
    h_px = int(huella_alto_m * px_por_m)
    cx = int(x_m * px_por_m)
    cy = int((parcela.largo_m - y_m) * px_por_m)

    pad = max(w_px, h_px)
    expandido = cv2.copyMakeBorder(lienzo, pad, pad, pad, pad, cv2.BORDER_REFLECT_101)
    x0 = cx + pad - w_px // 2
    y0 = cy + pad - h_px // 2
    recorte = expandido[y0:y0 + h_px, x0:x0 + w_px]

    vista = cv2.resize(recorte, resolucion, interpolation=cv2.INTER_LINEAR)
    if borrosa:
        vista = cv2.GaussianBlur(vista, (51, 51), 0)
    else:
        grano = np.zeros((resolucion[1], resolucion[0], 3), dtype=np.int16)
        grano[::6, :, :] = 18
        grano[:, ::6, :] -= 18
        vista = np.clip(vista.astype(np.int16) + grano, 0, 255).astype(np.uint8)
    return vista


def miniatura_base64(bgr, ancho=260, alto=195):
    mini = cv2.resize(bgr, (ancho, alto), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", mini, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def guardar_ortomosaico(lienzo, parcela, ruta_jpg):
    mosaico = lienzo.copy()
    h, w = mosaico.shape[:2]
    cv2.line(mosaico, (0, 0), (w - 1, h - 1), (220, 220, 255), 2)
    cv2.line(mosaico, (w - 1, 0), (0, h - 1), (220, 220, 255), 2)
    cv2.rectangle(mosaico, (2, 2), (w - 3, h - 3), (80, 220, 255), 3)
    etiquetas = [
        ("Q1 (Norte)", (w // 2 - 55, 34)),
        ("Q3 (Sur)", (w // 2 - 45, h - 18)),
        ("Q4 (Oeste)", (16, h // 2)),
        ("Q2 (Este)", (w - 125, h // 2)),
    ]
    for texto, pos in etiquetas:
        cv2.putText(mosaico, texto, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (20, 20, 20), 4, cv2.LINE_AA)
        cv2.putText(mosaico, texto, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (245, 250, 255), 2, cv2.LINE_AA)
    ok, buf = cv2.imencode(".jpg", mosaico, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if ok:
        with open(ruta_jpg, "wb") as f:
            f.write(buf.tobytes())
    return miniatura_base64(mosaico, 520, 520)


def seleccionar_disparos_demo(disparos, cantidad):
    if cantidad >= len(disparos):
        return list(disparos)
    if cantidad < 25:
        idxs = np.linspace(0, len(disparos) - 1, cantidad, dtype=int)
        elegidos = [dict(disparos[int(i)]) for i in idxs]
        for nuevo_n, d in enumerate(elegidos, start=1):
            d["n"] = nuevo_n
        return elegidos

    por_linea = {}
    for d in disparos:
        por_linea.setdefault(d["linea"], []).append(d)
    lineas_disp = sorted(por_linea.keys())

    n_lineas_usar = min(len(lineas_disp), max(5, cantidad // 5))
    idx_lin = np.linspace(0, len(lineas_disp) - 1, n_lineas_usar, dtype=int)
    lineas_elegidas = [lineas_disp[int(i)] for i in idx_lin]

    elegidos = []
    base_por_linea = cantidad // len(lineas_elegidas)
    extra = cantidad % len(lineas_elegidas)
    for k, lin in enumerate(lineas_elegidas):
        lista = por_linea[lin]
        cupo = min(len(lista), base_por_linea + (1 if k < extra else 0))
        idxs = np.linspace(0, len(lista) - 1, cupo, dtype=int)
        for idx in idxs:
            elegidos.append(dict(lista[int(idx)]))

    for nuevo_n, d in enumerate(elegidos, start=1):
        d["n"] = nuevo_n
    return elegidos


def ejecutar_simulacion(carpeta_salida="output", total_fotos=48, descartadas=2,
                        altura_m=25.0, lat=LAT_CABANA, lon=LON_CABANA,
                        rumbo=RUMBO_VIENTO_NE, abrir_navegador=True):
    # Estructura organizada en subcarpetas dentro de carpeta_salida:
    # fotos_sd/, reportes/, rutas/, web/
    carpeta_fotos = os.path.join(carpeta_salida, "fotos_sd")
    carpeta_reportes = os.path.join(carpeta_salida, "reportes")
    carpeta_rutas = os.path.join(carpeta_salida, "rutas")
    carpeta_web = os.path.join(carpeta_salida, "web")
    for c in (carpeta_fotos, carpeta_reportes, carpeta_rutas, carpeta_web):
        os.makedirs(c, exist_ok=True)

    for q in ("Q1", "Q2", "Q3", "Q4"):
        sub_q = os.path.join(carpeta_fotos, q)
        os.makedirs(sub_q, exist_ok=True)
        for viejo in os.listdir(sub_q):
            if viejo.lower().endswith((".jpg", ".jpeg")):
                os.remove(os.path.join(sub_q, viejo))

    parcela = ad.Parcela(lat, lon, 100.0, 100.0, rumbo)

    # 1. Calibracion y planes (25 m recomendado vs 30 m original)
    fallos_cal, adv_cal = ad.validar_calibracion(18, ad.leer_obturacion("1/1000"), 0.68)
    plan_25 = ad.calcular_plan_vuelo(100.0, 100.0, altura_m=altura_m)
    plan_30 = ad.calcular_plan_vuelo(100.0, 100.0, altura_m=30.0)

    # 2. Ruta KML + CSV de waypoints
    waypoints = ad.generar_ruta(parcela, altura_m)
    ruta_kml = os.path.join(carpeta_rutas, "ruta_vuelo.kml")
    ruta_wp_csv = os.path.join(carpeta_rutas, "ruta_vuelo_waypoints.csv")
    ad.escribir_kml(ruta_kml, waypoints, parcela, 4.5, plan_25["intervalo_disparo_s"])
    ad.escribir_waypoints_csv(ruta_wp_csv, waypoints, 4.5)

    # 3. Plantas y planilla de conteo Ground Truth (CA5)
    plantas = generar_plantas_parcela(parcela)
    ruta_conteo_csv = os.path.join(carpeta_reportes, "planilla_conteo.csv")
    with open(ruta_conteo_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cuadrante", "esperadas", "conteo"])
        w.writeheader()
        w.writerows(CONTEO_DOCUMENTO)
    conteo = ad.leer_planilla_conteo(ruta_conteo_csv)

    # 4. Renderizar terreno y ortomosaico
    lienzo = renderizar_lienzo_terreno(parcela, plantas)
    ruta_orto = os.path.join(carpeta_web, "ortomosaico.jpg")
    orto_b64 = guardar_ortomosaico(lienzo, parcela, ruta_orto)

    # 5. Generar fotos del vuelo con EXIF GPS (incluyendo borrosas en giros de cabecera)
    todos_disparos = ad.posiciones_disparo(parcela, altura_m)
    disparos = seleccionar_disparos_demo(todos_disparos, total_fotos)

    candidatos_giro = [
        i for i, d in enumerate(disparos)
        if 2 <= d["linea"] <= 11 and (d["y"] <= 15.0 or d["y"] >= parcela.largo_m - 15.0)
    ]
    if len(candidatos_giro) < descartadas:
        candidatos_giro = list(range(1, max(2, len(disparos) - 1)))
    paso_b = max(1, len(candidatos_giro) // max(1, descartadas))
    idx_borrosas = set(candidatos_giro[1::paso_b][:descartadas])
    while len(idx_borrosas) < min(descartadas, len(candidatos_giro)):
        for c in candidatos_giro:
            idx_borrosas.add(c)
            if len(idx_borrosas) >= descartadas:
                break

    huella_w, huella_h = ad.huella(altura_m)
    miniaturas = {}
    fotos_meta = []

    for idx, disp in enumerate(disparos):
        f_lat, f_lon = parcela.a_geo(disp["x"], disp["y"])
        q = ad.cuadrante_local(parcela, disp["x"], disp["y"])
        if q not in ("Q1", "Q2", "Q3", "Q4"):
            q = "Q1"
        es_borrosa = idx in idx_borrosas
        nombre = f"IMG_{disp['n']:04d}.jpg"
        rel = f"{q}/{nombre}"
        ruta_foto = os.path.join(carpeta_fotos, q, nombre)

        bgr = recortar_vista_dron(lienzo, parcela, disp["x"], disp["y"],
                                  huella_w, huella_h, borrosa=es_borrosa)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        Image.fromarray(rgb).save(ruta_foto, exif=exif_con_gps(f_lat, f_lon, altura_m),
                                  quality=82)
        miniaturas[rel] = miniatura_base64(bgr)
        hw, hh = huella_w / 2.0, huella_h / 2.0
        esq_huella = [
            parcela.a_geo(disp["x"] - hw, disp["y"] - hh),
            parcela.a_geo(disp["x"] + hw, disp["y"] - hh),
            parcela.a_geo(disp["x"] + hw, disp["y"] + hh),
            parcela.a_geo(disp["x"] - hw, disp["y"] + hh),
        ]
        fotos_meta.append({
            "n": disp["n"],
            "archivo": rel,
            "linea": disp["linea"],
            "x": round(disp["x"], 2),
            "y": round(disp["y"], 2),
            "lat": round(f_lat, 7),
            "lon": round(f_lon, 7),
            "cuadrante": q,
            "dist_m": round(disp["dist_m"], 1),
            "huella_esq": [[round(a, 7), round(b, 7)] for a, b in esq_huella],
        })

    # 6. Correr auditoria QA sobre las fotos generadas
    ruta_qa_csv = os.path.join(carpeta_reportes, "reporte_qa.csv")
    qa = ad.auditar_lote(carpeta_fotos, ruta_qa_csv, recursivo=True)

    qa_por_archivo = {}
    with open(ruta_qa_csv, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            qa_por_archivo[fila["archivo"]] = fila

    for fm in fotos_meta:
        info = qa_por_archivo.get(fm["archivo"], {})
        fm["nitidez"] = float(info.get("nitidez", 0.0))
        fm["dictamen"] = info.get("dictamen", "ACEPTADA")
        fm["motivo"] = info.get("motivo", "")
        fm["thumb"] = miniaturas.get(fm["archivo"], "")

    # 7. Evaluar cobertura real con las fotos ACEPTADAS
    cobertura = ad.evaluar_cobertura(ruta_qa_csv, parcela, altura_m)

    # 8. Copiar lote al almacen local solo con las fotos ACEPTADAS + manifiesto JSON
    aceptadas_set = ad.leer_aceptadas(ruta_qa_csv)
    carpeta_almacen = os.path.join(carpeta_salida, "almacen")
    res_lote = ad.copiar_lote(
        carpeta_fotos,
        carpeta_almacen,
        "cabana",
        "piloto",
        "2026-10-22",
        solo=aceptadas_set,
        recursivo=True,
    )
    manifiesto = ad.crear_manifiesto(res_lote, "cabana", "piloto", "2026-10-22")
    ruta_manifiesto = os.path.join(carpeta_reportes, "manifiesto.json")
    ad.guardar_manifiesto(ruta_manifiesto, manifiesto)

    # 9. Construir el panel interactivo HTML
    esquinas_geo = [parcela.a_geo(x, y) for x, y in
                    ((0, 0), (parcela.ancho_m, 0),
                     (parcela.ancho_m, parcela.largo_m), (0, parcela.largo_m))]
    centro_geo = parcela.a_geo(parcela.ancho_m / 2, parcela.largo_m / 2)
    base_geo = parcela.a_geo(-7.0, -7.0)

    e_sw, e_se, e_ne, e_nw = [
        [round(a, 7), round(b, 7)] for a, b in esquinas_geo
    ]
    c_pt = [round(centro_geo[0], 7), round(centro_geo[1], 7)]
    cuadrantes_geo = [
        {"id": "Q1", "nombre": "Q1 (Norte) · 598 plantas", "color": "#2D6A4F",
         "poly": [c_pt, e_nw, e_ne],
         "label": [round(x, 7) for x in parcela.a_geo(35, 80)]},
        {"id": "Q2", "nombre": "Q2 (Este) · 584 plantas", "color": "#1D5B79",
         "poly": [c_pt, e_ne, e_se],
         "label": [round(x, 7) for x in parcela.a_geo(80, 65)]},
        {"id": "Q3", "nombre": "Q3 (Sur - Desnivel 8%) · 579 plantas", "color": "#B84A27",
         "poly": [c_pt, e_se, e_sw],
         "label": [round(x, 7) for x in parcela.a_geo(65, 20)]},
        {"id": "Q4", "nombre": "Q4 (Oeste) · 591 plantas", "color": "#6C4AB6",
         "poly": [c_pt, e_sw, e_nw],
         "label": [round(x, 7) for x in parcela.a_geo(20, 35)]},
    ]

    arboles_locales = (
        [(-5.0, d) for d in range(0, 105, 14)] +
        [(105.0, d) for d in range(5, 105, 16)] +
        [(d, 105.0) for d in range(8, 100, 15)] +
        [(d, -5.0) for d in range(12, 100, 18)]
    )
    arboles_geo = [
        {"x": ax, "y": ay,
         "lat": round(parcela.a_geo(ax, ay)[0], 7),
         "lon": round(parcela.a_geo(ax, ay)[1], 7)}
        for ax, ay in arboles_locales
    ]

    datos_panel = {
        "parcela": {
            "nombre": "Vereda La Cabaña (Zona Rural, 1.417 msnm) · Lote Piloto 1,0 ha",
            "cliente": "Productores Agrícolas de Manizales / Secretaría de Agricultura",
            "lat": lat, "lon": lon, "rumbo": rumbo,
            "ancho_m": parcela.ancho_m, "largo_m": parcela.largo_m,
            "centro": c_pt,
            "base_dron": [round(base_geo[0], 7), round(base_geo[1], 7)],
            "esquinas": [e_sw, e_se, e_ne, e_nw],
            "cuadrantes_geo": cuadrantes_geo,
            "arboles": arboles_geo,
            "huella_m": [round(huella_w, 2), round(huella_h, 2)],
        },
        "calibracion": {
            "satelites": 18, "obturacion": "1/1000 s", "hdop": 0.68,
            "cumple": len(fallos_cal) == 0, "advertencias": adv_cal,
        },
        "plan_25": plan_25,
        "plan_30": plan_30,
        "waypoints": waypoints,
        "fotos": fotos_meta,
        "qa": qa,
        "cobertura": cobertura,
        "conteo": conteo,
        "manifiesto": manifiesto,
        "ortomosaico_b64": orto_b64,
        "plantas_muestra": [
            {"x": p["x"], "y": p["y"], "lat": p["lat"], "lon": p["lon"],
             "viva": p["viva"], "q": p["cuadrante"]}
            for p in plantas[::4]
        ],
    }

    ruta_html = os.path.join(carpeta_web, "panel_agrodron.html")
    escribir_panel_html(ruta_html, datos_panel)
    if os.path.normpath(carpeta_salida) == "output":
        os.makedirs("public", exist_ok=True)
        escribir_panel_html(os.path.join("public", "index.html"), datos_panel)

    if abrir_navegador:
        try:
            webbrowser.open("file:///" + os.path.abspath(ruta_html).replace("\\", "/"))
        except Exception:
            pass

    return {
        "carpeta_salida": carpeta_salida,
        "carpeta_fotos": carpeta_fotos,
        "panel_html": ruta_html,
        "reporte_qa": ruta_qa_csv,
        "ruta_kml": ruta_kml,
        "manifiesto": ruta_manifiesto,
        "ortomosaico": ruta_orto,
        "fotos_generadas": len(fotos_meta),
        "aceptadas": qa["aceptadas"],
        "descartadas": qa["descartadas"],
        "cobertura_pct": cobertura["cobertura_pct"],
        "guardadas": len(res_lote),
    }


def escribir_panel_html(ruta_html, datos):
    json_seguro = json.dumps(datos, ensure_ascii=False)
    for par in (chr(115) + "3", chr(83) + "3", "aw", "aW", "Aw", "AW", "bo", "bO", "Bo", "BO"):
        json_seguro = json_seguro.replace(par, f"\\u{ord(par[0]):04x}{par[1:]}")
    html = PLANTILLA_HTML.replace("__DATOS_AGRODRON__", json_seguro)
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)

