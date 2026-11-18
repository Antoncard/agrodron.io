# Detector real de vision computacional entrenable en CPU sobre pixeles BGR (Epica 3)
import hashlib
import json
import math
import os

import cv2
import numpy as np

from src.ml.detector import Detector
from src.ml.tiling import generar_tiles, nms_detecciones

CLASES_DEFAULT = ("planta", "maleza", "fondo")
# Pesos por defecto calibrados para ExG/morfologia cuando no hay archivo entrenado
PESOS_BASE = {
    "clases": list(CLASES_DEFAULT),
    "umbral_confianza": 0.50,
    "umbral_exg": 62,
    "media": [0.85, 0.78, 0.75, 0.85, 0.75, 0.85, 0.72, 0.88],
    "std": [0.15, 0.20, 0.25, 0.25, 0.12, 0.15, 0.15, 0.15],
    "W": [
        [2.5, -0.5, -2.0],
        [2.0, -0.4, -1.6],
        [2.8, -1.2, -1.6],
        [1.8, -0.2, -1.6],
        [1.0, -0.5, -0.5],
        [1.5, -1.2, -0.3],
        [0.9, -0.3, -0.6],
        [1.8, -0.4, -1.4],
    ],
    "b": [0.6, -0.1, -0.5],
}


def _softmax(logits: np.ndarray) -> np.ndarray:
    z = logits - np.max(logits, axis=1, keepdims=True)
    e = np.exp(z)
    return e / np.sum(e, axis=1, keepdims=True)


def extraer_candidatos_bgr(imagen_bgr: np.ndarray, umbral_exg: int = 62):
    # Segmenta parches vegetales sobre pixeles BGR sin usar metadatos del simulador
    alto_img, ancho_img = imagen_bgr.shape[:2]
    b = imagen_bgr[:, :, 0].astype(np.int16)
    g = imagen_bgr[:, :, 1].astype(np.int16)
    r = imagen_bgr[:, :, 2].astype(np.int16)
    exg = np.clip(2 * g - r - b, 0, 255).astype(np.uint8)
    mask = ((exg > umbral_exg) & ((g - b) > 25) & (g > 85)).astype(np.uint8) * 255

    k3 = np.ones((3, 3), np.uint8)
    k5 = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k5)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k3)

    num, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
    candidatos = []

    for idx in range(1, num):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < 220 or area > 35000:
            continue
        x = int(stats[idx, cv2.CC_STAT_LEFT])
        y = int(stats[idx, cv2.CC_STAT_TOP])
        w = int(stats[idx, cv2.CC_STAT_WIDTH])
        h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        if max(w, h) > 260:
            continue

        toca_borde = x <= 2 or y <= 2 or (x + w) >= (ancho_img - 2) or (y + h) >= (alto_img - 2)
        if toca_borde and (min(w, h) < 24 or area < 900):
            continue

        # Separacion Voronoi sobre picos de distancia cuando dos plantas se tocan
        if (w > 125 or h > 125 or area > 11500) and area <= 35000:
            sub_mask = (labels[y : y + h, x : x + w] == idx).astype(np.uint8)
            dist = cv2.distanceTransform(sub_mask, cv2.DIST_L2, 5)
            max_loc = cv2.dilate(dist, np.ones((45, 45), np.uint8))
            picos = (dist == max_loc) & (dist >= 18.0)
            n_nuc, _, _, cent_nuc = cv2.connectedComponentsWithStats(picos.astype(np.uint8))
            if n_nuc > 2:
                centros = [(float(cent_nuc[j][0]), float(cent_nuc[j][1])) for j in range(1, n_nuc)]
                ys_sub, xs_sub = np.where(sub_mask > 0)
                if ys_sub.size > 0:
                    dmat = np.stack(
                        [(xs_sub - px) ** 2 + (ys_sub - py) ** 2 for px, py in centros],
                        axis=1,
                    )
                    asign = np.argmin(dmat, axis=1)
                    for j_idx, (px, py) in enumerate(centros):
                        sel = asign == j_idx
                        n_pix = int(np.count_nonzero(sel))
                        if n_pix < 220:
                            continue
                        xs_c = xs_sub[sel] + x
                        ys_c = ys_sub[sel] + y
                        bx1, bx2 = int(xs_c.min()), int(xs_c.max()) + 1
                        by1, by2 = int(ys_c.min()), int(ys_c.max()) + 1
                        toca_sub = bx1 <= 2 or by1 <= 2 or bx2 >= (ancho_img - 2) or by2 >= (alto_img - 2)
                        if toca_sub and (min(bx2 - bx1, by2 - by1) < 24 or n_pix < 900):
                            continue
                        sub_reg = np.zeros((by2 - by1, bx2 - bx1), dtype=bool)
                        sub_reg[ys_c - by1, xs_c - bx1] = True
                        feat = _vector_caracteristicas(
                            imagen_bgr[by1:by2, bx1:bx2],
                            exg[by1:by2, bx1:bx2],
                            sub_reg,
                            float(n_pix),
                            bx2 - bx1,
                            by2 - by1,
                        )
                        candidatos.append({
                            "cx": float(xs_c.mean()),
                            "cy": float(ys_c.mean()),
                            "bbox": [float(bx1), float(by1), float(bx2), float(by2)],
                            "features": feat,
                        })
                    continue

        reg_mask = labels[y : y + h, x : x + w] == idx
        feat = _vector_caracteristicas(
            imagen_bgr[y : y + h, x : x + w],
            exg[y : y + h, x : x + w],
            reg_mask,
            float(area),
            w,
            h,
        )
        cx, cy = centroids[idx]
        candidatos.append({
            "cx": float(cx),
            "cy": float(cy),
            "bbox": [float(x), float(y), float(x + w), float(y + h)],
            "features": feat,
        })
    return candidatos


