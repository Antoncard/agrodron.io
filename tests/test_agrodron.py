# Suite de pruebas unitarias de AgroDron (python -m unittest discover -s tests -v)
from contextlib import redirect_stderr, redirect_stdout
import csv
import io
import json
import os
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from PIL import Image

from src import almacen as alm
from src import cli
from src.almacen import (
    contar_estados,
    copiar_imagen,
    copiar_lote,
    crear_manifiesto,
    guardar_manifiesto,
    md5_archivo,
)
from src.dominio.conteo_referencia import CONTEO_DOCUMENTO, comparar_conteo
from src.dominio.parcela import (
    CUADRANTES,
    Parcela,
    asignar_cuadrante,
    calcular_cobertura,
    cuadrante_local,
    evaluar_cobertura,
    generar_ruta,
    posiciones_disparo,
)
from src.dominio.plan_vuelo import (
    altura_maxima,
    altura_recomendada,
    calcular_gsd,
    calcular_plan_vuelo,
    leer_obturacion,
    validar_calibracion,
)
from src.dominio.qa_fotos import (
    GPS_TAG,
    NITIDEZ_MINIMA,
    TAMANO_MINIMO,
    auditar_lote,
    leer_aceptadas,
    leer_gps,
    tiene_gps,
)
from src.ml import (
    DetectorSimulado,
    ejecutar_conteo_simulado,
    evaluar_conteo_ia,
    fusionar_detecciones,
    pixel_a_gps,
    pixel_a_terreno,
    semaforo_error,
    terreno_a_pixel,
)
from src.sim.simulador import generar_plantas_parcela


def foto(ruta, nitida=True, gps=True, gps_vacio=False):
    rng = np.random.default_rng(1)
    img = rng.integers(0, 255, (3000, 4000), dtype=np.uint8)
    img[::10, :] = 255
    if not nitida:
        img = cv2.GaussianBlur(img, (51, 51), 0)
    exif = Image.Exif()
    if gps:
        exif[GPS_TAG] = {1: "N", 2: (5.0, 3.0, 0.0), 3: "W", 4: (75.0, 30.0, 0.0)}
    elif gps_vacio:
        exif[GPS_TAG] = {1: "N"}
    Image.fromarray(img).save(ruta, exif=exif)


