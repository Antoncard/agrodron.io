# Generacion y particion por foto completa del dataset etiquetado YOLO (IA-01 a IA-06)
import argparse
from datetime import datetime, timezone
import json
import os
import sys

import cv2
import numpy as np
import yaml

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.dominio.parcela import Parcela, asignar_cuadrante, posiciones_disparo
from src.dominio.plan_vuelo import calcular_gsd, huella
from src.dominio.qa_fotos import RESOLUCION
from src.ml.georef import terreno_a_pixel
from src.ml.tiling import generar_tiles
from src.sim.simulador import (
    LAT_CABANA,
    LON_CABANA,
    generar_malezas_parcela,
    generar_plantas_parcela,
    recortar_vista_dron,
    renderizar_lienzo_terreno,
)


def _seleccionar_fotos_por_cuadrante(parcela, disparos, por_cuadrante=3):
    por_q = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
    for d in disparos:
        lat, lon = parcela.a_geo(d["x"], d["y"])
        q = asignar_cuadrante(parcela, lat, lon)
        # Preferir fotos bien distribuidas dentro de cada cuadrante
        if q in por_q:
            por_q[q].append(d)

    seleccion = []
    # Particion estricta por foto (70% train = 8 fotos, 15% val = 2 fotos, 15% test = 2 fotos)
    for q in ("Q1", "Q2", "Q3", "Q4"):
        lista = por_q[q]
        idxs = np.linspace(2, max(2, len(lista) - 3), por_cuadrante, dtype=int)
        for i, idx in enumerate(idxs):
            d = dict(lista[int(idx)])
            d["cuadrante"] = q
            seleccion.append(d)

    # Asignar splits a nivel de foto completa (IA-04): nunca recortes de una foto en dos splits
    splits_por_q = {
        "Q1": ["train", "train", "val"],
        "Q2": ["train", "train", "test"],
        "Q3": ["train", "train", "val"],
        "Q4": ["train", "train", "test"],
    }
    conteo_q = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    for d in seleccion:
        q = d["cuadrante"]
        d["split"] = splits_por_q[q][conteo_q[q]]
        conteo_q[q] += 1
    return seleccion


