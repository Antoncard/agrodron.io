# Pruebas del script AgroDron (python -m unittest)
import csv
import io
import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock

import cv2
import numpy as np
from PIL import Image

import agrodron_sprint1_epica1_v3 as ad


def foto(ruta, nitida=True, gps=True, gps_vacio=False):
    rng = np.random.default_rng(1)
    img = rng.integers(0, 255, (3000, 4000), dtype=np.uint8)
    img[::10, :] = 255
    if not nitida:
        img = cv2.GaussianBlur(img, (51, 51), 0)
    exif = Image.Exif()
    if gps:
        # 5 grados 3' N, 75 grados 30' W (zona de Manizales)
        exif[ad.GPS_TAG] = {1: "N", 2: (5.0, 3.0, 0.0), 3: "W", 4: (75.0, 30.0, 0.0)}
    elif gps_vacio:
        exif[ad.GPS_TAG] = {1: "N"}   # bloque GPS sin coordenadas
    Image.fromarray(img).save(ruta, exif=exif)


def ejecutar(*argv):
    # Corre la CLI y devuelve (codigo, salida)
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        codigo = ad.main(list(argv))
    return codigo, out.getvalue() + err.getvalue()


class Calibracion(unittest.TestCase):
    def test_bitacora_cumple(self):
        fallos, adv = ad.validar_calibracion(18, ad.leer_obturacion("1/1000"), 0.68)
        self.assertEqual((fallos, adv), ([], []))

    def test_pocos_satelites_y_obturacion_lenta(self):
        fallos, _ = ad.validar_calibracion(12, ad.leer_obturacion("1/500"))
        self.assertEqual(len(fallos), 2)

    def test_cli_codigo_salida(self):
        self.assertEqual(ejecutar("calibracion", "--satelites", "18",
                                  "--obturacion", "1/1000")[0], 0)
        self.assertEqual(ejecutar("calibracion", "--satelites", "10",
                                  "--obturacion", "1/1000")[0], 1)


class PlanVuelo(unittest.TestCase):
    def test_30m_no_cumple(self):
        plan = ad.calcular_plan_vuelo(altura_m=30)
        self.assertEqual(plan["gsd_cm_px"], 1.125)
        self.assertFalse(plan["cumple_gsd"])
        self.assertEqual(plan["total_fotos"], 160)

    def test_25m_cumple(self):
        plan = ad.calcular_plan_vuelo(altura_m=25)
        self.assertEqual(plan["gsd_cm_px"], 0.938)
        self.assertTrue(plan["cumple_gsd"])
        self.assertEqual(plan["total_fotos"], 228)
        self.assertEqual(plan["intervalo_disparo_s"], 1.25)

    def test_altura_maxima(self):
        self.assertAlmostEqual(ad.altura_maxima(), 26.67, places=2)

    def test_altura_recomendada(self):
        self.assertEqual(ad.altura_recomendada(), 25.0)
        self.assertTrue(ad.calcular_plan_vuelo(altura_m=ad.altura_recomendada())["cumple_gsd"])

    def test_tiempo_y_baterias(self):
        plan = ad.calcular_plan_vuelo(altura_m=25)
        self.assertEqual(plan["distancia_m"], 1303.1)   # 12 lineas x 100 m + 11 traslados
        self.assertEqual(plan["tiempo_vuelo_min"], 4.8)
        self.assertEqual(plan["baterias"], 1)

    def test_parametros_invalidos(self):
        with self.assertRaises(ValueError):
            ad.calcular_plan_vuelo(altura_m=0)

    def test_cli_30m_avisa(self):
        codigo, salida = ejecutar("plan", "--altura", "30")
        self.assertEqual(codigo, 1)
        self.assertIn("ADVERTENCIA", salida)


class Conteo(unittest.TestCase):
    FILAS = [{"cuadrante": "Q1", "esperadas": 625, "conteo": 598},
             {"cuadrante": "Q2", "esperadas": 625, "conteo": 584},
             {"cuadrante": "Q3", "esperadas": 625, "conteo": 579},
             {"cuadrante": "Q4", "esperadas": 625, "conteo": 591}]

    def test_datos_del_entregable(self):
        r = ad.comparar_conteo(self.FILAS)
        self.assertEqual(r["conteo"], 2352)
        self.assertEqual(r["diferencia"], -148)
        self.assertEqual(r["porcentaje"], -5.92)
        self.assertEqual(r["detalle"][2]["porcentaje"], -7.36)

    def test_planilla_csv(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "conteo.csv")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("cuadrante,esperadas,conteo\n")
                for x in self.FILAS:
                    f.write(f"{x['cuadrante']},{x['esperadas']},{x['conteo']}\n")
            codigo, salida = ejecutar("conteo", ruta)
            self.assertEqual(codigo, 0)
            self.assertIn("2352", salida)

    def test_planilla_vacia(self):
        with self.assertRaises(ValueError):
            ad.comparar_conteo([])