def ejecutar(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        codigo = cli.main(list(argv))
    return codigo, out.getvalue() + err.getvalue()


class Calibracion(unittest.TestCase):
    def test_bitacora_cumple(self):
        fallos, adv = validar_calibracion(18, leer_obturacion("1/1000"), 0.68)
        self.assertEqual((fallos, adv), ([], []))

    def test_pocos_satelites_y_obturacion_lenta(self):
        fallos, _ = validar_calibracion(12, leer_obturacion("1/500"))
        self.assertEqual(len(fallos), 2)

    def test_cli_codigo_salida(self):
        self.assertEqual(ejecutar("calibracion", "--satelites", "18", "--obturacion", "1/1000")[0], 0)
        self.assertEqual(ejecutar("calibracion", "--satelites", "10", "--obturacion", "1/1000")[0], 1)


class PlanVuelo(unittest.TestCase):
    def test_30m_no_cumple(self):
        plan = calcular_plan_vuelo(altura_m=30)
        self.assertEqual(plan["gsd_cm_px"], 1.125)
        self.assertFalse(plan["cumple_gsd"])
        self.assertEqual(plan["total_fotos"], 160)

    def test_25m_cumple(self):
        plan = calcular_plan_vuelo(altura_m=25)
        self.assertEqual(plan["gsd_cm_px"], 0.938)
        self.assertTrue(plan["cumple_gsd"])
        self.assertEqual(plan["total_fotos"], 228)
        self.assertEqual(plan["intervalo_disparo_s"], 1.25)

    def test_altura_maxima(self):
        self.assertAlmostEqual(altura_maxima(), 26.67, places=2)

    def test_altura_recomendada(self):
        self.assertEqual(altura_recomendada(), 25.0)
        self.assertTrue(calcular_plan_vuelo(altura_m=altura_recomendada())["cumple_gsd"])

    def test_tiempo_y_baterias(self):
        plan = calcular_plan_vuelo(altura_m=25)
        self.assertEqual(plan["distancia_m"], 1303.1)
        self.assertEqual(plan["tiempo_vuelo_min"], 4.8)
        self.assertEqual(plan["baterias"], 1)

    def test_parametros_invalidos(self):
        with self.assertRaises(ValueError):
            calcular_plan_vuelo(altura_m=0)

    def test_cli_30m_avisa(self):
        codigo, salida = ejecutar("plan", "--altura", "30")
        self.assertEqual(codigo, 1)
        self.assertIn("ADVERTENCIA", salida)


class Conteo(unittest.TestCase):
    FILAS = CONTEO_DOCUMENTO

    def test_datos_del_entregable(self):
        r = comparar_conteo(self.FILAS)
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
            comparar_conteo([])


class Auditoria(unittest.TestCase):
    def test_lote(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "ok.jpg"))
            foto(os.path.join(d, "borrosa.jpg"), nitida=False)
            foto(os.path.join(d, "sin_gps.jpg"), gps=False)
            with open(os.path.join(d, "corrupta.jpg"), "wb") as f:
                f.write(b"x" * 20000)
            r = auditar_lote(d, os.path.join(d, "qa.csv"))
            motivos = dict(r["detalle"])
            self.assertEqual(r["aceptadas"], 1)
            self.assertIn("BORROSA", motivos["borrosa.jpg"])
            self.assertEqual(motivos["sin_gps.jpg"], "SIN_GPS")
            self.assertEqual(motivos["corrupta.jpg"], "CORRUPTA")
            self.assertGreater(r["nitidez_promedio_aceptadas"], NITIDEZ_MINIMA)

    def test_lote_con_archivo_corrupto_procesa_resto(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "foto1.jpg"))
            foto(os.path.join(d, "foto2.jpg"))
            with open(os.path.join(d, "corrupta.jpg"), "wb") as f:
                f.write(b"datos_invalidos" * 2000)
            rep = os.path.join(d, "qa.csv")
            r = auditar_lote(d, rep)
            self.assertEqual(r["extraidas"], 3)
            self.assertEqual(r["aceptadas"], 2)
            self.assertEqual(r["descartadas"], 1)
            self.assertEqual(leer_aceptadas(rep), {"foto1.jpg", "foto2.jpg"})

    def test_gps_sin_coordenadas(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"), gps=False, gps_vacio=True)
            self.assertFalse(tiene_gps(os.path.join(d, "a.jpg")))

    def test_ruta_con_tildes(self):
        with tempfile.TemporaryDirectory() as d:
            carpeta = os.path.join(d, "Vereda_La_Cabaña")
            os.mkdir(carpeta)
            foto(os.path.join(carpeta, "foto_ñ.jpg"))
            r = auditar_lote(carpeta, os.path.join(d, "qa.csv"))
            self.assertEqual(r["aceptadas"], 1)

    def test_recursivo_por_cuadrante(self):
        with tempfile.TemporaryDirectory() as d:
            for q in ("Q1", "Q2"):
                os.mkdir(os.path.join(d, q))
                foto(os.path.join(d, q, "a.jpg"))
            foto(os.path.join(d, "Q2", "b.jpg"), nitida=False)
            r = auditar_lote(d, os.path.join(d, "qa.csv"), recursivo=True)
            self.assertEqual(r["por_grupo"]["Q1"], {"aceptadas": 1, "descartadas": 0})
            self.assertEqual(r["por_grupo"]["Q2"], {"aceptadas": 1, "descartadas": 1})

    def test_carpeta_inexistente(self):
        self.assertIn("error", auditar_lote("/no/existe", "x.csv"))

    def test_coordenadas_en_reporte(self):
        with tempfile.TemporaryDirectory() as d:
            foto(os.path.join(d, "a.jpg"))
            self.assertEqual(leer_gps(os.path.join(d, "a.jpg")), (5.05, -75.5))
            reporte = os.path.join(d, "qa.csv")
            auditar_lote(d, reporte)
            with open(reporte, encoding="utf-8") as f:
                fila = list(csv.DictReader(f))[0]
            self.assertEqual((fila["lat"], fila["lon"]), ("5.05", "-75.5"))


ORIGEN = (5.05, -75.5)


def malla_de_fotos(parcela, altura=25.0, solo_lineas=None):
    plan = calcular_plan_vuelo(parcela.ancho_m, parcela.largo_m, altura)
    puntos = generar_ruta(parcela, altura)
    xs = sorted({round(parcela.a_local(p["lat"], p["lon"])[0], 3) for p in puntos})
    if solo_lineas:
        xs = xs[:solo_lineas]
    paso = plan["paso_frontal_m"]
    return [parcela.a_geo(x, j * paso) for x in xs for j in range(plan["fotos_por_linea"])]


class ParcelaGeo(unittest.TestCase):
    def test_ida_y_vuelta(self):
        for rumbo in (0, 45, 200):
            p = Parcela(*ORIGEN, rumbo_deg=rumbo)
            x, y = p.a_local(*p.a_geo(30.0, 70.0))
            self.assertAlmostEqual(x, 30.0, places=3)
            self.assertAlmostEqual(y, 70.0, places=3)

    def test_origen_invalido(self):
        with self.assertRaises(ValueError):
            Parcela(95.0, 0.0)

    def test_cuadrantes(self):
        # Cuatro cuadrantes reales de 50x50 m: Q1 NO, Q2 NE, Q3 SE, Q4 SO
        self.assertEqual(CUADRANTES, {"NO": "Q1", "NE": "Q2", "SE": "Q3", "SO": "Q4"})
        p = Parcela(*ORIGEN)
        casos = {
            (25, 75): "Q1",
            (75, 75): "Q2",
            (75, 25): "Q3",
            (25, 25): "Q4",
            (150, 50): "FUERA",
        }
        for (x, y), esperado in casos.items():
            self.assertEqual(asignar_cuadrante(p, *p.a_geo(x, y)), esperado)

    def test_cuadrantes_parcela_girada(self):
        # Con rumbo 90 grados (eje largo al este), (25, 75) queda al noreste -> Q2
        p = Parcela(*ORIGEN, rumbo_deg=90)
        self.assertEqual(asignar_cuadrante(p, *p.a_geo(25, 75)), "Q2")
        self.assertEqual(asignar_cuadrante(p, *p.a_geo(25, 25)), "Q1")
        self.assertEqual(asignar_cuadrante(p, *p.a_geo(75, 75)), "Q3")
        self.assertEqual(asignar_cuadrante(p, *p.a_geo(75, 25)), "Q4")

    def test_divisiones_sin_sesgo(self):
        # Los 4 semiejes sobre las divisiones se reparten 1 a cada cuadrante en molinete
        p = Parcela(*ORIGEN)
        en_division = [
            cuadrante_local(p, 50.0, 75.0),
            cuadrante_local(p, 75.0, 50.0),
            cuadrante_local(p, 50.0, 25.0),
            cuadrante_local(p, 25.0, 50.0),
        ]
        self.assertEqual(en_division, ["Q1", "Q2", "Q3", "Q4"])

    def test_ruido_gps_centro_y_division(self):
        # Con error GPS de ~1 m, en el centro del cuadrante no cambia; cerca de la division puede cambiar
        p = Parcela(*ORIGEN)
        centros = {(25.0, 75.0): "Q1", (75.0, 75.0): "Q2", (75.0, 25.0): "Q3", (25.0, 25.0): "Q4"}
        for (cx, cy), q_esp in centros.items():
            for dx, dy in ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0), (0.7, -0.7)):
                lat_r, lon_r = p.a_geo(cx + dx, cy + dy)
                self.assertEqual(asignar_cuadrante(p, lat_r, lon_r), q_esp)

        # Punto a 0,3 m de la division vertical x=50 m: un error de +1,0 m lo cruza de Q1 a Q2
        lat_antes, lon_antes = p.a_geo(49.7, 75.0)
        lat_despues, lon_despues = p.a_geo(49.7 + 1.0, 75.0)
        self.assertEqual(asignar_cuadrante(p, lat_antes, lon_antes), "Q1")
        self.assertEqual(asignar_cuadrante(p, lat_despues, lon_despues), "Q2")