def preparar_dataset(salida="dataset/v1", tiles_por_foto=32, semilla=42):
    rng = np.random.default_rng(semilla)
    parcela = Parcela(LAT_CABANA, LON_CABANA, 100.0, 100.0, 0.0)
    plantas = generar_plantas_parcela(parcela, semilla=semilla)
    malezas = generar_malezas_parcela(parcela, cantidad=220, semilla=99)
    lienzo = renderizar_lienzo_terreno(parcela, plantas, px_por_m=10, semilla=7, malezas=malezas)

    disparos = posiciones_disparo(parcela, 25.0)
    fotos_sel = _seleccionar_fotos_por_cuadrante(parcela, disparos, por_cuadrante=3)

    gsd = calcular_gsd(25.0)
    hw_m, hh_m = huella(25.0)
    escala_px_m = 100.0 / gsd  # ~106.67 px/m a 25m

    for split in ("train", "val", "test"):
        os.makedirs(os.path.join(salida, "images", split), exist_ok=True)
        os.makedirs(os.path.join(salida, "labels", split), exist_ok=True)

    resumen = {
        "total_fotos": len(fotos_sel),
        "fotos_por_split": {"train": [], "val": [], "test": []},
        "tiles_por_split": {"train": 0, "val": 0, "test": 0},
        "objetos_por_clase": {"planta": 0, "maleza": 0},
    }

    for idx_f, disp in enumerate(fotos_sel):
        split = disp["split"]
        foto_id = f"foto_{disp['n']:04d}_{disp['cuadrante']}"
        resumen["fotos_por_split"][split].append(foto_id)

        bgr = recortar_vista_dron(lienzo, parcela, disp["x"], disp["y"], hw_m, hh_m, borrosa=False)
        # Variacion realista de brillo/sombra y ruido de sensor por pasada
        brillo = float(rng.uniform(0.92, 1.08))
        ruido_sensor = rng.normal(0.0, 2.5, bgr.shape)
        bgr = np.clip(bgr.astype(np.float32) * brillo + ruido_sensor, 0, 255).astype(np.uint8)

        # Proyectar anotaciones ground-truth en pixeles de la foto 4000x3000
        cajas_foto = []
        for p in plantas:
            if not p.get("viva", True):
                continue
            px, py = terreno_a_pixel(p["x"], p["y"], disp["x"], disp["y"], gsd, RESOLUCION)
            r_px = p["radio_m"] * escala_px_m
            if -r_px <= px <= RESOLUCION[0] + r_px and -r_px <= py <= RESOLUCION[1] + r_px:
                cajas_foto.append((0, px, py, r_px * 2.1, r_px * 2.1))
        for m in malezas:
            px, py = terreno_a_pixel(m["x"], m["y"], disp["x"], disp["y"], gsd, RESOLUCION)
            r_px = m["radio_m"] * escala_px_m
            if -r_px <= px <= RESOLUCION[0] + r_px and -r_px <= py <= RESOLUCION[1] + r_px:
                cajas_foto.append((1, px, py, r_px * 2.2, r_px * 1.8))

        tiles = generar_tiles(bgr, tamano=640, solape=0.20)
        # Escoger tiles distribuidos en toda la foto asegurando >= 300 recortes (12 * 32 = 384)
        idxs_t = np.linspace(0, len(tiles) - 1, min(tiles_por_foto, len(tiles)), dtype=int)

        for t_idx in idxs_t:
            x0, y0, tile_bgr = tiles[int(t_idx)]
            lineas_lbl = []
            for cls_id, cx, cy, bw, bh in cajas_foto:
                tx, ty = cx - x0, cy - y0
                x1 = max(0.0, tx - bw / 2.0)
                y1 = max(0.0, ty - bh / 2.0)
                x2 = min(640.0, tx + bw / 2.0)
                y2 = min(640.0, ty + bh / 2.0)
                if x2 <= x1 or y2 <= y1:
                    continue
                vw, vh = (x2 - x1), (y2 - y1)
                area_vis = vw * vh
                # Consistente con filtro de visibilidad del detector (>=24px y >=900 px^2)
                if vw < 24.0 or vh < 24.0 or area_vis < 900.0:
                    continue
                nw, nh = vw / 640.0, vh / 640.0
                if nw < 0.015 or nh < 0.015:
                    continue
                ncx, ncy = ((x1 + x2) / 2.0) / 640.0, ((y1 + y2) / 2.0) / 640.0
                lineas_lbl.append(f"{cls_id} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}")
                if cls_id == 0:
                    resumen["objetos_por_clase"]["planta"] += 1
                else:
                    resumen["objetos_por_clase"]["maleza"] += 1

            nombre = f"{foto_id}_t{int(t_idx):02d}"
            ruta_img = os.path.join(salida, "images", split, f"{nombre}.jpg")
            ruta_lbl = os.path.join(salida, "labels", split, f"{nombre}.txt")
            cv2.imwrite(ruta_img, tile_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            with open(ruta_lbl, "w", encoding="utf-8") as fl:
                fl.write("\n".join(lineas_lbl) + ("\n" if lineas_lbl else ""))
            resumen["tiles_por_split"][split] += 1

    data_yaml = {
        "path": os.path.abspath(salida).replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "planta", 1: "maleza"},
    }
    with open(os.path.join(salida, "data.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(data_yaml, f, sort_keys=False, allow_unicode=True)

    metadata = {
        "dataset_version": "v1.0",
        "fecha_generacion": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "etiquetador": "Antonio Cardona (Analista de Datos / IA)",
        "herramienta": "Generador automatizado YOLO AgroDron (compatible CVAT / Label Studio)",
        "tamano_recorte_px": 640,
        "solape_tiling": 0.20,
        "regla_particion": "Por foto completa (cero solape de foto fuente entre splits, IA-04)",
        "resumen": resumen,
    }
    with open(os.path.join(salida, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return metadata


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Prepara dataset YOLO particionado por foto (IA-01 a IA-06)")
    ap.add_argument("--salida", default="dataset/v1")
    ap.add_argument("--tiles-por-foto", type=int, default=32)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()
    meta = preparar_dataset(args.salida, args.tiles_por_foto, args.semilla)
    print(json.dumps(meta["resumen"], ensure_ascii=False, indent=2))