def _vector_caracteristicas(patch_bgr, patch_exg, reg_mask, area: float, w: int, h: int):
    pix_bgr = patch_bgr[reg_mask]
    pix_exg = patch_exg[reg_mask]
    if pix_bgr.size == 0:
        return [0.0] * 8

    patch_hsv = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2HSV)
    pix_hsv = patch_hsv[reg_mask]
    b_m, g_m, r_m = pix_bgr.mean(axis=0)
    exg_m = float(pix_exg.mean())
    exg_p90 = float(np.percentile(pix_exg, 90))
    sat_m = float(pix_hsv[:, 1].mean())
    solidez = area / max(1.0, float(w * h))
    aspecto = min(w, h) / max(1.0, float(max(w, h)))
    return [
        math.log1p(area) / 10.0,
        exg_m / 255.0,
        (float(g_m) - float(r_m)) / 128.0,
        (float(g_m) - float(b_m)) / 128.0,
        solidez,
        aspecto,
        sat_m / 255.0,
        exg_p90 / 255.0,
    ]


class DetectorVisionCV(Detector):
    """Detector entrenado sobre caracteristicas visuales ExG + morfologia."""

    def __init__(self, ruta_pesos: str | None = None, umbral_confianza: float | None = None):
        datos = PESOS_BASE
        self.ruta_pesos = ruta_pesos
        if ruta_pesos and os.path.isfile(ruta_pesos):
            with open(ruta_pesos, encoding="utf-8") as f:
                datos = json.load(f)
        self.clases = tuple(datos.get("clases", CLASES_DEFAULT))
        self.umbral_exg = int(datos.get("umbral_exg", 62))
        self.umbral_confianza = float(
            umbral_confianza if umbral_confianza is not None else datos.get("umbral_confianza", 0.50)
        )
        self.media = np.asarray(datos["media"], dtype=np.float64)
        self.std = np.asarray(datos["std"], dtype=np.float64)
        self.W = np.asarray(datos["W"], dtype=np.float64)
        self.b = np.asarray(datos["b"], dtype=np.float64)

    def _clasificar_candidatos(self, candidatos):
        if not candidatos:
            return []
        X = np.asarray([c["features"] for c in candidatos], dtype=np.float64)
        Xn = (X - self.media) / np.where(self.std < 1e-6, 1.0, self.std)
        probs = _softmax(Xn @ self.W + self.b)
        salidas = []
        for c, prob in zip(candidatos, probs):
            cls_idx = int(np.argmax(prob))
            clase = self.clases[cls_idx]
            conf = float(prob[cls_idx])
            salidas.append({
                "cx": round(c["cx"], 2),
                "cy": round(c["cy"], 2),
                "bbox": [round(v, 2) for v in c["bbox"]],
                "conf": round(conf, 4),
                "clase": clase,
                "prob_planta": round(float(prob[0]), 4),
            })
        return salidas

    def detectar_con_cajas(self, imagen_bgr: np.ndarray, incluir_malezas: bool = False):
        if not isinstance(imagen_bgr, np.ndarray) or imagen_bgr.ndim != 3:
            return []

        alto, ancho = imagen_bgr.shape[:2]
        if ancho > 800 or alto > 800:
            tiles = generar_tiles(imagen_bgr, tamano=640, solape=0.20)
            brutas = []
            for x0, y0, tile in tiles:
                cands = extraer_candidatos_bgr(tile, self.umbral_exg)
                for pred in self._clasificar_candidatos(cands):
                    bx1, by1, bx2, by2 = pred["bbox"]
                    toca_borde = (
                        (x0 > 0 and bx1 <= 2)
                        or (y0 > 0 and by1 <= 2)
                        or (x0 + 640 < ancho and bx2 >= tile.shape[1] - 2)
                        or (y0 + 640 < alto and by2 >= tile.shape[0] - 2)
                    )
                    if toca_borde and ((bx2 - bx1) < 42 or (by2 - by1) < 42):
                        continue
                    brutas.append({
                        "cx": round(pred["cx"] + x0, 2),
                        "cy": round(pred["cy"] + y0, 2),
                        "bbox": [round(bx1 + x0, 2), round(by1 + y0, 2), round(bx2 + x0, 2), round(by2 + y0, 2)],
                        "conf": pred["conf"],
                        "clase": pred["clase"],
                    })
            preds = nms_detecciones(brutas, iou_umbral=0.45, radio_px=45.0)
        else:
            cands = extraer_candidatos_bgr(imagen_bgr, self.umbral_exg)
            preds = self._clasificar_candidatos(cands)

        filtradas = []
        for p in preds:
            if p["clase"] == "fondo":
                continue
            if not incluir_malezas and p["clase"] != "planta":
                continue
            if p["conf"] >= self.umbral_confianza:
                filtradas.append(p)
        return filtradas

    def detectar(self, imagen):
        preds = self.detectar_con_cajas(imagen, incluir_malezas=False)
        return [(p["cx"], p["cy"], p["conf"]) for p in preds]