class Ruta(unittest.TestCase):
    def test_waypoints(self):
        p = Parcela(*ORIGEN)
        puntos = generar_ruta(p, 25.0)
        self.assertEqual(len(puntos), 24)
        y = [round(p.a_local(w["lat"], w["lon"])[1], 2) for w in puntos[:4]]
        self.assertEqual(y, [0.0, 100.0, 100.0, 0.0])

    def test_kml_y_csv(self):
        with tempfile.TemporaryDirectory() as d:
            kml = os.path.join(d, "ruta.kml")
            codigo, _ = ejecutar("ruta", "--lat", "5.05", "--lon", "-75.5", "--rumbo", "45", "--salida", kml)
            self.assertEqual(codigo, 0)
            ns = {"k": "http://www.opengis.net/kml/2.2"}
            marcas = ET.parse(kml).getroot().findall(".//k:Placemark", ns)
            self.assertEqual(len(marcas), 24 + 2)
            with open(os.path.join(d, "ruta_waypoints.csv"), encoding="utf-8") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 24)

    def test_ruta_altura_alta_avisa(self):
        with tempfile.TemporaryDirectory() as d:
            codigo, salida = ejecutar("ruta", "--lat", "5.05", "--lon", "-75.5", "--altura", "30", "--salida", os.path.join(d, "r.kml"))
            self.assertEqual(codigo, 1)
            self.assertIn("ADVERTENCIA", salida)


