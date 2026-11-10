# Interfaz de deteccion de plantas e implementacion simulada para pruebas (Epica 3)
import numpy as np

from src.dominio.plan_vuelo import calcular_gsd, huella
from src.dominio.qa_fotos import RESOLUCION
from src.ml.georef import terreno_a_pixel


class Detector:
    # Interfaz base: detectar(imagen) -> lista de (x_px, y_px, confianza)
    def detectar(self, imagen):
        raise NotImplementedError("Subclases deben implementar detectar(imagen)")


class DetectorSimulado(Detector):
    # Detector simulado que proyecta plantas vivas dentro de la huella de cada foto
    def __init__(self, plantas=None, altura_m=25.0, ruido_px=0.0, semilla=42):
        self.plantas = plantas or []
        self.altura_m = altura_m
        self.gsd_cm_px = calcular_gsd(altura_m)
        self.huella_w, self.huella_h = huella(altura_m)
        self.ruido_px = float(ruido_px)
        self.rng = np.random.default_rng(semilla)

    def detectar(self, imagen):
        # Si recibe un dict de disparo {'x': ..., 'y': ...}, proyecta las plantas visibles
        if isinstance(imagen, dict) and "x" in imagen and "y" in imagen:
            return self._detectar_en_disparo(imagen["x"], imagen["y"])

        # Si recibe una matriz BGR, detecta coronas verdes por umbral cromático simple
        if isinstance(imagen, np.ndarray) and imagen.ndim == 3:
            import cv2
            alto, ancho = imagen.shape[:2]
            verde = (
                (imagen[:, :, 1].astype(np.int16) - imagen[:, :, 2].astype(np.int16) > 25)
                & (imagen[:, :, 1] > 90)
            ).astype(np.uint8) * 255
            num, _, stats, centroids = cv2.connectedComponentsWithStats(verde)
            detecciones = []
            for idx in range(1, num):
                area = stats[idx, cv2.CC_STAT_AREA]
                if 15 <= area <= 8000:
                    cx, cy = centroids[idx]
                    if 0 <= cx < ancho and 0 <= cy < alto:
                        detecciones.append((round(float(cx), 2), round(float(cy), 2), 0.95))
            return detecciones

        return []

    def _detectar_en_disparo(self, cx_m, cy_m):
        ancho_px, alto_px = RESOLUCION
        hw, hh = self.huella_w / 2.0, self.huella_h / 2.0
        resultados = []
        for p in self.plantas:
            if not p.get("viva", True):
                continue
            if abs(p["x"] - cx_m) <= hw and abs(p["y"] - cy_m) <= hh:
                px, py = terreno_a_pixel(
                    p["x"], p["y"], cx_m, cy_m, self.gsd_cm_px, RESOLUCION
                )
                if self.ruido_px > 0:
                    px += float(self.rng.normal(0.0, self.ruido_px))
                    py += float(self.rng.normal(0.0, self.ruido_px))
                if 0 <= px <= ancho_px and 0 <= py <= alto_px:
                    resultados.append((round(px, 2), round(py, 2), 0.98))
        return resultados

