# Servicios de consulta, deficit, densidad 10x10, huecos de resiembra y PDF de 1 pagina (Epica 4)
from datetime import datetime, timezone
import io
import csv
import math
import os
import xml.etree.ElementTree as ET

import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.dominio.parcela import Parcela, cuadrante_local
from src.ml.evaluacion import semaforo_error
from src.db.models import (
    ConteoCuadrante,
    CorridaIA,
    Cuadrante,
    Deteccion,
    Finca,
    GroundTruth,
    Imagen,
    ModeloIA,
    ParcelaDB,
    Reporte,
    Vuelo,
)

ORIENTACION_DESC = {
    "Q1": "Noroeste (NO)",
    "Q2": "Noreste (NE)",
    "Q3": "Sureste (SE)",
    "Q4": "Suroeste (SO)",
}


def frase_lenguaje_llano(codigo: str, deficit: int, esperadas: int) -> str:
    orient = ORIENTACION_DESC.get(codigo, codigo)
    if deficit > 0:
        pct = round(deficit * 100.0 / esperadas, 1) if esperadas else 0.0
        prio = "prioridad alta de resiembra" if pct >= 7.0 else "revisión moderada"
        return f"En el cuadrante {codigo} ({orient}) faltan unas {deficit} plantas de {esperadas} esperadas ({pct} %) — {prio}."
    if deficit < 0:
        return f"En el cuadrante {codigo} ({orient}) se estiman {abs(deficit)} plantas sobre la meta de {esperadas}."
    return f"El cuadrante {codigo} ({orient}) está al 100 % con {esperadas} plantas."


