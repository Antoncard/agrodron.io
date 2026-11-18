# Wrapper Ultralytics YOLOv8n/s con tiling + NMS y fabrica de detectores (IA-08, IA-11, IA-18)
import os

from src.ml.detector import Detector
from src.ml.detector_cv import DetectorVisionCV, sha256_archivo
from src.ml.tiling import generar_tiles, nms_detecciones


class DetectorYOLO(Detector):
    """Detector de objetos YOLOv8 (PyTorch .pt / ONNX .onnx) con tiling 640x640."""

    def __init__(self, ruta_pesos: str, umbral_confianza: float = 0.25, clase_objetivo: int = 0):
        if not os.path.isfile(ruta_pesos):
            raise FileNotFoundError(f"No existen pesos YOLO en {ruta_pesos}")
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Para usar DetectorYOLO instala requirements-ml.txt (ultralytics)"
            ) from exc

        self.ruta_pesos = ruta_pesos
        self.umbral_confianza = float(umbral_confianza)
        self.clase_objetivo = int(clase_objetivo)
        self.modelo = YOLO(ruta_pesos)

    def detectar(self, imagen):
        alto, ancho = imagen.shape[:2]
        tiles = generar_tiles(imagen, tamano=640, solape=0.20) if (ancho > 800 or alto > 800) else [(0, 0, imagen)]
        detecciones = []
        for x0, y0, tile in tiles:
            res = self.modelo.predict(tile, conf=self.umbral_confianza, verbose=False)[0]
            if res.boxes is None:
                continue
            for box in res.boxes:
                cls_id = int(box.cls[0])
                if cls_id != self.clase_objetivo:
                    continue
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                conf = float(box.conf[0])
                detecciones.append({
                    "cx": round((x1 + x2) / 2.0 + x0, 2),
                    "cy": round((y1 + y2) / 2.0 + y0, 2),
                    "bbox": [x1 + x0, y1 + y0, x2 + x0, y2 + y0],
                    "conf": round(conf, 4),
                    "clase": "planta",
                })
        filtradas = nms_detecciones(detecciones, iou_umbral=0.45, radio_px=42.0)
        return [(d["cx"], d["cy"], d["conf"]) for d in filtradas]


def cargar_detector(ruta_pesos: str | None = None, umbral_confianza: float | None = None) -> Detector:
    if ruta_pesos and ruta_pesos.lower().endswith((".pt", ".onnx")):
        return DetectorYOLO(ruta_pesos, umbral_confianza=umbral_confianza or 0.25)
    return DetectorVisionCV(ruta_pesos=ruta_pesos, umbral_confianza=umbral_confianza)


__all__ = ["DetectorYOLO", "DetectorVisionCV", "cargar_detector", "sha256_archivo"]
