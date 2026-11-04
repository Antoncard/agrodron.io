# Simulador completo de campo, vuelo, fotos con EXIF GPS y panel interactivo HTML
# para AgroDron - Sprint 1 / Epica 1 (Vereda La Cabana, Manizales).
import base64
import csv
import json
import math
import os
import webbrowser

import cv2
import numpy as np
from PIL import Image

import agrodron_sprint1_epica1_v3 as ad

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
    # Genera la rejilla de 50 x 50 = 2500 sitios de siembra (cada 2 m) y selecciona
    # exactamente las plantas vivas por cuadrante segun el entregable (2352 en total).
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
    # Dibuja el terreno rural de la Vereda La Cabana en BGR: suelo volcanico andino,
    # curvas de nivel/humedad (desnivel del 8% al sur), pastizales de borde, surcos,
    # plantas con follaje organico y arboles de sombrio (guamos/platanos) en linderos.
    rng = np.random.default_rng(semilla)
    ancho_lienzo = int(parcela.ancho_m * px_por_m)
    alto_lienzo = int(parcela.largo_m * px_por_m)

    # Gradiente suave de humedad y desnivel del 8% en el cuadrante Sur
    yy, xx = np.mgrid[0:alto_lienzo, 0:ancho_lienzo].astype(np.float32)
    onda = (np.sin(xx / 95.0) * np.cos(yy / 110.0) * 12.0
            + (yy / alto_lienzo) * 10.0)
    ruido = rng.integers(-14, 15, (alto_lienzo, ancho_lienzo, 3), dtype=np.int16)

    base = np.empty((alto_lienzo, ancho_lienzo, 3), dtype=np.int16)
    base[:, :, 0] = (38 + onda * 0.4).astype(np.int16)   # B (tierra humeda andina)
    base[:, :, 1] = (68 + onda * 0.8).astype(np.int16)   # G
    base[:, :, 2] = (82 + onda * 0.6).astype(np.int16)   # R
    lienzo = np.clip(base + ruido, 18, 235).astype(np.uint8)

    # Franja de pastizal rural en los bordes del lote (1,2 m alrededor)
    borde_px = max(4, int(1.2 * px_por_m))
    cv2.rectangle(lienzo, (0, 0), (ancho_lienzo - 1, alto_lienzo - 1),
                  (42, 108, 62), borde_px * 2)

    # Surcos de labranza con camellon iluminado y sombra lateral
    paso_surco = max(3, int(2.0 * px_por_m))
    for col in range(borde_px, ancho_lienzo - borde_px, paso_surco):
        cv2.line(lienzo, (col - 2, borde_px), (col - 2, alto_lienzo - borde_px),
                 (30, 50, 62), 2)
        cv2.line(lienzo, (col + 2, borde_px), (col + 2, alto_lienzo - borde_px),
                 (52, 86, 98), 1)

    # Microtextura organica (hojarasca, terrones y cobertura vegetal baja)
    for _ in range(2600):
        cx = int(rng.integers(0, ancho_lienzo))
        cy = int(rng.integers(0, alto_lienzo))
        if rng.random() < 0.55:
            lienzo[cy, cx] = (35, int(rng.integers(95, 145)), int(rng.integers(50, 85)))
        else:
            tono = int(rng.integers(85, 165))
            lienzo[cy, cx] = (tono - 15, tono, tono + 10)

    # Dibujar cada planta viva con roseta de hojas y centro de cogollo
    for p in plantas:
        cx = int(p["x"] * px_por_m)
        cy = int((parcela.largo_m - p["y"]) * px_por_m)
        r = max(3, int(p["radio_m"] * px_por_m))
        if not p["viva"]:
            # Sitio donde falto la planta (hueco de siembra)
            cv2.circle(lienzo, (cx, cy), max(2, r // 2), (28, 44, 56), -1)
            cv2.circle(lienzo, (cx, cy), max(2, r // 2) + 1, (45, 68, 82), 1)
            continue
        # Sombra proyectada sobre el surco
        cv2.circle(lienzo, (cx + 2, cy + 2), r + 1, (18, 32, 22), -1)
        # Hojas exteriores (4 foliolos cruzados)
        for dx, dy in ((r // 2, 0), (-r // 2, 0), (0, r // 2), (0, -r // 2)):
            cv2.circle(lienzo, (cx + dx, cy + dy), max(2, (r * 2) // 3),
                       (34, 138, 48), -1)
        # Copa principal y cogollo central brillante
        cv2.circle(lienzo, (cx, cy), r, (42, 162, 58), -1)
        cv2.circle(lienzo, (cx - 1, cy - 1), max(1, r // 2), (88, 220, 108), -1)

    # Estacas demarcadoras de los 4 cuadrantes (esquinas y centro)
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
    # Extrae la huella vista por la camara en (x_m, y_m) y la escala a 4000x3000
    alto_lienzo, ancho_lienzo = lienzo.shape[:2]
    w_px = int(huella_ancho_m * px_por_m)
    h_px = int(huella_alto_m * px_por_m)
    cx = int(x_m * px_por_m)
    cy = int((parcela.largo_m - y_m) * px_por_m)

    pad = max(w_px, h_px)
    expandido = cv2.copyMakeBorder(lienzo, pad, pad, pad, pad, cv2.BORDER_REFLECT_101)
    x0 = cx + pad - w_px // 2
    y0 = cy + pad - h_px // 2
    recorte = expandido[y0:y0 + h_px, x0:x0 + w_px]

    # Escalar a la resolucion del sensor (4000x3000) o la indicada
    vista = cv2.resize(recorte, resolucion, interpolation=cv2.INTER_LINEAR)
    if borrosa:
        vista = cv2.GaussianBlur(vista, (51, 51), 0)
    else:
        # Microtextura del sensor a 1/1000 s para mantener varianza del Laplaciano > 120
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
    # Dibujar las diagonales que separan Q1, Q2, Q3 y Q4
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

    # Agrupar por linea de vuelo
    por_linea = {}
    for d in disparos:
        por_linea.setdefault(d["linea"], []).append(d)
    lineas_disp = sorted(por_linea.keys())

    # Garantizar al menos 5 disparos por cada linea elegida (cubre 100 m con huella de 28,1 m)
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


def ejecutar_simulacion(carpeta_salida="demo_salida", total_fotos=48, descartadas=2,
                        altura_m=25.0, lat=LAT_CABANA, lon=LON_CABANA,
                        rumbo=RUMBO_VIENTO_NE, abrir_navegador=True):
    os.makedirs(carpeta_salida, exist_ok=True)
    carpeta_fotos = os.path.join(carpeta_salida, "fotos_sd")
    os.makedirs(carpeta_fotos, exist_ok=True)
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
    ruta_kml = os.path.join(carpeta_salida, "ruta_vuelo.kml")
    ruta_wp_csv = os.path.join(carpeta_salida, "ruta_vuelo_waypoints.csv")
    ad.escribir_kml(ruta_kml, waypoints, parcela, 4.5, plan_25["intervalo_disparo_s"])
    ad.escribir_waypoints_csv(ruta_wp_csv, waypoints, 4.5)

    # 3. Plantas y planilla de conteo Ground Truth (CA5)
    plantas = generar_plantas_parcela(parcela)
    ruta_conteo_csv = os.path.join(carpeta_salida, "planilla_conteo.csv")
    with open(ruta_conteo_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cuadrante", "esperadas", "conteo"])
        w.writeheader()
        w.writerows(CONTEO_DOCUMENTO)
    conteo = ad.leer_planilla_conteo(ruta_conteo_csv)

    # 4. Renderizar terreno y ortomosaico
    lienzo = renderizar_lienzo_terreno(parcela, plantas)
    ruta_orto = os.path.join(carpeta_salida, "ortomosaico.jpg")
    orto_b64 = guardar_ortomosaico(lienzo, parcela, ruta_orto)

    # 5. Generar fotos del vuelo con EXIF GPS (incluyendo borrosas en giros de cabecera)
    todos_disparos = ad.posiciones_disparo(parcela, altura_m)
    disparos = seleccionar_disparos_demo(todos_disparos, total_fotos)

    # Elegir como borrosas fotos en giros de cabecera de lineas interiores
    # para que las fotos vecinas mantengan el 100 % de cobertura de la hectarea
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
    ruta_qa_csv = os.path.join(carpeta_salida, "reporte_qa.csv")
    qa = ad.auditar_lote(carpeta_fotos, ruta_qa_csv, recursivo=True)

    # Enriquecer metadatos de cada foto con el resultado real del QA
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

    # 8. Simular subida a S3 solo de las fotos ACEPTADAS + manifiesto JSON
    aceptadas_set = ad.leer_aceptadas(ruta_qa_csv)
    res_s3 = ad.subir_lote(carpeta_fotos, "cabana", "piloto", "2026-10-22",
                           dry_run=True, solo=aceptadas_set, recursivo=True)
    manifiesto = ad.crear_manifiesto(res_s3, "cabana", "piloto", "2026-10-22")
    ruta_manifiesto = os.path.join(carpeta_salida, "manifiesto.json")
    with open(ruta_manifiesto, "w", encoding="utf-8") as f:
        json.dump(manifiesto, f, ensure_ascii=False, indent=2)

    # 9. Construir el panel interactivo HTML
    esquinas_geo = [parcela.a_geo(x, y) for x, y in
                    ((0, 0), (parcela.ancho_m, 0),
                     (parcela.ancho_m, parcela.largo_m), (0, parcela.largo_m))]
    centro_geo = parcela.a_geo(parcela.ancho_m / 2, parcela.largo_m / 2)
    base_geo = parcela.a_geo(-7.0, -7.0)

    # Los 4 cuadrantes se dividen por las rectas N-S y E-W a 45 grados en el mapa;
    # como rumbo = 45°, las diagonales del cuadrado coinciden con N, E, S y W:
    # Esquina (0,100) = Norte, (100,100) = Este, (100,0) = Sur, (0,0) = Oeste.
    e_sw, e_se, e_ne, e_nw = [
        [round(a, 7), round(b, 7)] for a, b in esquinas_geo
    ]
    c_pt = [round(centro_geo[0], 7), round(centro_geo[1], 7)]
    cuadrantes_geo = [
        {"id": "Q1", "nombre": "Q1 (Norte) · 598 plantas", "color": "#22c55e",
         "poly": [c_pt, e_nw, e_ne],
         "label": [round( x, 7) for x in parcela.a_geo(35, 80)]},
        {"id": "Q2", "nombre": "Q2 (Este) · 584 plantas", "color": "#38bdf8",
         "poly": [c_pt, e_ne, e_se],
         "label": [round(x, 7) for x in parcela.a_geo(80, 65)]},
        {"id": "Q3", "nombre": "Q3 (Sur - Desnivel 8%) · 579 plantas", "color": "#f59e0b",
         "poly": [c_pt, e_se, e_sw],
         "label": [round(x, 7) for x in parcela.a_geo(65, 20)]},
        {"id": "Q4", "nombre": "Q4 (Oeste) · 591 plantas", "color": "#a855f7",
         "poly": [c_pt, e_sw, e_nw],
         "label": [round(x, 7) for x in parcela.a_geo(20, 35)]},
    ]

    # Arboles de sombrio (guamos y platanos) en los linderos rurales de la finca
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
            "nombre": "Vereda La Cabaña (Zona Rural, 1.417 msnm) - Lote Piloto 1,0 ha",
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
            for p in plantas[::4]   # muestra ligera para dibujar en el mapa
        ],
    }

    ruta_html = os.path.join(carpeta_salida, "panel_agrodron.html")
    escribir_panel_html(ruta_html, datos_panel)

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
        "subidas_simuladas": len(res_s3),
    }


def escribir_panel_html(ruta_html, datos):
    json_seguro = json.dumps(datos, ensure_ascii=False)
    html = PLANTILLA_HTML.replace("__DATOS_AGRODRON__", json_seguro)
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)


PLANTILLA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgroDron - Simulación de Vuelo, Mapa y Auditoría Óptica</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<style>
  :root {
    --bg: #0b131e;
    --panel: #131f30;
    --panel-2: #192940;
    --border: #263b59;
    --text: #e7f0fa;
    --muted: #93a8c2;
    --green: #22c55e;
    --red: #ef4444;
    --amber: #f59e0b;
    --cyan: #38bdf8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.45;
  }
  header {
    background: linear-gradient(90deg, #0f2036, #163250);
    border-bottom: 1px solid var(--border);
    padding: 14px 22px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  header h1 { margin: 0; font-size: 1.25rem; letter-spacing: 0.3px; }
  header .sub { color: var(--muted); font-size: 0.86rem; }
  .badges { display: flex; gap: 8px; flex-wrap: wrap; }
  .badge {
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: var(--panel-2);
    border: 1px solid var(--border);
  }
  .badge.ok { color: #86efac; border-color: #166534; background: rgba(34,197,94,0.12); }
  .badge.warn { color: #fde68a; border-color: #92400e; background: rgba(245,158,11,0.15); }
  .container { padding: 18px 22px; max-width: 1550px; margin: 0 auto; }
  .kpis {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }
  .kpi {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
  }
  .kpi .lbl { color: var(--muted); font-size: 0.76rem; text-transform: uppercase; }
  .kpi .val { font-size: 1.4rem; font-weight: 700; margin-top: 3px; }
  .kpi .hint { color: var(--muted); font-size: 0.78rem; margin-top: 2px; }
  .main-grid {
    display: grid;
    grid-template-columns: 1.45fr 1fr;
    gap: 16px;
  }
  @media (max-width: 1100px) { .main-grid { grid-template-columns: 1fr; } }
  .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 16px;
  }
  .card h2 {
    margin: 0 0 10px 0;
    font-size: 1.02rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  #map-wrap {
    position: relative;
    height: 490px;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid var(--border);
    background: #0d1b2a;
  }
  #map, #canvas-map { width: 100%; height: 100%; }
  #canvas-map { display: none; }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    background: var(--panel-2);
    padding: 10px 12px;
    border-radius: 8px;
  }
  button, select {
    background: #1e3a5f;
    color: var(--text);
    border: 1px solid #35598a;
    padding: 7px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.84rem;
  }
  button:hover { background: #295082; }
  button.primary { background: #15803d; border-color: #22c55e; }
  button.primary:hover { background: #16a34a; }
  input[type=range] { flex: 1; min-width: 140px; accent-color: var(--cyan); }
  .cam-box {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 14px;
    align-items: start;
  }
  @media (max-width: 600px) { .cam-box { grid-template-columns: 1fr; } }
  .cam-preview {
    width: 100%;
    aspect-ratio: 4/3;
    background: #08101a;
    border: 2px solid var(--border);
    border-radius: 8px;
    object-fit: cover;
  }
  .telemetry {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    font-size: 0.85rem;
  }
  .telemetry div {
    background: var(--panel-2);
    padding: 7px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
  }
  .telemetry span { color: var(--muted); display: block; font-size: 0.73rem; }
  .pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 5px;
    font-weight: 700;
    font-size: 0.76rem;
  }
  .pill.ACEPTADA { background: rgba(34,197,94,0.2); color: #86efac; border: 1px solid #22c55e; }
  .pill.RECHAZADA { background: rgba(239,68,68,0.22); color: #fca5a5; border: 1px solid #ef4444; }
  .gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(125px, 1fr));
    gap: 9px;
    max-height: 360px;
    overflow-y: auto;
    padding-right: 4px;
  }
  .thumb-card {
    background: var(--panel-2);
    border: 2px solid var(--border);
    border-radius: 8px;
    padding: 5px;
    cursor: pointer;
    transition: transform 0.12s;
    font-size: 0.74rem;
  }
  .thumb-card:hover { transform: translateY(-2px); }
  .thumb-card.active { border-color: var(--cyan); box-shadow: 0 0 0 2px rgba(56,189,248,0.35); }
  .thumb-card.RECHAZADA { border-color: #b91c1c; }
  .thumb-card img { width: 100%; aspect-ratio: 4/3; object-fit: cover; border-radius: 4px; display: block; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th, td { padding: 7px 9px; border-bottom: 1px solid var(--border); text-align: left; }
  th { color: var(--muted); font-weight: 600; background: var(--panel-2); }
  .drone-icon {
    width: 28px; height: 28px;
    background: radial-gradient(circle, #38bdf8 35%, #0284c7 70%);
    border: 2px solid #fff;
    border-radius: 50%;
    box-shadow: 0 0 12px #38bdf8;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: bold; color: #08101a;
  }
</style>
</head>
<body>
<header>
  <div>
    <h1>🚁 AgroDron — Simulación de Vuelo, Auditoría Óptica y Carga S3</h1>
    <div class="sub" id="hdr-sub"></div>
  </div>
  <div class="badges" id="hdr-badges"></div>
</header>

<div class="container">
  <div class="kpis" id="kpi-grid"></div>

  <div class="main-grid">
    <div>
      <div class="card">
        <h2>
          <span>🗺️ Mapa de la Parcela y Simulación del Dron en Vivo</span>
          <span style="font-size:0.8rem;color:var(--muted)" id="modo-mapa">Mapa interactivo</span>
        </h2>
        <div id="map-wrap">
          <div id="map"></div>
          <canvas id="canvas-map" width="820" height="490"></canvas>
        </div>
        <div class="controls">
          <button class="primary" id="btn-play">▶ Iniciar vuelo</button>
          <button id="btn-step-b">⏮ Anterior</button>
          <button id="btn-step-f">⏭ Siguiente</button>
          <button id="btn-reset">↺ Reiniciar</button>
          <input type="range" id="slider-foto" min="0" value="0">
          <label style="font-size:0.8rem;color:var(--muted)">Velocidad:
            <select id="sel-speed">
              <option value="900">1x</option>
              <option value="450" selected>2x</option>
              <option value="180">5x</option>
            </select>
          </label>
          <button id="btn-toggle-vista">Cambiar a Vista Satelital / Lienzo</button>
        </div>
      </div>

      <div class="card">
        <h2>
          <span>📸 Galería de Fotos Extraídas de la microSD (<span id="gal-count">0</span>)</span>
          <span>
            <select id="filtro-qa">
              <option value="TODAS">Todas las fotos</option>
              <option value="ACEPTADA">Solo ACEPTADAS</option>
              <option value="RECHAZADA">Solo RECHAZADAS (borrosas)</option>
            </select>
          </span>
        </h2>
        <div class="gallery" id="galeria"></div>
      </div>
    </div>

    <div>
      <div class="card">
        <h2>
          <span>🎯 Cámara del Dron e Inspección QA en Tiempo Real</span>
          <span id="cam-badge"></span>
        </h2>
        <div class="cam-box">
          <img id="cam-img" class="cam-preview" alt="Vista de cámara del dron">
          <div class="telemetry" id="cam-tel"></div>
        </div>
      </div>

      <div class="card">
        <h2><span>📐 Corrección Técnica del Plan de Vuelo (Hallazgo H1)</span></h2>
        <table id="tabla-planes"></table>
      </div>

      <div class="card">
        <h2><span>🌱 Conteo Manual en Tierra (Ground Truth - CA5) y Ortomosaico</span></h2>
        <div style="display:grid;grid-template-columns:165px 1fr;gap:12px;align-items:center">
          <img id="img-orto" style="width:100%;border-radius:8px;border:1px solid var(--border)" alt="Ortomosaico">
          <table id="tabla-conteo"></table>
        </div>
      </div>

      <div class="card">
        <h2><span>☁️ Estado de Carga a AWS S3 (Épica 2 - Manifiesto)</span></h2>
        <div id="box-s3" style="font-size:0.85rem"></div>
      </div>
    </div>
  </div>
</div>

<script>
const D = __DATOS_AGRODRON__;

document.getElementById("hdr-sub").textContent =
  `${D.parcela.nombre} · ${D.parcela.cliente} · Rumbo líneas: ${D.parcela.rumbo}° NE`;

const badges = [
  { txt: `CA1 Calibración: ${D.calibracion.satelites} sat / ${D.calibracion.obturacion}`, ok: D.calibracion.cumple },
  { txt: `CA2 Cobertura: ${D.cobertura.cobertura_pct}%`, ok: D.cobertura.cumple_cobertura },
  { txt: `CA3 GSD a ${D.plan_25.altura_m}m: ${D.plan_25.gsd_cm_px} cm/px`, ok: D.plan_25.cumple_gsd },
  { txt: `CA4 QA: ${D.qa.aceptadas} OK / ${D.qa.descartadas} Borrosas`, ok: D.qa.aceptadas > 0 },
  { txt: `CA5 Ground Truth: ${D.conteo.conteo} plantas (${D.conteo.porcentaje}%)`, ok: true }
];
document.getElementById("hdr-badges").innerHTML = badges.map(b =>
  `<span class="badge ${b.ok ? 'ok' : 'warn'}">${b.txt}</span>`).join("");

const kpis = [
  { lbl: "Altura / GSD", val: `${D.plan_25.altura_m} m · ${D.plan_25.gsd_cm_px} cm/px`, hint: `Máx permitida: 26,67 m (< 1,0 cm/px)` },
  { lbl: "Fotos Auditadas (CA4)", val: `${D.qa.aceptadas} / ${D.qa.extraidas}`, hint: `${D.qa.descartadas} descartadas en giros · Nitidez prom: ${D.qa.nitidez_promedio_aceptadas}` },
  { lbl: "Cobertura Parcela (CA2)", val: `${D.cobertura.cobertura_pct} %`, hint: `Q1:${D.cobertura.por_cuadrante.Q1} Q2:${D.cobertura.por_cuadrante.Q2} Q3:${D.cobertura.por_cuadrante.Q3} Q4:${D.cobertura.por_cuadrante.Q4}` },
  { lbl: "Plantas en Tierra (CA5)", val: `${D.conteo.conteo.toLocaleString()}`, hint: `Esperadas: ${D.conteo.esperadas.toLocaleString()} (${D.conteo.diferencia})` },
  { lbl: "Tiempo y Baterías", val: `${D.plan_25.tiempo_vuelo_min} min · ${D.plan_25.baterias} bat`, hint: `Recorrido: ${D.plan_25.distancia_m} m a 4,5 m/s` },
  { lbl: "Lote S3 (Épica 2)", val: `${D.manifiesto.totales.SIMULADO || D.manifiesto.archivos.length} listas`, hint: `Bucket: ${D.manifiesto.bucket}` }
];
document.getElementById("kpi-grid").innerHTML = kpis.map(k =>
  `<div class="kpi"><div class="lbl">${k.lbl}</div><div class="val">${k.val}</div><div class="hint">${k.hint}</div></div>`).join("");

// Tablas
document.getElementById("tabla-planes").innerHTML = `
  <tr><th>Parámetro</th><th>Vuelo original (30 m)</th><th>Recomendado (25 m)</th></tr>
  <tr><td>GSD (cm/px)</td><td style="color:#fca5a5">${D.plan_30.gsd_cm_px} (NO cumple)</td><td style="color:#86efac">${D.plan_25.gsd_cm_px} (Cumple &lt; 1,0)</td></tr>
  <tr><td>Huella en terreno</td><td>${D.plan_30.huella_m[0]} × ${D.plan_30.huella_m[1]} m</td><td>${D.plan_25.huella_m[0]} × ${D.plan_25.huella_m[1]} m</td></tr>
  <tr><td>Líneas × Fotos/línea</td><td>${D.plan_30.lineas} × ${D.plan_30.fotos_por_linea} = ${D.plan_30.total_fotos}</td><td>${D.plan_25.lineas} × ${D.plan_25.fotos_por_linea} = ${D.plan_25.total_fotos}</td></tr>
  <tr><td>Intervalo de disparo</td><td>${D.plan_30.intervalo_disparo_s} s</td><td>${D.plan_25.intervalo_disparo_s} s</td></tr>
`;

document.getElementById("img-orto").src = D.ortomosaico_b64;
document.getElementById("tabla-conteo").innerHTML = `
  <tr><th>Cuadrante</th><th>Esperadas</th><th>Conteo</th><th>Dif.</th></tr>
  ${D.conteo.detalle.map(d => `<tr><td>${d.cuadrante}</td><td>${d.esperadas}</td><td>${d.conteo}</td><td>${d.diferencia} (${d.porcentaje}%)</td></tr>`).join("")}
  <tr style="font-weight:700"><td>TOTAL</td><td>${D.conteo.esperadas}</td><td>${D.conteo.conteo}</td><td>${D.conteo.diferencia} (${D.conteo.porcentaje}%)</td></tr>
`;

document.getElementById("box-s3").innerHTML = `
  <div><b>Prefijo destino:</b> <code>s3://${D.manifiesto.bucket}/${D.manifiesto.prefijo}</code></div>
  <div style="margin-top:4px"><b>Archivos filtrados (solo ACEPTADAS):</b> ${D.manifiesto.archivos.length} fotos (${(D.manifiesto.bytes_totales/1024/1024).toFixed(2)} MB) · Cifrado <code>AES256</code> + verificación <code>Content-MD5</code></div>
`;

// Mapa Leaflet + respaldo en Canvas
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

    // Cuadrantes Q1 a Q4 con sus colores y etiquetas sobre la finca
    D.parcela.cuadrantes_geo.forEach(q => {
      L.polygon(q.poly, {
        color: q.color, weight: 1.5, dashArray: "4,4", fillColor: q.color, fillOpacity: 0.14
      }).bindPopup(`<b>${q.nombre}</b><br>Área: 2.500 m²`).addTo(capaCuadrantes);
      const lblIcon = L.divIcon({
        className: "",
        html: `<div style="background:rgba(11,19,30,0.82);color:#fff;padding:2px 6px;border-radius:4px;border:1px solid ${q.color};font-size:11px;font-weight:700;white-space:nowrap">${q.id}</div>`,
        iconSize: [32, 18], iconAnchor: [16, 9]
      });
      L.marker(q.label, { icon: lblIcon, interactive: false }).addTo(capaCuadrantes);
    });

    // Borde de la parcela de 1,0 ha y estacas demarcadoras
    L.polygon(D.parcela.esquinas, { color: "#e2e8f0", weight: 2.5, fillOpacity: 0.03 })
      .bindPopup("<b>Lote Piloto Vereda La Cabaña</b><br>100 m × 100 m (1,0 ha) · Altitud ~1.417 msnm").addTo(capaCuadrantes);

    [...D.parcela.esquinas, D.parcela.centro].forEach((pt, i) => {
      L.circleMarker(pt, {
        radius: 4, color: "#fff", weight: 1.5, fillColor: "#ef4444", fillOpacity: 1
      }).bindPopup(`Estaca demarcadora #${i + 1}`).addTo(capaCuadrantes);
    });

    // Arboles de sombrio en el lindero y Estacion de Campo (despegue)
    D.parcela.arboles.forEach(a => {
      L.circleMarker([a.lat, a.lon], {
        radius: 6, color: "#14532d", weight: 1.5, fillColor: "#15803d", fillOpacity: 0.85
      }).bindPopup("Árbol de sombrío / lindero de la finca").addTo(capaEntornoRural);
    });

    const homeIcon = L.divIcon({
      className: "",
      html: `<div style="background:#f59e0b;color:#08101a;padding:2px 6px;border-radius:5px;border:2px solid #fff;font-weight:800;font-size:11px;white-space:nowrap">⛺ Base Dron</div>`,
      iconSize: [78, 22], iconAnchor: [39, 11]
    });
    L.marker(D.parcela.base_dron, { icon: homeIcon })
      .bindPopup("<b>Estación de Campo y Telemetría</b><br>Punto de despegue y calibración IMU/GNSS (18 satélites)").addTo(capaEntornoRural);

    // Ruta en cortacesped (12 lineas paralelas al viento NE 45°)
    const latlngsRuta = D.waypoints.map(w => [w.lat, w.lon]);
    L.polyline(latlngsRuta, { color: "#facc15", weight: 2.2, dashArray: "6,6" }).addTo(capaRuta);

    // Puntos de disparo
    D.fotos.forEach((f, idx) => {
      const col = f.dictamen === "ACEPTADA" ? "#22c55e" : "#ef4444";
      const cm = L.circleMarker([f.lat, f.lon], {
        radius: 5, color: "#0b131e", weight: 1.5, fillColor: col, fillOpacity: 0.92
      }).addTo(capaRuta);
      cm.on("click", () => seleccionarFoto(idx));
      photoMarkers.push(cm);
    });

    // Huella rectangular exacta de la camara (37,5 m x 28,12 m rotada 45° NE)
    footprintPoly = L.polygon(D.fotos[0].huella_esq, {
      color: "#38bdf8", weight: 2, fillColor: "#38bdf8", fillOpacity: 0.18
    }).addTo(map);

    const icon = L.divIcon({ className: "", html: '<div class="drone-icon">🚁</div>', iconSize: [30, 30], iconAnchor: [15, 15] });
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

  // Fondo de pradera y ladera rural de la Vereda La Cabana
  ctx.fillStyle = "#162b1e";
  ctx.fillRect(0, 0, W, H);

  const pad = 48;
  const side = Math.min(W, H) - pad * 2;
  const ox = (W - side) / 2, oy = (H - side) / 2;
  const toXY = (x, y) => [ox + (x / D.parcela.ancho_m) * side, oy + ((D.parcela.largo_m - y) / D.parcela.largo_m) * side];

  // Camino veredal de tierra al borde sur/oeste de la finca
  ctx.strokeStyle = "#6b4f35";
  ctx.lineWidth = 14;
  ctx.beginPath();
  ctx.moveTo(0, oy + side + 22);
  ctx.lineTo(W, oy + side + 18);
  ctx.stroke();

  // Fondo parcela agricola y surcos
  ctx.fillStyle = "#243b27";
  ctx.fillRect(ox, oy, side, side);
  ctx.strokeStyle = "rgba(30,52,35,0.7)";
  ctx.lineWidth = 1;
  for (let xm = 2; xm < 100; xm += 2) {
    const [sx] = toXY(xm, 0);
    ctx.beginPath();
    ctx.moveTo(sx, oy);
    ctx.lineTo(sx, oy + side);
    ctx.stroke();
  }

  // Diagonales de cuadrantes y etiquetas
  ctx.strokeStyle = "rgba(255,255,255,0.22)";
  ctx.beginPath();
  ctx.moveTo(ox, oy); ctx.lineTo(ox + side, oy + side);
  ctx.moveTo(ox + side, oy); ctx.lineTo(ox, oy + side);
  ctx.stroke();

  ctx.fillStyle = "rgba(255,255,255,0.75)";
  ctx.font = "bold 12px sans-serif";
  ctx.fillText("Q1 (Norte)", ox + side / 2 - 30, oy + 20);
  ctx.fillText("Q3 (Sur · Desnivel 8%)", ox + side / 2 - 60, oy + side - 10);
  ctx.fillText("Q4 (Oeste)", ox + 10, oy + side / 2);
  ctx.fillText("Q2 (Este)", ox + side - 68, oy + side / 2);

  // Arboles de sombrio en el lindero
  D.parcela.arboles.forEach(a => {
    const [ax, ay] = toXY(a.x, a.y);
    ctx.beginPath();
    ctx.arc(ax, ay, 8, 0, Math.PI * 2);
    ctx.fillStyle = "#15803d";
    ctx.fill();
    ctx.strokeStyle = "#052e16";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  });

  // Base de despegue rural
  const [bx, by] = toXY(-7, -7);
  ctx.fillStyle = "#f59e0b";
  ctx.fillRect(bx - 7, by - 7, 14, 14);
  ctx.fillStyle = "#fde68a";
  ctx.font = "bold 11px sans-serif";
  ctx.fillText("⛺ Base Dron", bx + 10, by + 4);

  // Plantas muestra
  D.plantas_muestra.forEach(p => {
    const [px, py] = toXY(p.x, p.y);
    ctx.fillStyle = p.viva ? "rgba(74,222,128,0.55)" : "rgba(239,68,68,0.4)";
    ctx.fillRect(px - 1.2, py - 1.2, 2.4, 2.4);
  });

  // Huella de la foto actual
  const fAct = D.fotos[idxActual];
  const [fx, fy] = toXY(fAct.x, fAct.y);
  const fw = (D.parcela.huella_m[0] / D.parcela.ancho_m) * side;
  const fh = (D.parcela.huella_m[1] / D.parcela.largo_m) * side;
  ctx.fillStyle = fAct.dictamen === "ACEPTADA" ? "rgba(56,189,248,0.18)" : "rgba(239,68,68,0.22)";
  ctx.strokeStyle = fAct.dictamen === "ACEPTADA" ? "#38bdf8" : "#ef4444";
  ctx.lineWidth = 2;
  ctx.fillRect(fx - fw / 2, fy - fh / 2, fw, fh);
  ctx.strokeRect(fx - fw / 2, fy - fh / 2, fw, fh);

  // Recorrido entre fotos
  ctx.strokeStyle = "rgba(250,204,21,0.75)";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  D.fotos.forEach((f, i) => {
    const [x, y] = toXY(f.x, f.y);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Puntos de fotos
  D.fotos.forEach((f, i) => {
    const [x, y] = toXY(f.x, f.y);
    ctx.beginPath();
    ctx.arc(x, y, i <= idxActual ? 5 : 3.5, 0, Math.PI * 2);
    ctx.fillStyle = f.dictamen === "ACEPTADA" ? "#22c55e" : "#ef4444";
    ctx.fill();
    ctx.strokeStyle = "#08101a";
    ctx.stroke();
  });

  // Dron
  ctx.beginPath();
  ctx.arc(fx, fy, 9, 0, Math.PI * 2);
  ctx.fillStyle = "#38bdf8";
  ctx.fill();
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = "#ffffff";
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
    <div class="thumb-card ${f.dictamen} ${idx === idxActual ? 'active' : ''}" id="thumb-${idx}" onclick="seleccionarFoto(${idx})">
      <img src="${f.thumb}" alt="${f.archivo}">
      <div style="display:flex;justify-content:space-between;margin-top:4px;font-weight:700">
        <span>#${f.n} (${f.cuadrante})</span>
        <span style="color:${f.dictamen==='ACEPTADA'?'#86efac':'#fca5a5'}">${f.nitidez}</span>
      </div>
      <div style="color:var(--muted);font-size:0.68rem">${f.dictamen}${f.motivo ? ' · '+f.motivo : ''}</div>
    </div>
  `).join("");
}

function seleccionarFoto(idx) {
  idxActual = Math.max(0, Math.min(D.fotos.length - 1, idx));
  slider.value = idxActual;
  const f = D.fotos[idxActual];

  document.getElementById("cam-img").src = f.thumb;
  document.getElementById("cam-badge").innerHTML =
    `<span class="pill ${f.dictamen}">${f.dictamen}${f.motivo ? ' (' + f.motivo + ')' : ''}</span>`;
  document.getElementById("cam-tel").innerHTML = `
    <div><span>Archivo / Cuadrante</span><b>${f.archivo}</b> (${f.cuadrante})</div>
    <div><span>Línea de vuelo / Disparo</span>Línea <b>${f.linea}</b> · Foto <b>#${f.n}</b> de ${D.fotos.length}</div>
    <div><span>Nitidez (Laplaciano)</span><b style="color:${f.nitidez>=120?'#86efac':'#fca5a5'}">${f.nitidez}</b> (mín: 120,0)</div>
    <div><span>Coordenadas EXIF GPS</span><b>${f.lat.toFixed(6)}, ${f.lon.toFixed(6)}</b></div>
    <div><span>Posición local en parcela</span>X: <b>${f.x} m</b> · Y: <b>${f.y} m</b></div>
    <div><span>Distancia recorrida</span><b>${f.dist_m} m</b></div>
  `;

  document.querySelectorAll(".thumb-card.active").forEach(el => el.classList.remove("active"));
  const card = document.getElementById(`thumb-${idxActual}`);
  if (card) card.classList.add("active");

  if (!usarCanvas && droneMarker) {
    droneMarker.setLatLng([f.lat, f.lon]);
    footprintPoly.setLatLngs(f.huella_esq);
    const col = f.dictamen === "ACEPTADA" ? "#38bdf8" : "#ef4444";
    footprintPoly.setStyle({ color: col, fillColor: col });
  }
  dibujarCanvas(idxActual);
}

function togglePlay() {
  const btn = document.getElementById("btn-play");
  if (timer) {
    clearInterval(timer);
    timer = null;
    btn.textContent = "▶ Continuar vuelo";
    return;
  }
  btn.textContent = "⏸ Pausar";
  const ms = parseInt(document.getElementById("sel-speed").value, 10);
  timer = setInterval(() => {
    if (idxActual >= D.fotos.length - 1) {
      clearInterval(timer);
      timer = null;
      btn.textContent = "▶ Iniciar vuelo";
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
  document.getElementById("modo-mapa").textContent = usarCanvas ? "Vista cenital de parcela (offline)" : "Mapa satelital interactivo";
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
