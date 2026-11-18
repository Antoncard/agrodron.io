# Pipeline completo de inferencia georreferenciada, BD y sensibilidad GPS (Epica 3)
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import time

import cv2
import numpy as np

from src.dominio.conteo_referencia import CONTEO_DOCUMENTO
from src.dominio.parcela import Parcela, cuadrante_local
from src.dominio.plan_vuelo import calcular_gsd
from src.dominio.qa_fotos import RESOLUCION
from src.ml.detector_yolo import cargar_detector
from src.ml.evaluacion import GROUND_TRUTH_CUADRANTES, evaluar_conteo_ia, semaforo_error
from src.ml.fusion import MARGEN_CENTRO_M, RADIO_FUSION_M, fusionar_detecciones
from src.ml.georef import pixel_a_gps, pixel_a_terreno


def leer_bgr(ruta: str):
    datos = np.fromfile(ruta, dtype=np.uint8)
    if datos.size == 0:
        return None
    return cv2.imdecode(datos, cv2.IMREAD_COLOR)


def evaluar_sensibilidad_gps(
    detecciones_por_foto,
    parcela: Parcela,
    ground_truth=None,
    ruidos_m=(0.5, 1.0, 2.0),
    semilla: int = 42,
):
    # Repite fusion y conteo perturbando la posicion GPS de cada foto (IA-23)
    rng = np.random.default_rng(semilla)
    resultados = []
    for sigma in ruidos_m:
        perturbadas = []
        for foto in detecciones_por_foto:
            dx = float(rng.normal(0.0, sigma))
            dy = float(rng.normal(0.0, sigma))
            pts = [
                (float(pt[0]) + dx, float(pt[1]) + dy, float(pt[2]) if len(pt) > 2 else 1.0)
                for pt in foto.get("puntos", ())
            ]
            perturbadas.append({"x": float(foto["x"]) + dx, "y": float(foto["y"]) + dy, "puntos": pts})
        fusionados = fusionar_detecciones(perturbadas, radio_m=RADIO_FUSION_M, margen_m=MARGEN_CENTRO_M)
        ev = evaluar_conteo_ia(fusionados, parcela, ground_truth=ground_truth)
        resultados.append({
            "ruido_gps_m": float(sigma),
            "detectadas": ev["detectadas"],
            "ground_truth": ev["ground_truth"],
            "error_pct": ev["error_pct"],
            "sesgo_pct": ev["sesgo_pct"],
            "semaforo": ev["semaforo"],
        })
    return resultados


