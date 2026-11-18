# Paquete de conteo de plantas con IA (Epica 3)
from src.ml.detector import Detector, DetectorSimulado
from src.ml.detector_cv import DetectorVisionCV, sha256_archivo
from src.ml.detector_yolo import DetectorYOLO, cargar_detector
from src.ml.evaluacion import (
    ESPERADAS_CUADRANTES,
    GROUND_TRUTH_CUADRANTES,
    TOTAL_GROUND_TRUTH,
    ejecutar_conteo_simulado,
    evaluar_conteo_ia,
    semaforo_error,
)
from src.ml.fusion import MARGEN_CENTRO_M, RADIO_FUSION_M, fusionar_detecciones
from src.ml.georef import pixel_a_gps, pixel_a_terreno, terreno_a_pixel
from src.ml.pipeline_vuelo import (
    ejecutar_conteo_imagenes,
    evaluar_sensibilidad_gps,
    leer_bgr,
    procesar_vuelo_en_bd,
)
from src.ml.tiling import calcular_iou, generar_tiles, nms_detecciones

__all__ = [
    "Detector",
    "DetectorSimulado",
    "DetectorVisionCV",
    "DetectorYOLO",
    "ESPERADAS_CUADRANTES",
    "GROUND_TRUTH_CUADRANTES",
    "MARGEN_CENTRO_M",
    "RADIO_FUSION_M",
    "TOTAL_GROUND_TRUTH",
    "calcular_iou",
    "cargar_detector",
    "ejecutar_conteo_imagenes",
    "ejecutar_conteo_simulado",
    "evaluar_conteo_ia",
    "evaluar_sensibilidad_gps",
    "fusionar_detecciones",
    "generar_tiles",
    "leer_bgr",
    "nms_detecciones",
    "pixel_a_gps",
    "pixel_a_terreno",
    "procesar_vuelo_en_bd",
    "semaforo_error",
    "sha256_archivo",
    "terreno_a_pixel",
]
