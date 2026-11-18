# Script de entrenamiento reproducible y evaluacion en prueba ciega (IA-06 a IA-11, IA-19)
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

from src.ml.detector_cv import (
    DetectorVisionCV,
    entrenar_clasificador_cv,
    extraer_candidatos_bgr,
    sha256_archivo,
)
from src.ml.tiling import calcular_iou


def _leer_cajas_yolo(ruta_txt: str, ancho: int = 640, alto: int = 640):
    cajas = []
    if not os.path.isfile(ruta_txt):
        return cajas
    with open(ruta_txt, encoding="utf-8") as f:
        for linea in f:
            partes = linea.strip().split()
            if len(partes) != 5:
                continue
            cls_id = int(partes[0])
            cx, cy, bw, bh = [float(v) for v in partes[1:]]
            x1 = (cx - bw / 2.0) * ancho
            y1 = (cy - bh / 2.0) * alto
            x2 = (cx + bw / 2.0) * ancho
            y2 = (cy + bh / 2.0) * alto
            cajas.append({"clase_id": cls_id, "bbox": [x1, y1, x2, y2]})
    return cajas


def _preparar_cache_split(dataset_dir: str, split: str, umbral_exg: int = 62):
    img_dir = os.path.join(dataset_dir, "images", split)
    lbl_dir = os.path.join(dataset_dir, "labels", split)
    cache = []
    for nombre in sorted(os.listdir(img_dir)):
        if not nombre.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        base = os.path.splitext(nombre)[0]
        img = cv2.imread(os.path.join(img_dir, nombre))
        gt_plantas = [c["bbox"] for c in _leer_cajas_yolo(os.path.join(lbl_dir, f"{base}.txt")) if c["clase_id"] == 0]
        cands = extraer_candidatos_bgr(img, umbral_exg=umbral_exg)
        cache.append((gt_plantas, cands))
    return cache


def _evaluar_cache_cv(detector: DetectorVisionCV, cache, iou_min: float = 0.50):
    tp, fp, fn = 0, 0, 0
    for gt_plantas, cands in cache:
        preds = [
            p
            for p in detector._clasificar_candidatos(cands)
            if p["clase"] == "planta" and p["conf"] >= detector.umbral_confianza
        ]
        preds.sort(key=lambda p: p["conf"], reverse=True)
        usados = set()
        for pred in preds:
            mejor_iou, mejor_idx = 0.0, -1
            for i, gt_box in enumerate(gt_plantas):
                if i in usados:
                    continue
                iou = calcular_iou(pred["bbox"], gt_box)
                if iou > mejor_iou:
                    mejor_iou, mejor_idx = iou, i
            if mejor_iou >= iou_min and mejor_idx >= 0:
                tp += 1
                usados.add(mejor_idx)
            else:
                fp += 1
        fn += len(gt_plantas) - len(usados)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "iou_umbral": iou_min,
    }


def _evaluar_split_cv(detector: DetectorVisionCV, dataset_dir: str, split: str, iou_min: float = 0.50):
    cache = _preparar_cache_split(dataset_dir, split, umbral_exg=detector.umbral_exg)
    return _evaluar_cache_cv(detector, cache, iou_min=iou_min)


