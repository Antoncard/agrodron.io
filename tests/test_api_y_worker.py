# Pruebas de FastAPI (/api/v1), autenticacion x-api-key y worker de eventos (API-01 a API-06, 2.2.1-2.2.2)
import os
import tempfile
import unittest
from unittest import mock

from alembic import command as alembic_cmd
from alembic.config import Config
from fastapi.testclient import TestClient

from src.api.app import crear_app
from src.db.models import CorridaIA, ModeloIA
from src.db.session import create_session_factory
from src.servicios import asistente as srv_ia
from src.servicios.seed import sembrar_piloto
from src.worker.servicio import procesar_siguiente_corrida


class ApiYWorker(unittest.TestCase):
    def _setup_api(self, d: str, permitir_llm_externo: bool = False):
        db_url = f"sqlite:///{os.path.join(d, 'api_test.db')}".replace("\\", "/")
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", db_url)
        alembic_cmd.upgrade(cfg, "head")
        sf, engine = create_session_factory(db_url)
        with sf() as s:
            seed_info = sembrar_piloto(
                s,
                modelos_dir="modelos",
                reportes_dir=os.path.join(d, "pdfs"),
                ejecutar_ia_real=False,
            )
        app = crear_app(
            session_factory=sf,
            api_key="clave-prueba-segura",
            public_dir="public",
            permitir_llm_externo=permitir_llm_externo,
        )
        return TestClient(app), sf, engine, seed_info

    def test_endpoints_api_y_autenticacion(self):
        with tempfile.TemporaryDirectory() as d:
            client, sf, engine, info = self._setup_api(d)
            try:
                # Salud publica
                r_salud = client.get("/api/v1/salud")
                self.assertEqual(r_salud.status_code, 200)
                self.assertEqual(r_salud.json()["estado"], "ok")

                # API-06: sin x-api-key devuelve 401
                r_unauth = client.get(f"/api/v1/parcelas/{info['parcela_id']}/ultimo-vuelo")
                self.assertEqual(r_unauth.status_code, 401)
                r_bad = client.get(
                    f"/api/v1/parcelas/{info['parcela_id']}/ultimo-vuelo",
                    headers={"x-api-key": "incorrecta"},
                )
                self.assertEqual(r_bad.status_code, 401)

                hdr = {"x-api-key": "clave-prueba-segura"}
                # API-01: ultimo vuelo
                r_ult = client.get(f"/api/v1/parcelas/{info['parcela_id']}/ultimo-vuelo", headers=hdr)
                self.assertEqual(r_ult.status_code, 200)
                body = r_ult.json()
                self.assertEqual(body["resumen"]["esperadas"], 2500)
                self.assertEqual(len(body["cuadrantes"]), 4)
                self.assertEqual(len(body["densidad_10x10"]), 100)

                # API-02: conteo de vuelo
                r_cnt = client.get(f"/api/v1/vuelos/{info['vuelo_id']}/conteo", headers=hdr)
                self.assertEqual(r_cnt.status_code, 200)
                self.assertEqual(r_cnt.json()["resumen"]["detectadas"], 2352)

                # API-03: GeoJSON
                r_geo = client.get(f"/api/v1/vuelos/{info['vuelo_id']}/detecciones.geojson", headers=hdr)
                self.assertEqual(r_geo.status_code, 200)
                gj = r_geo.json()
                self.assertEqual(gj["type"], "FeatureCollection")
                self.assertEqual(len(gj["features"]), 2352)

                # API-05: PDF de 1 pagina
                rep_id = body["corrida"]["reporte_id"]
                r_pdf = client.get(f"/api/v1/reportes/{rep_id}.pdf", headers=hdr)
                self.assertEqual(r_pdf.status_code, 200)
                self.assertEqual(r_pdf.headers["content-type"], "application/pdf")
                self.assertTrue(r_pdf.content.startswith(b"%PDF"))

                # Idea 1: Huecos CSV y GPX
                r_csv = client.get(f"/api/v1/vuelos/{info['vuelo_id']}/huecos.csv", headers=hdr)
                self.assertEqual(r_csv.status_code, 200)
                self.assertIn("cuadrante,lat,lon", r_csv.text)
                r_gpx = client.get(f"/api/v1/vuelos/{info['vuelo_id']}/huecos.gpx", headers=hdr)
                self.assertEqual(r_gpx.status_code, 200)
                self.assertIn("<gpx", r_gpx.text)

                # API-04 + Worker (IA-26): encolar corrida y procesarla con worker
                r_proc = client.post(f"/api/v1/vuelos/{info['vuelo_id']}/procesar", headers=hdr)
                self.assertEqual(r_proc.status_code, 200)
                cid = r_proc.json()["corrida_id"]
                self.assertEqual(r_proc.json()["estado"], "EN_COLA")

                r_st = client.get(f"/api/v1/corridas/{cid}", headers=hdr)
                self.assertEqual(r_st.json()["estado"], "EN_COLA")

                with sf() as s:
                    res_w = procesar_siguiente_corrida(s, reportes_dir=os.path.join(d, "pdfs"))
                    self.assertIsNotNone(res_w)
                    self.assertEqual(res_w["estado"], "LISTA")

                r_st2 = client.get(f"/api/v1/corridas/{cid}", headers=hdr)
                self.assertEqual(r_st2.json()["estado"], "LISTA")

                # Asistente IA: 401 sin clave, 200 con clave usando datos reales de BD
                r_ia_unauth = client.post("/api/v1/asistente", json={"mensaje": "cuantas faltan"})
                self.assertEqual(r_ia_unauth.status_code, 401)
                r_ia = client.post(
                    "/api/v1/asistente",
                    headers=hdr,
                    json={"mensaje": "¿Dónde faltan más plantas?", "vista": "agro", "parcela_id": info["parcela_id"]},
                )
                self.assertEqual(r_ia.status_code, 200)
                ia_body = r_ia.json()
                self.assertEqual(ia_body["proveedor"], "local-offline")
                self.assertIn("Q3", ia_body["respuesta"])

                # Saludo natural + CORS para file:// (Origin: null)
                r_hola = client.post(
                    "/api/v1/asistente",
                    headers={**hdr, "Origin": "null"},
                    json={"mensaje": "hola", "vista": "agro", "parcela_id": info["parcela_id"]},
                )
                self.assertEqual(r_hola.status_code, 200)
                self.assertIn("Hola", r_hola.json()["respuesta"])
                self.assertEqual(r_hola.headers.get("access-control-allow-origin"), "*")
            finally:
                engine.dispose()

    def test_asistente_proveedores_openrouter_y_fallback_vertex(self):
        prompt = srv_ia.construir_system_prompt(None, vista="agro")
        self.assertIn("Vereda La Cabana", prompt)
        self.assertIn("2.352", prompt)

        fake_cfg = mock.MagicMock(
            vertex_api_key="fake-v",
            openrouter_api_key="fake-o",
            llm_model_vertex="gemini-2.5-flash",
            llm_model_openrouter="google/gemini-2.5-flash",
        )
        with mock.patch.object(srv_ia, "obtener_configuracion", return_value=fake_cfg):
            with mock.patch.object(srv_ia, "_llamar_vertex_express", return_value="Respuesta Vertex"):
                r1 = srv_ia.consultar_asistente("hola")
                self.assertEqual(r1["proveedor"], "vertex")
                self.assertEqual(r1["respuesta"], "Respuesta Vertex")

            with (
                mock.patch.object(srv_ia, "_llamar_vertex_express", side_effect=RuntimeError("timeout")),
                mock.patch.object(srv_ia, "_llamar_openrouter", return_value="Respuesta OpenRouter"),
            ):
                r2 = srv_ia.consultar_asistente("hola")
                self.assertEqual(r2["proveedor"], "openrouter")
                self.assertEqual(r2["respuesta"], "Respuesta OpenRouter")

            with (
                mock.patch.object(srv_ia, "_llamar_vertex_express", side_effect=RuntimeError("timeout")),
                mock.patch.object(srv_ia, "_llamar_openrouter", side_effect=RuntimeError("timeout")),
            ):
                r3 = srv_ia.consultar_asistente("hola")
                self.assertEqual(r3["proveedor"], "local-offline")

    def test_bd_n5_sin_credenciales_hardcodeadas_y_cli_bitacora_demo(self):
        # BD-N5: nunca almacenar credenciales de proveedores externos en el repositorio
        for ruta in ("src/db/config.py", "src/web/plantilla.py", "api/asistente.js", "public/index.html"):
            if os.path.isfile(ruta):
                with open(ruta, encoding="utf-8") as f:
                    contenido = f.read()
                self.assertNotIn("sk-or-v1-", contenido, f"Clave OpenRouter detectada en {ruta}")
                self.assertNotIn("AQ.Ab8RN6", contenido, f"Clave Vertex detectada en {ruta}")

        # Bitacora real configurable desde CLI demo (Sprint 3)
        from src import cli
        with tempfile.TemporaryDirectory() as d:
            rc = cli.main([
                "demo",
                "--carpeta", d,
                "--fotos", "4",
                "--descartadas", "1",
                "--fecha", "2026-11-24",
                "--satelites", "20",
                "--hdop", "0.55",
                "--obturacion", "1/1250",
                "--no-abrir",
            ])
            self.assertEqual(rc, 0)
            panel = os.path.join(d, "web", "panel_agrodron.html")
            with open(panel, encoding="utf-8") as f:
                html = f.read()
            self.assertIn('"fecha": "2026-11-24"', html)
            self.assertIn('"satelites": 20', html)
            self.assertIn('"hdop": 0.55', html)


if __name__ == "__main__":
    unittest.main()
