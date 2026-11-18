# Tiling de fotos 4000x3000 con solape y NMS intra-foto (IA-12, IA-13)
import math


def _posiciones_eje(longitud: int, tamano: int, paso: int) -> list[int]:
    if longitud <= tamano:
        return [0]
    pos = list(range(0, longitud - tamano, paso))
    ultimo = longitud - tamano
    if not pos or pos[-1] != ultimo:
        pos.append(ultimo)
    return pos


def generar_tiles(imagen_bgr, tamano: int = 640, solape: float = 0.20):
    # Divide la imagen en recortes de tamano x tamano con solape; 4000x3000 -> 48 tiles (8x6)
    alto, ancho = imagen_bgr.shape[:2]
    paso = max(1, int(round(tamano * (1.0 - solape))))
    xs = _posiciones_eje(ancho, tamano, paso)
    ys = _posiciones_eje(alto, tamano, paso)
    tiles = []
    for y0 in ys:
        for x0 in xs:
            recorte = imagen_bgr[y0 : min(alto, y0 + tamano), x0 : min(ancho, x0 + tamano)]
            tiles.append((x0, y0, recorte))
    return tiles


def calcular_iou(box_a, box_b) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0.0 else 0.0


def nms_detecciones(detecciones, iou_umbral: float = 0.45, radio_px: float = 42.0):
    # Elimina duplicados entre recortes vecinos dentro de la misma foto
    if not detecciones:
        return []

    normalizadas = []
    for det in detecciones:
        if isinstance(det, dict):
            cx, cy = float(det["cx"]), float(det["cy"])
            conf = float(det["conf"])
            clase = det.get("clase", "planta")
            bbox = det.get("bbox")
            normalizadas.append({"cx": cx, "cy": cy, "conf": conf, "clase": clase, "bbox": bbox, "_raw": det})
        else:
            cx, cy, conf = float(det[0]), float(det[1]), float(det[2])
            clase = det[3] if len(det) > 3 else "planta"
            normalizadas.append({"cx": cx, "cy": cy, "conf": conf, "clase": clase, "bbox": None, "_raw": det})

    normalizadas.sort(key=lambda d: d["conf"], reverse=True)
    mantenidas = []
    for cand in normalizadas:
        duplicado = False
        for keep in mantenidas:
            if cand["clase"] != keep["clase"]:
                continue
            if cand["bbox"] is not None and keep["bbox"] is not None:
                if calcular_iou(cand["bbox"], keep["bbox"]) >= iou_umbral:
                    duplicado = True
                    break
            if math.hypot(cand["cx"] - keep["cx"], cand["cy"] - keep["cy"]) <= radio_px:
                duplicado = True
                break
        if not duplicado:
            mantenidas.append(cand)

    return [m["_raw"] for m in mantenidas]