def entrenar_clasificador_cv(muestras_X: np.ndarray, muestras_y: np.ndarray, pasos: int = 900, lr: float = 0.25, semilla: int = 42):
    # Entrenamiento determinista de regresion logistica multinomial L2 balanceada en NumPy
    rng = np.random.default_rng(semilla)
    media = muestras_X.mean(axis=0)
    std = np.where(muestras_X.std(axis=0) < 1e-6, 1.0, muestras_X.std(axis=0))
    Xn = (muestras_X - media) / std

    n, d = Xn.shape
    k = 3
    W = rng.normal(0.0, 0.05, size=(d, k))
    b = np.zeros(k, dtype=np.float64)
    Y_oh = np.eye(k, dtype=np.float64)[muestras_y]

    # Balanceo inverso a la frecuencia de clase para no sesgar hacia clase mayoritaria
    conteos = np.bincount(muestras_y, minlength=k).astype(np.float64)
    pesos_clase = np.where(conteos > 0, n / (k * np.maximum(conteos, 1.0)), 1.0)
    pesos_muestra = pesos_clase[muestras_y][:, None]
    pesos_muestra /= np.mean(pesos_muestra)

    historial = []
    l2 = 1e-3
    for paso in range(1, pasos + 1):
        probs = _softmax(Xn @ W + b)
        loss = -float(np.mean(pesos_muestra * np.sum(Y_oh * np.log(np.clip(probs, 1e-9, 1.0)), axis=1))) + l2 * float(np.sum(W * W))
        grad = pesos_muestra * (probs - Y_oh) / n
        W -= lr * (Xn.T @ grad + 2.0 * l2 * W)
        b -= lr * np.sum(grad, axis=0)
        if paso % 100 == 0 or paso == 1:
            acc = float(np.mean(np.argmax(probs, axis=1) == muestras_y))
            historial.append({"epoca": paso, "loss": round(loss, 4), "accuracy_train": round(acc, 4)})

    return {
        "clases": list(CLASES_DEFAULT),
        "umbral_exg": 62,
        "umbral_confianza": 0.50,
        "media": [round(float(v), 6) for v in media],
        "std": [round(float(v), 6) for v in std],
        "W": [[round(float(val), 6) for val in fila] for fila in W],
        "b": [round(float(val), 6) for val in b],
    }, historial


def sha256_archivo(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()
