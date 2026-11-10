# Paquete de conteo de plantas con IA (Epica 3)
from src.ml.detector import Detector, DetectorSimulado
from src.ml.evaluacion import (
    GROUND_TRUTH_CUADRANTES,
    TOTAL_GROUND_TRUTH,
    ejecutar_conteo_simulado,
    evaluar_conteo_ia,
    semaforo_error,
)
from src.ml.fusion import MARGEN_CENTRO_M, RADIO_FUSION_M, fusionar_detecciones
from src.ml.georef import pixel_a_gps, pixel_a_terreno, terreno_a_pixel