class Cobertura(unittest.TestCase):
    def test_plan_completo_cubre_todo(self):
        p = Parcela(*ORIGEN, rumbo_deg=30)
        self.assertEqual(calcular_cobertura(p, malla_de_fotos(p)), 100.0)

    def test_faltan_lineas(self):
        p = Parcela(*ORIGEN)
        self.assertLess(calcular_cobertura(p, malla_de_fotos(p, solo_lineas=4)), 60.0)

    def test_desde_reporte_qa(self):
        p = Parcela(*ORIGEN)
        with tempfile.TemporaryDirectory() as d:
            reporte = os.path.join(d, "qa.csv")
            with open(reporte, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["archivo", "dictamen", "lat", "lon"])
                for i, (lat, lon) in enumerate(malla_de_fotos(p)):
                    w.writerow([f"{i}.jpg", "ACEPTADA", lat, lon])
                w.writerow(["borrosa.jpg", "RECHAZADA", ORIGEN[0], ORIGEN[1]])
            r = evaluar_cobertura(reporte, p)
            self.assertEqual(r["fotos_usadas"], 228)
            self.assertTrue(r["cumple_cobertura"])
            self.assertEqual(sum(r["por_cuadrante"].values()), 228)
            codigo, salida = ejecutar("cobertura", reporte, "--lat", "5.05", "--lon", "-75.5")
            self.assertEqual(codigo, 0)
            self.assertIn("CUMPLE", salida)


