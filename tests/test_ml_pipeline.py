# Pruebas del pipeline real de IA: tiling, NMS, dataset sin fuga, DetectorVisionCV, sensibilidad GPS (IA-01 a IA-23)
import json
import os
import tempfile
import unittest

import numpy as np

from ml_training.entrenar import _evaluar_split_cv
from ml_training.preparar_dataset import preparar_dataset
from src.dominio.parcela import Parcela, posiciones_disparo
from src.ml.detector_cv import DetectorVisionCV, sha256_archivo
from src.ml.evaluacion import semaforo_error
from src.ml.pipeline_vuelo import evaluar_sensibilidad_gps
from src.ml.tiling import generar_tiles, nms_detecciones
from src.sim.simulador import generar_plantas_parcela


class MLPipeline(unittest.TestCase):
    def test_tiling_4000x3000_genera_48_recortes(self):
        img = np.zeros((3000, 4000, 3), dtype=np.uint8)
        tiles = generar_tiles(img, tamano=640, solape=0.20)
        self.assertEqual(len(tiles), 48)
        for _, _, t in tiles:
            self.assertEqual(t.shape, (640, 640, 3))

    def test_nms_elimina_duplicados_en_solape_de_tiles(self):
        dets = [
            {"cx": 100.0, "cy": 100.0, "bbox": [70, 70, 130, 130], "conf": 0.92, "clase": "planta"},
            {"cx": 104.0, "cy": 102.0, "bbox": [74, 72, 134, 132], "conf": 0.78, "clase": "planta"},
            {"cx": 300.0, "cy": 300.0, "bbox": [270, 270, 330, 330], "conf": 0.88, "clase": "planta"},
        ]
        res = nms_detecciones(dets, iou_umbral=0.45, radio_px=40.0)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["conf"], 0.92)

    def test_dataset_particionado_por_foto_sin_fuga(self):
        with tempfile.TemporaryDirectory() as d:
            meta = preparar_dataset(d, tiles_por_foto=26, semilla=42)
            self.assertGreaterEqual(sum(meta["resumen"]["tiles_por_split"].values()), 300)
            fotos = meta["resumen"]["fotos_por_split"]
            set_tr, set_va, set_te = set(fotos["train"]), set(fotos["val"]), set(fotos["test"])
            self.assertEqual(len(set_tr & set_va), 0)
            self.assertEqual(len(set_tr & set_te), 0)
            self.assertEqual(len(set_va & set_te), 0)
            self.assertTrue(os.path.isfile(os.path.join(d, "data.yaml")))

    def test_modelo_entrenado_v1_cumple_f1_y_sha256(self):
        ruta_pesos = os.path.join("modelos", "v1.0.0", "pesos.json")
        ruta_metricas = os.path.join("modelos", "v1.0.0", "metricas.json")
        self.assertTrue(os.path.isfile(ruta_pesos))
        self.assertTrue(os.path.isfile(ruta_metricas))
        with open(ruta_metricas, encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(m["sha256"], sha256_archivo(ruta_pesos))
        self.assertGreaterEqual(m["prueba_ciega"]["f1"], 0.85)
        self.assertTrue(m["cumple_f1_minimo"])

        det = DetectorVisionCV(ruta_pesos=ruta_pesos)
        self.assertEqual(det.umbral_confianza, m["umbral_calibrado"])
        if os.path.isdir("dataset/v1/images/test"):
            ev = _evaluar_split_cv(det, "dataset/v1", "test")
            self.assertGreaterEqual(ev["f1"], 0.85)

    def test_sensibilidad_gps_y_semaforo_cuadrante(self):
        self.assertEqual(semaforo_error(4.0, nivel="total"), "VERDE")
        self.assertEqual(semaforo_error(8.0, nivel="total"), "AMARILLO")
        self.assertEqual(semaforo_error(8.0, nivel="cuadrante"), "VERDE")
        self.assertEqual(semaforo_error(12.0, nivel="cuadrante"), "AMARILLO")
        self.assertEqual(semaforo_error(16.0, nivel="cuadrante"), "ROJO")

        p = Parcela(5.0949, -75.5891, 100.0, 100.0, 0.0)
        plantas = [x for x in generar_plantas_parcela(p) if x["viva"]]
        disparos = posiciones_disparo(p, 25.0)
        det_fotos = [
            {
                "x": d["x"],
                "y": d["y"],
                "puntos": [
                    (pl["x"], pl["y"], 0.95)
                    for pl in plantas
                    if abs(pl["x"] - d["x"]) <= 18.75 and abs(pl["y"] - d["y"]) <= 14.06
                ],
            }
            for d in disparos
        ]
        sens = evaluar_sensibilidad_gps(det_fotos, p, ruidos_m=(0.5, 1.0, 2.0))
        self.assertEqual([s["ruido_gps_m"] for s in sens], [0.5, 1.0, 2.0])
        self.assertTrue(all("error_pct" in s for s in sens))


if __name__ == "__main__":
    unittest.main()