def calcular_mapa_densidad(puntos_xy, parcela: Parcela, plantas_esperadas: int = 2500, celda_m: float = 10.0):
    # Idea 2 / UI-02: grilla 10x10 m con densidad plantas/ha
    nx = max(1, int(round(parcela.ancho_m / celda_m)))
    ny = max(1, int(round(parcela.largo_m / celda_m)))
    conteos = [[0 for _ in range(nx)] for _ in range(ny)]
    for x_m, y_m in puntos_xy:
        ix = min(nx - 1, max(0, int(x_m // celda_m)))
        iy = min(ny - 1, max(0, int(y_m // celda_m)))
        conteos[iy][ix] += 1

    esp_celda = max(1.0, plantas_esperadas / (nx * ny))
    celdas = []
    for iy in range(ny):
        for ix in range(nx):
            cx = (ix + 0.5) * celda_m
            cy = (iy + 0.5) * celda_m
            n_pl = conteos[iy][ix]
            dens_ha = round(n_pl * (10000.0 / (celda_m * celda_m)))
            ratio = n_pl / esp_celda
            if ratio >= 0.92:
                nivel = "OPTIMO"
            elif ratio >= 0.80:
                nivel = "MEDIO"
            elif ratio >= 0.68:
                nivel = "BAJO"
            else:
                nivel = "CRITICO"
            celdas.append({
                "ix": ix,
                "iy": iy,
                "x_m": round(cx, 1),
                "y_m": round(cy, 1),
                "cuadrante": cuadrante_local(parcela, cx, cy),
                "plantas": n_pl,
                "esperadas": int(round(esp_celda)),
                "densidad_ha": dens_ha,
                "nivel": nivel,
            })
    return celdas


def calcular_huecos_resiembra(puntos_xy, parcela: Parcela, radio_sitio_m: float = 1.15):
    # Idea 1: compara la malla esperada 50x50 (2.500 sitios) contra detecciones
    xs = np.linspace(1.5, parcela.ancho_m - 1.5, 50)
    ys = np.linspace(1.5, parcela.largo_m - 1.5, 50)
    sitios = np.array([(float(x), float(y)) for x in xs for y in ys], dtype=np.float64)
    det_arr = np.asarray(puntos_xy, dtype=np.float64) if len(puntos_xy) else np.empty((0, 2), dtype=np.float64)

    if det_arr.size == 0:
        faltantes = sitios
    else:
        # Distancia minima vectorizada via producto matricial BLAS (< 15 ms para 2500 x 2352)
        s2 = np.sum(sitios * sitios, axis=1, keepdims=True)
        d2 = np.sum(det_arr * det_arr, axis=1)[None, :]
        dist2 = np.maximum(0.0, s2 + d2 - 2.0 * (sitios @ det_arr.T))
        dist_min = np.sqrt(dist2.min(axis=1))
        faltantes = sitios[dist_min > radio_sitio_m]

    huecos = []
    for idx, (x_m, y_m) in enumerate(faltantes, start=1):
        lat, lon = parcela.a_geo(float(x_m), float(y_m))
        huecos.append({
            "id": f"H-{idx:04d}",
            "cuadrante": cuadrante_local(parcela, float(x_m), float(y_m)),
            "x_m": round(float(x_m), 2),
            "y_m": round(float(y_m), 2),
            "lat": round(float(lat), 7),
            "lon": round(float(lon), 7),
        })
    return huecos


def exportar_huecos_csv(huecos) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "cuadrante", "lat", "lon", "x_m", "y_m"])
    for h in huecos:
        w.writerow([h["id"], h["cuadrante"], h["lat"], h["lon"], h["x_m"], h["y_m"]])
    return buf.getvalue()


def exportar_huecos_gpx(huecos, nombre_lote: str = "Vereda La Cabana") -> str:
    root = ET.Element("gpx", version="1.1", creator="AgroDron", xmlns="http://www.topografix.com/GPX/1/1")
    meta = ET.SubElement(root, "metadata")
    ET.SubElement(meta, "name").text = f"Huecos de resiembra - {nombre_lote}"
    for h in huecos:
        wpt = ET.SubElement(root, "wpt", lat=str(h["lat"]), lon=str(h["lon"]))
        ET.SubElement(wpt, "name").text = h["id"]
        ET.SubElement(wpt, "desc").text = f"Cuadrante {h['cuadrante']} (X={h['x_m']}m, Y={h['y_m']}m)"
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def obtener_ultimo_vuelo(session, parcela_id: int, vuelo_id: int | None = None):
    # BD-07: consulta el ultimo vuelo (o uno especifico) + ultima corrida LISTA
    parcela_db = session.get(ParcelaDB, parcela_id)
    if parcela_db is None:
        return None
    finca = session.get(Finca, parcela_db.finca_id)
    parcela_geo = Parcela(
        parcela_db.lat_origen,
        parcela_db.lon_origen,
        parcela_db.ancho_m,
        parcela_db.largo_m,
        parcela_db.rumbo_deg,
    )

    if vuelo_id is not None:
        vuelo = session.get(Vuelo, vuelo_id)
        if vuelo is None or vuelo.parcela_id != parcela_id:
            return None
    else:
        vuelo = (
            session.query(Vuelo)
            .filter(Vuelo.parcela_id == parcela_id)
            .order_by(Vuelo.fecha.desc(), Vuelo.id.desc())
            .first()
        )
        if vuelo is None:
            return None

    corrida = (
        session.query(CorridaIA)
        .filter(CorridaIA.vuelo_id == vuelo.id, CorridaIA.estado == "LISTA")
        .order_by(CorridaIA.id.desc())
        .first()
    )
    if corrida is None:
        corrida = (
            session.query(CorridaIA)
            .filter(CorridaIA.vuelo_id == vuelo.id)
            .order_by(CorridaIA.id.desc())
            .first()
        )

    modelo = session.get(ModeloIA, corrida.modelo_id) if corrida else None
    cuadrantes_db = (
        session.query(Cuadrante)
        .filter(Cuadrante.parcela_id == parcela_db.id)
        .order_by(Cuadrante.codigo.asc())
        .all()
    )

    gt_por_cuadrante = {}
    for q in cuadrantes_db:
        gt = (
            session.query(GroundTruth)
            .filter(GroundTruth.cuadrante_id == q.id)
            .order_by(GroundTruth.fecha.desc(), GroundTruth.id.desc())
            .first()
        )
        gt_por_cuadrante[q.id] = gt.contadas if gt else q.esperadas

    conteos_db = {}
    if corrida:
        for cc in session.query(ConteoCuadrante).filter(ConteoCuadrante.corrida_id == corrida.id).all():
            conteos_db[cc.cuadrante_id] = cc

    cuadrantes_out = []
    tot_esp, tot_det, tot_gt = 0, 0, 0
    for q in cuadrantes_db:
        cc = conteos_db.get(q.id)
        det = cc.detectadas if cc else 0
        esp = cc.esperadas if cc else q.esperadas
        gt_val = gt_por_cuadrante.get(q.id, esp)
        deficit = esp - det
        deficit_pct = round(deficit * 100.0 / esp, 2) if esp else 0.0
        err_gt = cc.error_vs_gt_pct if cc else (round(abs(det - gt_val) * 100.0 / gt_val, 2) if gt_val else 0.0)
        sem = cc.semaforo if cc else semaforo_error(err_gt, nivel="cuadrante")
        cuadrantes_out.append({
            "id": q.id,
            "codigo": q.codigo,
            "orientacion": q.orientacion,
            "esperadas": esp,
            "detectadas": det,
            "ground_truth": gt_val,
            "deficit": deficit,
            "deficit_pct": deficit_pct,
            "error_vs_gt_pct": err_gt,
            "semaforo": sem,
            "frase": frase_lenguaje_llano(q.codigo, deficit, esp),
        })
        tot_esp += esp
        tot_det += det
        tot_gt += gt_val

    tot_deficit = tot_esp - tot_det
    tot_deficit_pct = round(tot_deficit * 100.0 / tot_esp, 2) if tot_esp else 0.0
    tot_err_gt = round(abs(tot_det - tot_gt) * 100.0 / tot_gt, 2) if tot_gt else 0.0
    tot_sesgo = round((tot_det - tot_gt) * 100.0 / tot_gt, 2) if tot_gt else 0.0
    sem_total = semaforo_error(tot_err_gt, nivel="total")

    det_xy = []
    if corrida:
        det_rows = (
            session.query(Deteccion.x_m, Deteccion.y_m)
            .filter(Deteccion.corrida_id == corrida.id, Deteccion.fusionada.is_(True))
            .all()
        )
        det_xy = [(r[0], r[1]) for r in det_rows]

    densidad = calcular_mapa_densidad(det_xy, parcela_geo, tot_esp or parcela_db.plantas_esperadas)
    huecos = calcular_huecos_resiembra(det_xy, parcela_geo) if det_xy else []

    imgs_tot = session.query(Imagen).filter(Imagen.vuelo_id == vuelo.id).count()
    imgs_ok = session.query(Imagen).filter(Imagen.vuelo_id == vuelo.id, Imagen.dictamen == "ACEPTADA").count()

    # Idea 6: historico de vuelos de la parcela
    vuelos_hist = (
        session.query(Vuelo)
        .filter(Vuelo.parcela_id == parcela_db.id)
        .order_by(Vuelo.fecha.asc(), Vuelo.id.asc())
        .all()
    )
    historico = []
    for vh in vuelos_hist:
        ch = (
            session.query(CorridaIA)
            .filter(CorridaIA.vuelo_id == vh.id, CorridaIA.estado == "LISTA")
            .order_by(CorridaIA.id.desc())
            .first()
        )
        det_h = ch.total_detectadas if ch else 0
        def_h = (tot_esp or parcela_db.plantas_esperadas) - det_h if ch else None
        historico.append({
            "vuelo_id": vh.id,
            "fecha": vh.fecha,
            "altura_m": vh.altura_m,
            "gsd_cm_px": vh.gsd_cm_px,
            "estado": vh.estado,
            "detectadas": det_h,
            "deficit": def_h,
            "deficit_pct": round(def_h * 100.0 / (tot_esp or 2500), 2) if def_h is not None else None,
        })

    reporte_db = session.query(Reporte).filter(Reporte.corrida_id == corrida.id).first() if corrida else None

    return {
        "finca": {
            "id": finca.id,
            "nombre": finca.nombre,
            "vereda": finca.vereda,
            "municipio": finca.municipio,
            "altitud_msnm": finca.altitud_msnm,
        } if finca else None,
        "parcela": {
            "id": parcela_db.id,
            "nombre": parcela_db.nombre,
            "lat_origen": parcela_db.lat_origen,
            "lon_origen": parcela_db.lon_origen,
            "ancho_m": parcela_db.ancho_m,
            "largo_m": parcela_db.largo_m,
            "rumbo_deg": parcela_db.rumbo_deg,
            "plantas_esperadas": parcela_db.plantas_esperadas,
        },
        "vuelo": {
            "id": vuelo.id,
            "fecha": vuelo.fecha,
            "altura_m": vuelo.altura_m,
            "gsd_cm_px": vuelo.gsd_cm_px,
            "solape_frontal": vuelo.solape_frontal,
            "solape_lateral": vuelo.solape_lateral,
            "velocidad_ms": vuelo.velocidad_ms,
            "satelites": vuelo.satelites,
            "hdop": vuelo.hdop,
            "obturacion": vuelo.obturacion,
            "estado": vuelo.estado,
            "imagenes_totales": imgs_tot,
            "imagenes_aceptadas": imgs_ok,
        },
        "corrida": {
            "id": corrida.id,
            "estado": corrida.estado,
            "umbral_confianza": corrida.umbral_confianza,
            "radio_fusion_m": corrida.radio_fusion_m,
            "total_detectadas": corrida.total_detectadas,
            "reporte_id": reporte_db.id if reporte_db else None,
        } if corrida else None,
        "modelo": {
            "id": modelo.id,
            "nombre": modelo.nombre,
            "version": modelo.version,
            "arquitectura": modelo.arquitectura,
            "sha256": modelo.sha256,
            "dataset_version": modelo.dataset_version,
            "metricas": modelo.metricas_json,
        } if modelo else None,
        "resumen": {
            "esperadas": tot_esp,
            "detectadas": tot_det,
            "ground_truth": tot_gt,
            "deficit": tot_deficit,
            "deficit_pct": tot_deficit_pct,
            "error_vs_gt_pct": tot_err_gt,
            "sesgo_pct": tot_sesgo,
            "semaforo": sem_total,
            "frase_principal": f"Esperadas {tot_esp:,} · Estimadas {tot_det:,} · Déficit {tot_deficit} ({tot_deficit_pct} %)".replace(",", "."),
        },
        "cuadrantes": cuadrantes_out,
        "densidad_10x10": densidad,
        "huecos_resiembra": huecos,
        "historico_vuelos": historico,
    }


def _color_celda_densidad(nivel: str):
    return {
        "OPTIMO": colors.HexColor("#2D6A4F"),
        "MEDIO": colors.HexColor("#52B788"),
        "BAJO": colors.HexColor("#E9C46A"),
        "CRITICO": colors.HexColor("#B84A27"),
    }.get(nivel, colors.HexColor("#95D5B2"))


def generar_pdf_agricultor(resumen_vuelo: dict, ruta_pdf: str) -> str:
    # Idea 4 / API-05: reporte limpio de 1 sola pagina en lenguaje llano para el agricultor
    os.makedirs(os.path.dirname(os.path.abspath(ruta_pdf)), exist_ok=True)
    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    w, h = letter  # 612 x 792 pt

    # Banda superior verde bosque
    c.setFillColor(colors.HexColor("#16231B"))
    c.rect(0, h - 82, w, 82, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#FCFBF7"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(36, h - 38, "AgroDron · Resumen de Cultivo en Finca")
    finca_nom = (resumen_vuelo.get("finca") or {}).get("nombre", "Finca Piloto")
    vereda = (resumen_vuelo.get("finca") or {}).get("vereda", "Vereda La Cabaña")
    vuelo = resumen_vuelo["vuelo"]
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#B7E4C7"))
    c.drawString(36, h - 58, f"{finca_nom} · {vereda} · Vuelo del {vuelo['fecha']} · Altura {vuelo['altura_m']} m · 1,0 hectárea")

    # 3 grandes cifras (UI-01)
    res = resumen_vuelo["resumen"]
    y_kpi = h - 160
    tarjetas = [
        ("PLANTAS ESPERADAS", f"{res['esperadas']:,}".replace(",", "."), "Malla 50x50 sitios", "#18221B"),
        ("PLANTAS ESTIMADAS (IA)", f"{res['detectadas']:,}".replace(",", "."), f"Precisión vs campo: {100 - res['error_vs_gt_pct']:.1f} %", "#2D6A4F"),
        ("FALTANTES / DÉFICIT", f"{res['deficit']} ({res['deficit_pct']} %)", f"Semáforo: {res['semaforo']}", "#B84A27"),
    ]
    cw = (w - 92) / 3.0
    for idx, (lbl, val, sub, col_hex) in enumerate(tarjetas):
        x0 = 36 + idx * (cw + 10)
        c.setFillColor(colors.HexColor("#F7F4ED"))
        c.setStrokeColor(colors.HexColor("#D6D0C4"))
        c.roundRect(x0, y_kpi, cw, 62, 6, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#5C665E"))
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x0 + 10, y_kpi + 46, lbl)
        c.setFillColor(colors.HexColor(col_hex))
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x0 + 10, y_kpi + 24, val)
        c.setFillColor(colors.HexColor("#5C665E"))
        c.setFont("Helvetica", 8)
        c.drawString(x0 + 10, y_kpi + 9, sub)

    # Mapa de densidad 10x10 m a la izquierda
    c.setFillColor(colors.HexColor("#18221B"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(36, h - 190, "Mapa de Densidad del Cultivo (celdas 10 × 10 m)")
    gx0, gy0, gside = 36, h - 415, 210
    celda_pt = gside / 10.0
    for cell in resumen_vuelo.get("densidad_10x10", []):
        cx = gx0 + cell["ix"] * celda_pt
        cy = gy0 + cell["iy"] * celda_pt
        c.setFillColor(_color_celda_densidad(cell["nivel"]))
        c.setStrokeColor(colors.HexColor("#FCFBF7"))
        c.setLineWidth(0.6)
        c.rect(cx, cy, celda_pt, celda_pt, fill=1, stroke=1)

    # Ejes de cuadrantes sobre el mapa
    c.setStrokeColor(colors.HexColor("#16231B"))
    c.setLineWidth(1.6)
    c.line(gx0 + gside / 2, gy0, gx0 + gside / 2, gy0 + gside)
    c.line(gx0, gy0 + gside / 2, gx0 + gside, gy0 + gside / 2)
    c.setFillColor(colors.HexColor("#FCFBF7"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(gx0 + 8, gy0 + gside - 16, "Q1 (NO)")
    c.drawString(gx0 + gside / 2 + 8, gy0 + gside - 16, "Q2 (NE)")
    c.drawString(gx0 + 8, gy0 + 8, "Q4 (SO)")
    c.drawString(gx0 + gside / 2 + 8, gy0 + 8, "Q3 (SE)")

    # Leyenda de mapa
    leg_y = gy0 - 18
    for i, (etq, niv) in enumerate((("Óptimo", "OPTIMO"), ("Medio", "MEDIO"), ("Bajo", "BAJO"), ("Crítico", "CRITICO"))):
        lx = gx0 + i * 54
        c.setFillColor(_color_celda_densidad(niv))
        c.rect(lx, leg_y, 9, 9, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#18221B"))
        c.setFont("Helvetica", 7.5)
        c.drawString(lx + 12, leg_y + 1, etq)

    # Tabla por cuadrante a la derecha
    tx0 = 270
    c.setFillColor(colors.HexColor("#18221B"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(tx0, h - 190, "Detalle por Cuadrante (50 × 50 m)")

    headers = [("Cuadrante", 68), ("Esperadas", 58), ("Estimadas", 58), ("Faltan", 54), ("Estado", 62)]
    ty = h - 215
    c.setFillColor(colors.HexColor("#EDE8DC"))
    c.rect(tx0, ty - 4, 306, 18, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#18221B"))
    c.setFont("Helvetica-Bold", 8.5)
    cur_x = tx0 + 6
    for h_txt, col_w in headers:
        c.drawString(cur_x, ty + 1, h_txt)
        cur_x += col_w

    ty -= 24
    c.setFont("Helvetica", 9)
    peor_q = None
    for q in resumen_vuelo["cuadrantes"]:
        if peor_q is None or q["deficit"] > peor_q["deficit"]:
            peor_q = q
        cur_x = tx0 + 6
        vals = [
            f"{q['codigo']} ({q['orientacion']})",
            str(q["esperadas"]),
            str(q["detectadas"]),
            f"{q['deficit']} ({q['deficit_pct']}%)",
            q["semaforo"],
        ]
        for (h_txt, col_w), v in zip(headers, vals):
            c.setFillColor(colors.HexColor("#18221B"))
            c.drawString(cur_x, ty, v)
            cur_x += col_w
        c.setStrokeColor(colors.HexColor("#D6D0C4"))
        c.setLineWidth(0.5)
        c.line(tx0, ty - 6, tx0 + 306, ty - 6)
        ty -= 22

    # Frases claras por cuadrante
    ty -= 10
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(colors.HexColor("#18221B"))
    c.drawString(tx0, ty, "Lectura rápida por zona:")
    ty -= 16
    c.setFont("Helvetica", 8.5)
    for q in resumen_vuelo["cuadrantes"]:
        c.setFillColor(colors.HexColor("#334139"))
        c.drawString(tx0, ty, f"• {q['frase'][:68]}")
        if len(q["frase"]) > 68:
            ty -= 11
            c.drawString(tx0 + 8, ty, q["frase"][68:])
        ty -= 15

    # Recomendacion agricola inferior
    n_huecos = len(resumen_vuelo.get("huecos_resiembra", []))
    rec_y = 66
    c.setFillColor(colors.HexColor("#E3F0E9"))
    c.setStrokeColor(colors.HexColor("#2D6A4F"))
    c.roundRect(36, rec_y, w - 72, 68, 6, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#16231B"))
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(48, rec_y + 46, "Recomendación Práctica de Resiembra")
    c.setFont("Helvetica", 9.5)
    zona_txt = f"{peor_q['codigo']} ({peor_q['orientacion']}) con {peor_q['deficit']} plantas faltantes" if peor_q else "toda la parcela"
    c.drawString(48, rec_y + 28, f"• Priorice la resiembra en el cuadrante {zona_txt}.")
    c.drawString(48, rec_y + 13, f"• Se identificaron {n_huecos} puntos exactos sin planta; exporte el archivo GPX o CSV desde el panel para ubicarlos en campo.")

    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#5C665E"))
    c.drawString(36, 32, f"Generado por AgroDron · {datetime.now().strftime('%Y-%m-%d %H:%M')} · Documento de 1 página para productor")
    c.showPage()
    c.save()
    return ruta_pdf


def crear_y_guardar_reporte(session, corrida_id: int, carpeta_reportes: str = "output/reportes_pdf") -> Reporte:
    corrida = session.get(CorridaIA, corrida_id)
    if corrida is None:
        raise ValueError(f"No existe corrida_ia id={corrida_id}")
    vuelo = session.get(Vuelo, corrida.vuelo_id)
    resumen = obtener_ultimo_vuelo(session, vuelo.parcela_id, vuelo_id=vuelo.id)
    os.makedirs(carpeta_reportes, exist_ok=True)
    ruta_pdf = os.path.join(carpeta_reportes, f"reporte_vuelo_{vuelo.id}_corrida_{corrida.id}.pdf").replace("\\", "/")
    generar_pdf_agricultor(resumen, ruta_pdf)

    resumen_ligero = {
        "vuelo_id": vuelo.id,
        "corrida_id": corrida.id,
        "resumen": resumen["resumen"],
        "cuadrantes": resumen["cuadrantes"],
        "total_huecos": len(resumen["huecos_resiembra"]),
    }

    rep = session.query(Reporte).filter(Reporte.corrida_id == corrida.id).first()
    if rep is None:
        rep = Reporte(
            corrida_id=corrida.id,
            resumen_json=resumen_ligero,
            ruta_pdf=ruta_pdf,
            creado=datetime.now(timezone.utc),
        )
        session.add(rep)
    else:
        rep.resumen_json = resumen_ligero
        rep.ruta_pdf = ruta_pdf
        rep.creado = datetime.now(timezone.utc)
    session.commit()
    session.refresh(rep)
    return rep