class AlmacenLocal(unittest.TestCase):
    def test_copia_correcta_con_md5(self):
        with tempfile.TemporaryDirectory() as d:
            origen = os.path.join(d, "origen")
            destino = os.path.join(d, "almacen")
            os.mkdir(origen)
            ruta_a = os.path.join(origen, "a.jpg")
            foto(ruta_a)
            md5_esp = md5_archivo(ruta_a).hex()

            res = copiar_lote(origen, destino, "finca1", "lote1", "2026-10-22")
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["archivo"], "a.jpg")
            self.assertEqual(res[0]["estado"], "COPIADO")
            self.assertEqual(res[0]["md5"], md5_esp)
            self.assertGreater(res[0]["bytes"], TAMANO_MINIMO)
            copia = os.path.join(destino, "raw", "finca1", "lote1", "2026-10-22", "a.jpg")
            self.assertTrue(os.path.isfile(copia))
            self.assertEqual(md5_archivo(copia).hex(), md5_esp)

    def test_segunda_corrida_da_ya_existe(self):
        with tempfile.TemporaryDirectory() as d:
            origen = os.path.join(d, "origen")
            destino = os.path.join(d, "almacen")
            os.mkdir(origen)
            foto(os.path.join(origen, "a.jpg"))

            res1 = copiar_lote(origen, destino, "finca1", "lote1", "2026-10-22")
            res2 = copiar_lote(origen, destino, "finca1", "lote1", "2026-10-22")
            self.assertEqual(res1[0]["estado"], "COPIADO")
            self.assertEqual(res2[0]["estado"], "YA_EXISTE")

    def test_error_lectura_no_detiene_lote(self):
        from src.almacen import local as loc
        with tempfile.TemporaryDirectory() as d:
            origen = os.path.join(d, "origen")
            destino = os.path.join(d, "almacen")
            os.mkdir(origen)
            foto(os.path.join(origen, "a.jpg"))
            foto(os.path.join(origen, "b.jpg"))

            md5_real = loc.md5_archivo

            def md5_con_fallo(ruta):
                if ruta.endswith("a.jpg"):
                    raise OSError("error de lectura en disco")
                return md5_real(ruta)

            with mock.patch.object(loc, "md5_archivo", side_effect=md5_con_fallo):
                res = copiar_lote(origen, destino, "f", "l", "2026-10-22")

            estados = {r["archivo"]: r["estado"] for r in res}
            self.assertEqual(estados, {"a.jpg": "ERROR", "b.jpg": "COPIADO"})

    def test_estados_no_existe_y_muy_pequena(self):
        with tempfile.TemporaryDirectory() as d:
            r_no = copiar_imagen(os.path.join(d, "no.jpg"), d, "f", "l", "2026-10-22")
            self.assertEqual(r_no["estado"], "NO_EXISTE")
            peq = os.path.join(d, "peq.jpg")
            with open(peq, "wb") as f:
                f.write(b"123")
            r_peq = copiar_imagen(peq, d, "f", "l", "2026-10-22")
            self.assertEqual(r_peq["estado"], "MUY_PEQUENA")

    def test_destino_invalido(self):
        with self.assertRaises(ValueError):
            copiar_lote(".", "almacen", "finca/../x", "lote1", "2026-10-22")
        with self.assertRaises(ValueError):
            copiar_lote(".", "almacen", "finca1", "lote1", "22/10/2026")

    def test_carpeta_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            copiar_lote("/no/existe", "almacen", "finca1", "lote1", "2026-10-22")

    def test_solo_aceptadas(self):
        with tempfile.TemporaryDirectory() as d:
            origen = os.path.join(d, "origen")
            destino = os.path.join(d, "almacen")
            os.mkdir(origen)
            foto(os.path.join(origen, "ok.jpg"))
            foto(os.path.join(origen, "borrosa.jpg"), nitida=False)
            reporte = os.path.join(d, "qa.csv")
            auditar_lote(origen, reporte)
            res = copiar_lote(origen, destino, "finca1", "lote1", "2026-10-22", solo=leer_aceptadas(reporte))
            self.assertEqual([r["archivo"] for r in res], ["ok.jpg"])

    def test_manifiesto_y_guardado(self):
        with tempfile.TemporaryDirectory() as d:
            origen = os.path.join(d, "origen")
            destino = os.path.join(d, "almacen")
            os.mkdir(origen)
            foto(os.path.join(origen, "a.jpg"))
            res = copiar_lote(origen, destino, "f", "l", "2026-10-22")
            m = crear_manifiesto(res, "f", "l", "2026-10-22")
            self.assertEqual(m["totales"], {"COPIADO": 1})
            self.assertEqual(m["ruta_lote"], "raw/f/l/2026-10-22/")
            ruta_m = os.path.join(d, "manifiesto.json")
            guardar_manifiesto(ruta_m, m)
            with open(ruta_m, encoding="utf-8") as f:
                leido = json.load(f)
            self.assertEqual(leido["lote"], "l")
            self.assertEqual(leido["archivos"][0]["archivo"], "a.jpg")

    def test_cli_guardar_y_alias_subir(self):
        with tempfile.TemporaryDirectory() as d:
            origen = os.path.join(d, "origen")
            destino = os.path.join(d, "almacen")
            os.mkdir(origen)
            foto(os.path.join(origen, "a.jpg"))
            salida = os.path.join(d, "m.json")
            codigo, _ = ejecutar("guardar", origen, "--destino", destino, "--finca", "f", "--lote", "l", "--fecha", "2026-10-22", "--manifiesto", salida)
            self.assertEqual(codigo, 0)
            with open(salida, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["totales"], {"COPIADO": 1})

            codigo2, texto2 = ejecutar("subir", origen, "--destino", destino, "--finca", "f", "--lote", "l", "--fecha", "2026-10-22")
            self.assertEqual(codigo2, 0)
            self.assertIn("desuso", texto2)

    def test_cli_flujo(self):
        with tempfile.TemporaryDirectory() as d:
            origen = os.path.join(d, "origen")
            destino = os.path.join(d, "almacen")
            os.mkdir(origen)
            foto(os.path.join(origen, "ok.jpg"))
            foto(os.path.join(origen, "borrosa.jpg"), nitida=False)
            rep = os.path.join(d, "qa.csv")
            man = os.path.join(d, "m.json")
            codigo, _ = ejecutar("flujo", origen, "--reporte", rep, "--destino", destino, "--finca", "f", "--lote", "l", "--fecha", "2026-10-22", "--manifiesto", man)
            self.assertEqual(codigo, 0)
            with open(man, encoding="utf-8") as f:
                datos = json.load(f)
            self.assertEqual(len(datos["archivos"]), 1)
            self.assertEqual(datos["archivos"][0]["archivo"], "ok.jpg")