def _entrenar_backend_cv(cfg: dict, dataset_dir: str, salida_modelo: str):
    train_img = os.path.join(dataset_dir, "images", "train")
    train_lbl = os.path.join(dataset_dir, "labels", "train")
    X_lista, y_lista = [], []

    for nombre in sorted(os.listdir(train_img)):
        if not nombre.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        base = os.path.splitext(nombre)[0]
        img = cv2.imread(os.path.join(train_img, nombre))
        gt_cajas = _leer_cajas_yolo(os.path.join(train_lbl, f"{base}.txt"))
        cands = extraer_candidatos_bgr(img, umbral_exg=62)
        for cand in cands:
            mejor_iou, mejor_cls = 0.0, 2  # 2 = fondo
            for gt in gt_cajas:
                iou = calcular_iou(cand["bbox"], gt["bbox"])
                if iou > mejor_iou:
                    mejor_iou, mejor_cls = iou, gt["clase_id"]
            if mejor_iou < 0.20:
                mejor_cls = 2
            X_lista.append(cand["features"])
            y_lista.append(mejor_cls)

    X = np.asarray(X_lista, dtype=np.float64)
    y = np.asarray(y_lista, dtype=np.int64)
    pesos_dict, curvas = entrenar_clasificador_cv(X, y, pasos=900, lr=0.25, semilla=int(cfg.get("seed", 42)))

    os.makedirs(salida_modelo, exist_ok=True)
    ruta_pesos = os.path.join(salida_modelo, "pesos.json")
    with open(ruta_pesos, "w", encoding="utf-8") as f:
        json.dump(pesos_dict, f, indent=2)

    # Calibrar umbral exclusivamente en validacion (IA-06) con cache en memoria
    cache_val = _preparar_cache_split(dataset_dir, "val", umbral_exg=62)
    mejor_umbral, mejor_val_f1, eval_val = 0.45, -1.0, {}
    for umb in (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65):
        det = DetectorVisionCV(ruta_pesos=ruta_pesos, umbral_confianza=umb)
        m_val = _evaluar_cache_cv(det, cache_val, iou_min=0.50)
        if m_val["f1"] > mejor_val_f1:
            mejor_val_f1, mejor_umbral, eval_val = m_val["f1"], umb, m_val

    pesos_dict["umbral_confianza"] = mejor_umbral
    with open(ruta_pesos, "w", encoding="utf-8") as f:
        json.dump(pesos_dict, f, indent=2)

    # Evaluacion ciega unica sobre test (IA-06, IA-19)
    det_final = DetectorVisionCV(ruta_pesos=ruta_pesos, umbral_confianza=mejor_umbral)
    eval_test = _evaluar_split_cv(det_final, dataset_dir, "test", iou_min=0.50)
    hash_pesos = sha256_archivo(ruta_pesos)

    metricas = {
        "version": cfg.get("version", "v1.0.0"),
        "dataset_version": cfg.get("dataset_version", "v1.0"),
        "arquitectura": "AgroDron-CV-ExG-Morphology-v1",
        "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hash_pesos,
        "ruta_pesos": ruta_pesos.replace("\\", "/"),
        "umbral_calibrado": mejor_umbral,
        "muestras_train": int(len(y)),
        "validacion": eval_val,
        "prueba_ciega": eval_test,
        "cumple_f1_minimo": eval_test["f1"] >= 0.85,
    }
    with open(os.path.join(salida_modelo, "metricas.json"), "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)
    with open(os.path.join(salida_modelo, "curvas.json"), "w", encoding="utf-8") as f:
        json.dump({"curvas": curvas}, f, indent=2)
    with open(os.path.join(salida_modelo, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"pesos": "pesos.json", "sha256": hash_pesos, "config": cfg}, f, ensure_ascii=False, indent=2)

    return metricas


def _entrenar_backend_yolo(cfg: dict, dataset_dir: str, salida_modelo: str):
    from ultralytics import YOLO  # type: ignore

    data_yaml = os.path.join(dataset_dir, "data.yaml")
    aug = cfg.get("augment", {})
    model = YOLO(cfg.get("model", "yolov8n.pt"))
    res = model.train(
        data=data_yaml,
        epochs=int(cfg.get("epochs", 50)),
        imgsz=int(cfg.get("imgsz", 640)),
        batch=int(cfg.get("batch", 16)),
        seed=int(cfg.get("seed", 42)),
        degrees=float(aug.get("degrees", 90.0)),
        flipud=float(aug.get("flipud", 0.5)),
        fliplr=float(aug.get("fliplr", 0.5)),
        hsv_v=float(aug.get("hsv_v", 0.2)),
        hsv_s=float(aug.get("hsv_s", 0.2)),
        scale=float(aug.get("scale", 0.0)),
        mosaic=float(aug.get("mosaic", 0.0)),
        project=salida_modelo,
        name="run",
        exist_ok=True,
    )
    ruta_best = os.path.join(salida_modelo, "run", "weights", "best.pt")
    hash_pesos = sha256_archivo(ruta_best)
    metricas = {
        "version": cfg.get("version", "v1.0.0"),
        "dataset_version": cfg.get("dataset_version", "v1.0"),
        "arquitectura": cfg.get("model", "yolov8n.pt"),
        "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256": hash_pesos,
        "ruta_pesos": ruta_best.replace("\\", "/"),
        "resultados_dict": {k: float(v) for k, v in getattr(res, "results_dict", {}).items()},
    }
    with open(os.path.join(salida_modelo, "metricas.json"), "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)
    return metricas


def entrenar(config_path: str, dataset_dir: str, version: str, backend: str = "cv", modelos_dir: str = "modelos"):
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["version"] = version
    salida_modelo = os.path.join(modelos_dir, version)
    if backend == "yolo":
        return _entrenar_backend_yolo(cfg, dataset_dir, salida_modelo)
    return _entrenar_backend_cv(cfg, dataset_dir, salida_modelo)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Entrenamiento reproducible de deteccion AgroDron")
    ap.add_argument("--config", default="ml_training/config_yolo.yaml")
    ap.add_argument("--dataset", default="dataset/v1")
    ap.add_argument("--version", default="v1.0.0")
    ap.add_argument("--backend", choices=("cv", "yolo"), default="cv")
    ap.add_argument("--modelos-dir", default="modelos")
    args = ap.parse_args()
    m = entrenar(args.config, args.dataset, args.version, args.backend, args.modelos_dir)
    print(json.dumps(m, ensure_ascii=False, indent=2))
