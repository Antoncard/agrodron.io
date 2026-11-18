# Pruebas de base de datos, migraciones Alembic, importador y reportes (BD-01 a BD-09, BD-N1 a BD-N7)
import csv
import json
import os
import tempfile
import time
import unittest

from alembic import command as alembic_cmd
from alembic.config import Config

from scripts.backup_db import respaldar_sqlite, restaurar_y_verificar_sqlite
from src.db.models import ConteoCuadrante, CorridaIA, Cuadrante, GroundTruth, Imagen, Reporte, Vuelo
from src.db.session import create_session_factory
from src.dominio.conteo_referencia import CONTEO_DOCUMENTO
from src.dominio.parcela import Parcela
from src.servicios.importador import importar_ground_truth_csv, importar_lote_vuelo, registrar_vuelo
from src.servicios.reportes import (
    calcular_huecos_resiembra,
    calcular_mapa_densidad,
    exportar_huecos_csv,
    exportar_huecos_gpx,
    generar_pdf_agricultor,
    obtener_ultimo_vuelo,
)
from src.servicios.seed import sembrar_piloto


class BaseDatosYServicios(unittest.TestCase):
    def _migrar_temporal(self, carpeta: str):
        db_path = os.path.join(carpeta, "test.db").replace("\\", "/")
        url = f"sqlite:///{db_path}"
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", url)
        alembic_cmd.upgrade(cfg, "head")
        sf, engine = create_session_factory(url)
        return sf, engine, db_path

    def test_alembic_seed_consulta_rapida_y_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            sf, engine, db_path = self._migrar_temporal(d)
            try:
                with sf() as s:
                    res_seed = sembrar_piloto(
                        s,
                        modelos_dir="modelos",
                        reportes_dir=os.path.join(d, "pdfs"),
                        ejecutar_ia_real=False,
                    )
                    self.assertEqual(res_seed["total_detectadas"], 2352)
                    # Idempotencia del seed
                    res_seed2 = sembrar_piloto(
                        s,
                        modelos_dir="modelos",
                        reportes_dir=os.path.join(d, "pdfs"),
                        ejecutar_ia_real=False,
                    )
                    self.assertEqual(res_seed2["corrida_id"], res_seed["corrida_id"])

                    # BD-07: consulta de ultimo vuelo en < 200 ms
                    t0 = time.perf_counter()
                    ultimo = obtener_ultimo_vuelo(s, res_seed["parcela_id"])
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    self.assertLess(elapsed_ms, 200.0)
                    self.assertEqual(ultimo["resumen"]["esperadas"], 2500)
                    self.assertEqual(ultimo["resumen"]["detectadas"], 2352)
                    self.assertEqual(ultimo["resumen"]["deficit"], 148)

                    # BD-06: 625 - 598 = 27 en Q1
                    q1 = [q for q in ultimo["cuadrantes"] if q["codigo"] == "Q1"][0]
                    self.assertEqual(q1["deficit"], 27)
                    self.assertEqual(len(ultimo["densidad_10x10"]), 100)
                    self.assertEqual(len(ultimo["historico_vuelos"]), 2)
                    self.assertGreater(len(ultimo["huecos_resiembra"]), 100)

                    # Idea 1: CSV y GPX de huecos
                    csv_h = exportar_huecos_csv(ultimo["huecos_resiembra"])
                    self.assertIn("cuadrante,lat,lon", csv_h)
                    gpx_h = exportar_huecos_gpx(ultimo["huecos_resiembra"])
                    self.assertIn("<gpx", gpx_h)
                    self.assertIn("<wpt", gpx_h)

                    # Idea 4 / BD-08: PDF valido de 1 pagina
                    rep = s.query(Reporte).first()
                    self.assertIsNotNone(rep)
                    self.assertTrue(os.path.isfile(rep.ruta_pdf))
                    with open(rep.ruta_pdf, "rb") as fp:
                        self.assertTrue(fp.read(4) == b"%PDF")

                # BD-N6: Respaldo y verificacion de restauracion SQLite
                bkp = respaldar_sqlite(db_path, os.path.join(d, "bkp"))
                rest = restaurar_y_verificar_sqlite(bkp, os.path.join(d, "rest.db"))
                self.assertGreaterEqual(rest["tablas"], 11)
                self.assertEqual(rest["vuelos"], 2)
            finally:
                engine.dispose()

    def test_regla_bd01_vuelo_rechazado_e_importadores(self):
        with tempfile.TemporaryDirectory() as d:
            sf, engine, _ = self._migrar_temporal(d)
            try:
                with sf() as s:
                    res_seed = sembrar_piloto(
                        s,
                        modelos_dir="modelos",
                        reportes_dir=os.path.join(d, "pdfs"),
                        ejecutar_ia_real=False,
                    )
                    pid = res_seed["parcela_id"]

                    # BD-01: satelites < 16 -> RECHAZADO
                    v_malo = registrar_vuelo(s, pid, "2026-10-23", 25.0, satelites=12, obturacion="1/1000")
                    self.assertEqual(v_malo.estado, "RECHAZADO")
                    # BD-01: obturacion lenta -> RECHAZADO
                    v_lento = registrar_vuelo(s, pid, "2026-10-24", 25.0, satelites=18, obturacion="1/500")
                    self.assertEqual(v_lento.estado, "RECHAZADO")

                    # BD-03: corrida sin modelo_id debe fallar por integridad
                    c_invalida = CorridaIA(vuelo_id=v_malo.id, modelo_id=None, estado="EN_COLA")
                    s.add(c_invalida)
                    with self.assertRaises(Exception):
                        s.commit()
                    s.rollback()

                    # BD-05: importar ground_truth sin duplicar si se repite
                    csv_gt = os.path.join(d, "planilla.csv")
                    with open(csv_gt, "w", newline="", encoding="utf-8") as f:
                        w = csv.DictWriter(f, fieldnames=["cuadrante", "esperadas", "conteo"])
                        w.writeheader()
                        w.writerows(CONTEO_DOCUMENTO)
                    importar_ground_truth_csv(s, pid, csv_gt, fecha="2026-10-22")
                    importar_ground_truth_csv(s, pid, csv_gt, fecha="2026-10-22")
                    self.assertEqual(s.query(GroundTruth).count(), 4)

                    # BD-02 / BD-09: importar reporte_qa.csv + manifiesto.json en transaccion
                    v_ok = registrar_vuelo(s, pid, "2026-10-25", 25.0, satelites=18, obturacion="1/1000")
                    qa_csv = os.path.join(d, "qa.csv")
                    with open(qa_csv, "w", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        w.writerow(["archivo", "grupo", "resolucion", "nitidez", "gps", "lat", "lon", "dictamen", "motivo"])
                        w.writerow(["Q1/IMG_0001.jpg", "Q1", "4000x3000", "245.1", "True", "5.09557", "-75.58887", "ACEPTADA", ""])
                        w.writerow(["Q3/IMG_0002.jpg", "Q3", "4000x3000", "70.0", "True", "5.09512", "-75.58842", "RECHAZADA", "BORROSA"])
                    man_json = os.path.join(d, "manifiesto.json")
                    with open(man_json, "w", encoding="utf-8") as f:
                        json.dump({"ruta_lote": "raw/cabana/piloto/2026-10-25/", "archivos": [{"archivo": "Q1/IMG_0001.jpg", "md5": "abc123", "bytes": 2500000}]}, f)

                    n = importar_lote_vuelo(s, v_ok.id, qa_csv, man_json)
                    self.assertEqual(n, 2)
                    imgs = s.query(Imagen).filter(Imagen.vuelo_id == v_ok.id).order_by(Imagen.id.asc()).all()
                    self.assertEqual(len(imgs), 2)
                    self.assertEqual(imgs[0].md5, "abc123")
                    self.assertIsNotNone(imgs[0].cuadrante_id)
            finally:
                engine.dispose()

    def test_densidad_y_huecos_calculo(self):
        p = Parcela(5.0949, -75.5891, 100.0, 100.0, 0.0)
        pts = [(15.0, 15.0), (25.0, 75.0)]
        celdas = calcular_mapa_densidad(pts, p, plantas_esperadas=2500)
        self.assertEqual(len(celdas), 100)
        self.assertEqual(sum(c["plantas"] for c in celdas), 2)
        huecos = calcular_huecos_resiembra(pts, p)
        self.assertGreater(len(huecos), 2400)


if __name__ == "__main__":
    unittest.main()