def ejecutar_conteo_imagenes(
    parcela: Parcela,
    imagenes_meta,
    detector,
    carpeta_base: str | None = None,
    altura_m: float = 25.0,
    radio_fusion_m: float = RADIO_FUSION_M,
    ground_truth=None,
):
    t0 = time.perf_counter()
    gsd = calcular_gsd(altura_m)
    detecciones_por_foto = []
    errores = []
    procesadas = 0

    aceptadas = [it for it in imagenes_meta if it.get("dictamen", "ACEPTADA") == "ACEPTADA"]

    def _inferir_una(item):
        ruta = item.get("ruta") or (
            os.path.join(carpeta_base, item["archivo"]) if carpeta_base and item.get("archivo") else None
        )
        try:
            if not ruta or not os.path.isfile(ruta):
                raise FileNotFoundError(f"No existe imagen: {ruta}")
            bgr = leer_bgr(ruta)
            if bgr is None:
                raise ValueError(f"Imagen ilegible: {ruta}")
            alto_px, ancho_px = bgr.shape[:2]
            cx_m, cy_m = float(item["x"]), float(item["y"])
            dets_px = detector.detectar(bgr)
            pts_m = [
                (*pixel_a_terreno(px, py, cx_m, cy_m, gsd, (ancho_px, alto_px)), conf)
                for px, py, conf in dets_px
            ]
            return True, {
                "imagen_id": item.get("id"),
                "archivo": item.get("archivo"),
                "x": cx_m,
                "y": cy_m,
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "puntos": pts_m,
            }
        except Exception as exc:
            return False, {"archivo": item.get("archivo", "?"), "error": str(exc)}

    workers = min(8, os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        salidas = list(pool.map(_inferir_una, aceptadas))

    for ok, res_item in salidas:
        if ok:
            detecciones_por_foto.append(res_item)
            procesadas += 1
        else:
            errores.append(res_item)

    fusionados = fusionar_detecciones(detecciones_por_foto, radio_m=radio_fusion_m, margen_m=MARGEN_CENTRO_M)
    ev = evaluar_conteo_ia(fusionados, parcela, ground_truth=ground_truth)
    ev["puntos_fusionados"] = len(fusionados)
    ev["fotos_procesadas"] = procesadas
    ev["errores"] = errores
    ev["duracion_s"] = round(time.perf_counter() - t0, 3)
    ev["detecciones_terreno"] = fusionados
    ev["sensibilidad_gps"] = evaluar_sensibilidad_gps(detecciones_por_foto, parcela, ground_truth=ground_truth)
    return ev


def procesar_vuelo_en_bd(session, vuelo_id: int, corrida_id: int, detector=None):
    from src.db.models import (
        ConteoCuadrante,
        CorridaIA,
        Cuadrante,
        Deteccion,
        GroundTruth,
        Imagen,
        ModeloIA,
        ParcelaDB,
        Vuelo,
    )

    corrida = session.get(CorridaIA, corrida_id)
    if corrida is None:
        raise ValueError(f"No existe corrida_ia id={corrida_id}")

    vuelo = session.get(Vuelo, vuelo_id)
    if vuelo is None:
        raise ValueError(f"No existe vuelo id={vuelo_id}")

    parcela_db = session.get(ParcelaDB, vuelo.parcela_id)
    parcela = Parcela(
        parcela_db.lat_origen,
        parcela_db.lon_origen,
        parcela_db.ancho_m,
        parcela_db.largo_m,
        parcela_db.rumbo_deg,
    )

    corrida.estado = "PROCESANDO"
    corrida.inicio = datetime.now(timezone.utc)
    session.commit()

    if detector is None:
        modelo_db = session.get(ModeloIA, corrida.modelo_id)
        detector = cargar_detector(modelo_db.ruta_pesos, umbral_confianza=corrida.umbral_confianza)

    cuadrantes = {
        c.codigo: c
        for c in session.query(Cuadrante).filter(Cuadrante.parcela_id == parcela_db.id).all()
    }
    gt_map = dict(GROUND_TRUTH_CUADRANTES)
    for cod, q_obj in cuadrantes.items():
        gt_row = (
            session.query(GroundTruth)
            .filter(GroundTruth.cuadrante_id == q_obj.id)
            .order_by(GroundTruth.fecha.desc(), GroundTruth.id.desc())
            .first()
        )
        if gt_row is not None:
            gt_map[cod] = gt_row.contadas

    imagenes = (
        session.query(Imagen)
        .filter(Imagen.vuelo_id == vuelo.id, Imagen.dictamen == "ACEPTADA")
        .order_by(Imagen.id.asc())
        .all()
    )

    def _inferir_bd(img):
        try:
            if not img.ruta or not os.path.isfile(img.ruta):
                raise FileNotFoundError(f"Imagen no encontrada en disco: {img.ruta}")
            bgr = leer_bgr(img.ruta)
            if bgr is None:
                raise ValueError(f"No se pudo decodificar imagen: {img.ruta}")
            if img.lat is None or img.lon is None:
                raise ValueError(f"Imagen sin coordenadas GPS: {img.archivo}")
            cx_m, cy_m = parcela.a_local(img.lat, img.lon)
            alto_px, ancho_px = bgr.shape[:2]
            dets_px = detector.detectar(bgr)
            pts_m = [
                (*pixel_a_terreno(px, py, cx_m, cy_m, vuelo.gsd_cm_px, (ancho_px, alto_px)), conf)
                for px, py, conf in dets_px
            ]
            return True, {
                "imagen_id": img.id,
                "x": cx_m,
                "y": cy_m,
                "puntos": pts_m,
            }
        except Exception as exc:
            return False, {"imagen_id": img.id, "archivo": img.archivo, "error": str(exc)}

    detecciones_por_foto = []
    errores = []
    workers = min(8, os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for ok, item_res in pool.map(_inferir_bd, imagenes):
            if ok:
                detecciones_por_foto.append(item_res)
            else:
                errores.append(item_res)

    if not detecciones_por_foto and imagenes:
        corrida.estado = "ERROR"
        corrida.errores_json = errores
        corrida.fin = datetime.now(timezone.utc)
        session.commit()
        return {"corrida_id": corrida.id, "estado": "ERROR", "errores": errores}

    fusionados = fusionar_detecciones(
        detecciones_por_foto,
        radio_m=corrida.radio_fusion_m,
        margen_m=MARGEN_CENTRO_M,
    )

    session.query(Deteccion).filter(Deteccion.corrida_id == corrida.id).delete()
    session.query(ConteoCuadrante).filter(ConteoCuadrante.corrida_id == corrida.id).delete()

    conteos_q = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    nuevas_det = []
    for x_m, y_m, conf in fusionados:
        lat_d, lon_d = parcela.a_geo(x_m, y_m)
        cod_q = cuadrante_local(parcela, x_m, y_m)
        q_obj = cuadrantes.get(cod_q)
        if cod_q in conteos_q:
            conteos_q[cod_q] += 1
        nuevas_det.append(
            Deteccion(
                corrida_id=corrida.id,
                imagen_id=None,
                x_m=float(x_m),
                y_m=float(y_m),
                lat=round(float(lat_d), 7),
                lon=round(float(lon_d), 7),
                confianza=float(conf),
                clase="planta",
                cuadrante_id=q_obj.id if q_obj else None,
                fusionada=True,
            )
        )
    session.bulk_save_objects(nuevas_det)

    esp_map = {f["cuadrante"]: f["esperadas"] for f in CONTEO_DOCUMENTO}
    for cod, q_obj in cuadrantes.items():
        det_q = conteos_q.get(cod, 0)
        esp_q = q_obj.esperadas or esp_map.get(cod, 625)
        gt_q = gt_map.get(cod, esp_q)
        err_q = round(abs(det_q - gt_q) * 100.0 / gt_q, 2) if gt_q > 0 else 0.0
        session.add(
            ConteoCuadrante(
                corrida_id=corrida.id,
                cuadrante_id=q_obj.id,
                detectadas=det_q,
                esperadas=esp_q,
                deficit=esp_q - det_q,
                error_vs_gt_pct=err_q,
                semaforo=semaforo_error(err_q, nivel="cuadrante"),
            )
        )

    corrida.total_detectadas = sum(conteos_q.values())
    corrida.errores_json = errores
    corrida.estado = "LISTA"
    corrida.fin = datetime.now(timezone.utc)
    session.commit()
    return {
        "corrida_id": corrida.id,
        "estado": corrida.estado,
        "total_detectadas": corrida.total_detectadas,
        "errores": errores,
    }