class SimulacionDemo(unittest.TestCase):
    def test_posiciones_disparo(self):
        p = Parcela(*ORIGEN)
        disparos = posiciones_disparo(p, 25.0)
        self.assertEqual(len(disparos), 228)
        self.assertEqual(disparos[0]["y"], 0.0)
        self.assertEqual(disparos[18]["y"], 100.0)

    def test_cli_demo_genera_fotos_y_panel(self):
        with tempfile.TemporaryDirectory() as d:
            codigo, salida = ejecutar("demo", "--carpeta", d, "--fotos", "6", "--descartadas", "1", "--no-abrir")
            self.assertEqual(codigo, 0)
            self.assertIn("Simulacion completada", salida)
            self.assertIn("(muestra)", salida)
            ruta_html = os.path.join(d, "web", "panel_agrodron.html")
            self.assertTrue(os.path.isfile(ruta_html))
            self.assertTrue(os.path.isfile(os.path.join(d, "web", "ortomosaico.jpg")))
            self.assertTrue(os.path.isfile(os.path.join(d, "web", "assets", "ortomosaico.jpg")))
            self.assertTrue(os.path.isfile(os.path.join(d, "web", "vendor", "leaflet.js")))
            self.assertTrue(os.path.isfile(os.path.join(d, "reportes", "reporte_qa.csv")))
            self.assertTrue(os.path.isfile(os.path.join(d, "reportes", "manifiesto.json")))
            self.assertLess(os.path.getsize(ruta_html), 200 * 1024)

            with open(ruta_html, encoding="utf-8") as f:
                html = f.read()
            self.assertIn("0.938", html)
            self.assertIn("1.125", html)
            self.assertIn("228", html)
            self.assertIn("160", html)
            self.assertIn("Vuelo a 30 m · incumple", html)
            self.assertIn("Vuelo a 25 m · cumple", html)
            for q in ("Q1 (NO", "Q2 (NE", "Q3 (SE", "Q4 (SO"):
                self.assertIn(q, html)


class Epica3ConteoIA(unittest.TestCase):
    def test_georef_ida_y_vuelta(self):
        gsd = calcular_gsd(25.0)
        x, y = pixel_a_terreno(2000, 1500, 50.0, 50.0, gsd)
        self.assertEqual((x, y), (50.0, 50.0))
        px, py = terreno_a_pixel(55.0, 45.0, 50.0, 50.0, gsd)
        x2, y2 = pixel_a_terreno(px, py, 50.0, 50.0, gsd)
        self.assertAlmostEqual(x2, 55.0, places=4)
        self.assertAlmostEqual(y2, 45.0, places=4)
        lat, lon = pixel_a_gps(2000, 1500, 5.0949, -75.5891, gsd)
        self.assertEqual((lat, lon), (5.0949, -75.5891))

    def test_fusion_elimina_duplicados_en_solape(self):
        # Dos fotos solapadas ven la misma planta en (10,0, 10,0) con leve diferencia
        fotos = [
            {"x": 8.0, "y": 10.0, "puntos": [(10.0, 10.0, 0.95), (5.0, 10.0, 0.98)]},
            {"x": 12.0, "y": 10.0, "puntos": [(10.1, 10.0, 0.92), (14.0, 10.0, 0.97)]},
        ]
        fusionados = fusionar_detecciones(fotos, radio_m=0.6, margen_m=0.05)
        self.assertEqual(len(fusionados), 3)

    def test_detector_simulado_sin_ruido_error_menor_2pct(self):
        p = Parcela(5.0949, -75.5891, 100.0, 100.0, 0.0)
        plantas = generar_plantas_parcela(p)
        disparos = posiciones_disparo(p, 25.0)
        res = ejecutar_conteo_simulado(p, plantas, disparos, altura_m=25.0, ruido_px=0.0)
        self.assertEqual(res["ground_truth"], 2352)
        self.assertLess(res["error_pct"], 2.0)
        self.assertEqual(res["semaforo"], "VERDE")

    def test_semaforo_umbrales(self):
        self.assertEqual(semaforo_error(3.5), "VERDE")
        self.assertEqual(semaforo_error(5.0), "VERDE")
        self.assertEqual(semaforo_error(7.2), "AMARILLO")
        self.assertEqual(semaforo_error(12.1), "ROJO")

    def test_cli_contar(self):
        codigo, salida = ejecutar("contar")
        self.assertEqual(codigo, 0)
        for q in ("Q1", "Q2", "Q3", "Q4", "TOTAL", "VERDE"):
            self.assertIn(q, salida)


if __name__ == "__main__":
    unittest.main()