class Auditoria(unittest.TestCase):
    def test_lote(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "ok.jpg"))
            foto(os.path.join(d, "borrosa.jpg"), nitida=False)
            foto(os.path.join(d, "sin_gps.jpg"), gps=False)
            with open(os.path.join(d, "corrupta.jpg"), "wb") as f:
                f.write(b"x" * 20000)
            r = ad.auditar_lote(d, os.path.join(d, "qa.csv"))
            motivos = dict(r["detalle"])
            self.assertEqual(r["aceptadas"], 1)
            self.assertIn("BORROSA", motivos["borrosa.jpg"])
            self.assertEqual(motivos["sin_gps.jpg"], "SIN_GPS")
            self.assertEqual(motivos["corrupta.jpg"], "CORRUPTA")
            self.assertGreater(r["nitidez_promedio_aceptadas"], ad.NITIDEZ_MINIMA)

    def test_gps_sin_coordenadas(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"), gps=False, gps_vacio=True)
            self.assertFalse(ad.tiene_gps(os.path.join(d, "a.jpg")))

    def test_ruta_con_tildes(self):
        with tempfile.TemporaryDirectory() as d:
            carpeta = os.path.join(d, "Vereda_La_Cabaña")
            os.mkdir(carpeta)
            foto(os.path.join(carpeta, "foto_ñ.jpg"))
            r = ad.auditar_lote(carpeta, os.path.join(d, "qa.csv"))
            self.assertEqual(r["aceptadas"], 1)

    def test_recursivo_por_cuadrante(self):
        with tempfile.TemporaryDirectory() as d:
            for q in ("Q1", "Q2"):
                os.mkdir(os.path.join(d, q))
                foto(os.path.join(d, q, "a.jpg"))
            foto(os.path.join(d, "Q2", "b.jpg"), nitida=False)
            r = ad.auditar_lote(d, os.path.join(d, "qa.csv"), recursivo=True)
            self.assertEqual(r["por_grupo"]["Q1"], {"aceptadas": 1, "descartadas": 0})
            self.assertEqual(r["por_grupo"]["Q2"], {"aceptadas": 1, "descartadas": 1})

    def test_carpeta_inexistente(self):
        self.assertIn("error", ad.auditar_lote("/no/existe", "x.csv"))

    def test_coordenadas_en_reporte(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            self.assertEqual(ad.leer_gps(os.path.join(d, "a.jpg")), (5.05, -75.5))
            reporte = os.path.join(d, "qa.csv")
            ad.auditar_lote(d, reporte)
            with open(reporte, encoding="utf-8") as f:
                fila = list(csv.DictReader(f))[0]
            self.assertEqual((fila["lat"], fila["lon"]), ("5.05", "-75.5"))


ORIGEN = (5.05, -75.5)


def malla_de_fotos(parcela, altura=25.0, solo_lineas=None):
    # Posiciones (lat, lon) de las fotos que tomaria el plan de vuelo
    plan = ad.calcular_plan_vuelo(parcela.ancho_m, parcela.largo_m, altura)
    puntos = ad.generar_ruta(parcela, altura)
    xs = sorted({round(parcela.a_local(p["lat"], p["lon"])[0], 3) for p in puntos})
    if solo_lineas:
        xs = xs[:solo_lineas]
    paso = plan["paso_frontal_m"]
    return [parcela.a_geo(x, j * paso) for x in xs
            for j in range(plan["fotos_por_linea"])]


class ParcelaGeo(unittest.TestCase):
    def test_ida_y_vuelta(self):
        for rumbo in (0, 45, 200):
            p = ad.Parcela(*ORIGEN, rumbo_deg=rumbo)
            x, y = p.a_local(*p.a_geo(30.0, 70.0))
            self.assertAlmostEqual(x, 30.0, places=3)
            self.assertAlmostEqual(y, 70.0, places=3)

    def test_origen_invalido(self):
        with self.assertRaises(ValueError):
            ad.Parcela(95.0, 0.0)

    def test_cuadrantes(self):
        p = ad.Parcela(*ORIGEN)
        casos = {(50, 95): "Q1", (95, 50): "Q2", (50, 5): "Q3", (5, 50): "Q4",
                 (150, 50): "FUERA"}
        for (x, y), esperado in casos.items():
            self.assertEqual(ad.asignar_cuadrante(p, *p.a_geo(x, y)), esperado)

    def test_cuadrantes_parcela_girada(self):
        # Lineas hacia el este: el extremo "largo" de la parcela queda al este
        p = ad.Parcela(*ORIGEN, rumbo_deg=90)
        self.assertEqual(ad.asignar_cuadrante(p, *p.a_geo(50, 95)), "Q2")


class Ruta(unittest.TestCase):
    def test_waypoints(self):
        p = ad.Parcela(*ORIGEN)
        puntos = ad.generar_ruta(p, 25.0)
        self.assertEqual(len(puntos), 24)          # 12 lineas x 2 extremos
        y = [round(p.a_local(w["lat"], w["lon"])[1], 2) for w in puntos[:4]]
        self.assertEqual(y, [0.0, 100.0, 100.0, 0.0])   # sentido alterno

    def test_kml_y_csv(self):
        with tempfile.TemporaryDirectory() as d:
            kml = os.path.join(d, "ruta.kml")
            codigo, _ = ejecutar("ruta", "--lat", "5.05", "--lon", "-75.5",
                                 "--rumbo", "45", "--salida", kml)
            self.assertEqual(codigo, 0)
            ns = {"k": "http://www.opengis.net/kml/2.2"}
            marcas = ET.parse(kml).getroot().findall(".//k:Placemark", ns)
            self.assertEqual(len(marcas), 24 + 2)  # waypoints + parcela + ruta
            with open(os.path.join(d, "ruta_waypoints.csv"), encoding="utf-8") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 24)

    def test_ruta_altura_alta_avisa(self):
        with tempfile.TemporaryDirectory() as d:
            codigo, salida = ejecutar("ruta", "--lat", "5.05", "--lon", "-75.5",
                                      "--altura", "30", "--salida", os.path.join(d, "r.kml"))
            self.assertEqual(codigo, 1)
            self.assertIn("ADVERTENCIA", salida)


class Cobertura(unittest.TestCase):
    def test_plan_completo_cubre_todo(self):
        p = ad.Parcela(*ORIGEN, rumbo_deg=30)
        self.assertEqual(ad.calcular_cobertura(p, malla_de_fotos(p)), 100.0)

    def test_faltan_lineas(self):
        p = ad.Parcela(*ORIGEN)
        self.assertLess(ad.calcular_cobertura(p, malla_de_fotos(p, solo_lineas=4)), 60.0)

    def test_desde_reporte_qa(self):
        p = ad.Parcela(*ORIGEN)
        with tempfile.TemporaryDirectory() as d:
            reporte = os.path.join(d, "qa.csv")
            with open(reporte, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["archivo", "dictamen", "lat", "lon"])
                for i, (lat, lon) in enumerate(malla_de_fotos(p)):
                    w.writerow([f"{i}.jpg", "ACEPTADA", lat, lon])
                w.writerow(["borrosa.jpg", "RECHAZADA", ORIGEN[0], ORIGEN[1]])
            r = ad.evaluar_cobertura(reporte, p)
            self.assertEqual(r["fotos_usadas"], 228)
            self.assertTrue(r["cumple_cobertura"])
            self.assertEqual(sum(r["por_cuadrante"].values()), 228)
            codigo, salida = ejecutar("cobertura", reporte, "--lat", "5.05", "--lon", "-75.5")
            self.assertEqual(codigo, 0)
            self.assertIn("CUMPLE", salida)


class ClienteFalso:
    def __init__(self, existentes=None, fallar=False, metadatos=None):
        self.existentes, self.fallar, self.subidas = existentes or {}, fallar, []
        self.metadatos = metadatos or {}
        self.multiparte, self.cuerpos = [], {}

    def head_object(self, Bucket, Key):
        if Key in self.metadatos:
            return {"ETag": '"otro-etag-1"', "Metadata": {"md5": self.metadatos[Key]}}
        if Key not in self.existentes:
            raise KeyError("404")
        return {"ETag": f'"{self.existentes[Key]}"'}

    def put_object(self, **kw):
        if self.fallar:
            raise ConnectionError("sin red")
        self.subidas.append(kw["Key"])
        if isinstance(kw["Body"], bytes):
            self.cuerpos[kw["Key"]] = kw["Body"]

    def upload_file(self, ruta, bucket, clave, ExtraArgs=None):
        self.multiparte.append(clave)
        self.subidas.append(clave)


class Carga(unittest.TestCase):
    def test_simulacion(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            res = ad.subir_lote(d, "finca1", "lote1", "2026-10-22")
            self.assertEqual(res[0]["estado"], "SIMULADO")
            self.assertEqual(res[0]["clave"], "raw/finca1/lote1/2026-10-22/a.jpg")

    def test_destino_invalido(self):
        with self.assertRaises(ValueError):
            ad.subir_lote(".", "finca/../x", "lote1", "2026-10-22")
        with self.assertRaises(ValueError):
            ad.subir_lote(".", "finca1", "lote1", "22/10/2026")

    def test_carpeta_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            ad.subir_lote("/no/existe", "finca1", "lote1", "2026-10-22")

    def test_solo_aceptadas(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "ok.jpg"))
            foto(os.path.join(d, "borrosa.jpg"), nitida=False)
            reporte = os.path.join(d, "qa.csv")
            ad.auditar_lote(d, reporte)
            res = ad.subir_lote(d, "finca1", "lote1", "2026-10-22",
                                solo=ad.leer_aceptadas(reporte))
            self.assertEqual([r["archivo"] for r in res], ["ok.jpg"])

    def test_real_con_cliente_falso(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            foto(os.path.join(d, "b.jpg"), nitida=False)
            md5_a = ad.md5_archivo(os.path.join(d, "a.jpg")).hex()
            cliente = ClienteFalso({"raw/f/l/2026-10-22/a.jpg": md5_a})
            res = ad.subir_lote(d, "f", "l", "2026-10-22", dry_run=False, cliente=cliente)
            self.assertEqual(ad.contar_estados(res), {"YA_EXISTE": 1, "SUBIDO": 1})
            self.assertEqual(cliente.subidas, ["raw/f/l/2026-10-22/b.jpg"])

    def test_error_no_detiene_lote(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            foto(os.path.join(d, "b.jpg"))
            res = ad.subir_lote(d, "f", "l", "2026-10-22", dry_run=False,
                                cliente=ClienteFalso(fallar=True))
            self.assertEqual(ad.contar_estados(res), {"ERROR": 2})
            self.assertIn("sin red", res[0]["error"])

    def test_multiparte(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            cliente = ClienteFalso()
            with mock.patch.object(ad, "UMBRAL_MULTIPARTE", 1):
                res = ad.subir_lote(d, "f", "l", "2026-10-22", dry_run=False, cliente=cliente)
            self.assertEqual(res[0]["estado"], "SUBIDO")
            self.assertTrue(res[0]["multiparte"])
            self.assertEqual(cliente.multiparte, ["raw/f/l/2026-10-22/a.jpg"])

    def test_ya_existe_por_metadatos(self):
        # En multiparte el ETag no es el MD5; se usa el MD5 guardado en Metadata
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            md5 = ad.md5_archivo(os.path.join(d, "a.jpg")).hex()
            cliente = ClienteFalso(metadatos={"raw/f/l/2026-10-22/a.jpg": md5})
            res = ad.subir_lote(d, "f", "l", "2026-10-22", dry_run=False, cliente=cliente)
            self.assertEqual(res[0]["estado"], "YA_EXISTE")

    def test_manifiesto(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            res = ad.subir_lote(d, "f", "l", "2026-10-22")
            m = ad.crear_manifiesto(res, "f", "l", "2026-10-22")
            self.assertEqual(m["totales"], {"SIMULADO": 1})
            self.assertEqual(m["archivos"][0]["clave"], "raw/f/l/2026-10-22/a.jpg")
            cliente = ClienteFalso()
            clave = ad.subir_manifiesto(cliente, m)
            self.assertEqual(clave, "raw/f/l/2026-10-22/manifiesto.json")
            self.assertEqual(json.loads(cliente.cuerpos[clave])["lote"], "l")

    def test_cli_manifiesto_local(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            salida = os.path.join(d, "m.json")
            codigo, _ = ejecutar("subir", d, "--finca", "f", "--lote", "l",
                                 "--fecha", "2026-10-22", "--manifiesto", salida)
            self.assertEqual(codigo, 0)
            with open(salida, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["totales"], {"SIMULADO": 1})


class SimulacionDemo(unittest.TestCase):
    def test_posiciones_disparo(self):
        p = ad.Parcela(*ORIGEN)
        disparos = ad.posiciones_disparo(p, 25.0)
        self.assertEqual(len(disparos), 228)
        self.assertEqual(disparos[0]["y"], 0.0)
        self.assertEqual(disparos[18]["y"], 100.0)

    def test_cli_demo_genera_fotos_y_panel(self):
        with tempfile.TemporaryDirectory() as d:
            codigo, salida = ejecutar("demo", "--carpeta", d, "--fotos", "6",
                                      "--descartadas", "1", "--no-abrir")
            self.assertEqual(codigo, 0)
            self.assertIn("Simulacion completada", salida)
            self.assertTrue(os.path.isfile(os.path.join(d, "panel_agrodron.html")))
            self.assertTrue(os.path.isfile(os.path.join(d, "ortomosaico.jpg")))
            self.assertTrue(os.path.isfile(os.path.join(d, "reporte_qa.csv")))
            self.assertTrue(os.path.isfile(os.path.join(d, "manifiesto.json")))


if __name__ == "__main__":
    unittest.main()
