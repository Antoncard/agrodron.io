# Parcela georreferenciada, cuadrantes de 50x50 m, rutas KML/CSV y cobertura
import csv
from dataclasses import dataclass
import math

from src.dominio.plan_vuelo import CAMARA, huella

R_TIERRA = 6371000.0
# Cuatro cuadrantes reales de 50x50 m: Q1 noroeste, Q2 noreste, Q3 sureste, Q4 suroeste
CUADRANTES = {"NO": "Q1", "NE": "Q2", "SE": "Q3", "SO": "Q4"}


@dataclass(frozen=True)
class Parcela:
    # Rectangulo en terreno. (lat, lon) es el origen; largo sigue rumbo_deg
    lat: float
    lon: float
    ancho_m: float = 100.0
    largo_m: float = 100.0
    rumbo_deg: float = 0.0

    def __post_init__(self):
        if not (-90 <= self.lat <= 90 and -180 <= self.lon <= 180):
            raise ValueError("Coordenadas de origen fuera de rango")
        if min(self.ancho_m, self.largo_m) <= 0:
            raise ValueError("La parcela debe tener medidas positivas")

    def _giro(self):
        r = math.radians(self.rumbo_deg)
        return math.cos(r), math.sin(r)

    def a_geo(self, x, y):
        # Metros locales -> (lat, lon)
        return self.en_a_geo(*self.a_mundo(x, y))

    def a_mundo(self, x, y):
        # Metros locales -> (este, norte) en metros desde el origen
        c, s = self._giro()
        return x * c + y * s, -x * s + y * c

    def en_a_geo(self, este, norte):
        # (este, norte) en metros desde el origen -> (lat, lon)
        lat = self.lat + math.degrees(norte / R_TIERRA)
        lon = self.lon + math.degrees(este / (R_TIERRA * math.cos(math.radians(self.lat))))
        return lat, lon

    def a_local(self, lat, lon):
        # (lat, lon) -> metros locales (x a lo ancho, y a lo largo)
        c, s = self._giro()
        norte = math.radians(lat - self.lat) * R_TIERRA
        este = math.radians(lon - self.lon) * R_TIERRA * math.cos(math.radians(self.lat))
        return este * c - norte * s, este * s + norte * c

    def contiene(self, x, y):
        return 0 <= x <= self.ancho_m and 0 <= y <= self.largo_m


def cuadrante_local(parcela, x, y):
    # Cuatro cuadrantes reales (Q1 NO, Q2 NE, Q3 SE, Q4 SO) teniendo en cuenta rumbo_deg.
    # En las divisiones se asigna en molinete de forma determinista sin favorecer ninguno.
    if not parcela.contiene(x, y):
        return "FUERA"
    este, norte = parcela.a_mundo(x - parcela.ancho_m / 2, y - parcela.largo_m / 2)
    if abs(este) < 1e-6 and abs(norte) < 1e-6:
        return CUADRANTES["NO"]
    if abs(este) < 1e-6:
        return CUADRANTES["NO" if norte > 0 else "SE"]
    if abs(norte) < 1e-6:
        return CUADRANTES["NE" if este > 0 else "SO"]
    if norte > 0:
        return CUADRANTES["NO" if este < 0 else "NE"]
    return CUADRANTES["SO" if este < 0 else "SE"]


def asignar_cuadrante(parcela, lat, lon):
    # Cuadrante de una coordenada GPS; "FUERA" si cae fuera de la parcela
    return cuadrante_local(parcela, *parcela.a_local(lat, lon))


def lineas_x(parcela, altura_m=25.0, solape_lateral=0.75, cam=CAMARA):
    # Posicion x (m) de cada linea de vuelo, centradas en la parcela
    huella_ancho, _ = huella(altura_m, cam)
    paso = huella_ancho * (1 - solape_lateral)
    lineas = math.ceil(parcela.ancho_m / paso) + 1
    margen = (parcela.ancho_m - (lineas - 1) * paso) / 2
    return [margen + i * paso for i in range(lineas)], paso


def generar_ruta(parcela, altura_m=25.0, solape_lateral=0.75, cam=CAMARA):
    # Waypoints en cortacesped alternando el sentido de las lineas
    xs, paso = lineas_x(parcela, altura_m, solape_lateral, cam)
    puntos = []
    for i, x in enumerate(xs):
        extremos = (0.0, parcela.largo_m) if i % 2 == 0 else (parcela.largo_m, 0.0)
        for k, y in enumerate(extremos):
            lat, lon = parcela.a_geo(x, y)
            dist = i * (parcela.largo_m + paso) + k * parcela.largo_m
            puntos.append({
                "n": len(puntos) + 1,
                "linea": i + 1,
                "lat": round(lat, 7),
                "lon": round(lon, 7),
                "alt_m": altura_m,
                "dist_m": round(dist, 2),
            })
    return puntos


def posiciones_disparo(parcela, altura_m=25.0, solape_frontal=0.80, solape_lateral=0.75, cam=CAMARA):
    # Posiciones (x, y) donde dispara la camara a lo largo de las lineas
    xs, paso_lat = lineas_x(parcela, altura_m, solape_lateral, cam)
    _, huella_alto = huella(altura_m, cam)
    por_linea = math.ceil(parcela.largo_m / (huella_alto * (1 - solape_frontal))) + 1
    separacion = parcela.largo_m / (por_linea - 1)
    fotos = []
    for i, x in enumerate(xs):
        for j in range(por_linea):
            avance = j * separacion
            y = avance if i % 2 == 0 else parcela.largo_m - avance
            fotos.append({
                "n": len(fotos) + 1,
                "linea": i + 1,
                "x": x,
                "y": y,
                "dist_m": i * (parcela.largo_m + paso_lat) + avance,
            })
    return fotos


def escribir_kml(ruta_kml, puntos, parcela, velocidad_ms, intervalo_s):
    esquinas = [
        parcela.a_geo(x, y)
        for x, y in (
            (0, 0),
            (parcela.ancho_m, 0),
            (parcela.ancho_m, parcela.largo_m),
            (0, parcela.largo_m),
            (0, 0),
        )
    ]
    poligono = " ".join(f"{lon:.7f},{lat:.7f},0" for lat, lon in esquinas)
    linea = " ".join(f"{p['lon']},{p['lat']},{p['alt_m']}" for p in puntos)
    marcas = "\n".join(
        f"    <Placemark><name>WP{p['n']}</name><description>linea {p['linea']}</description>"
        f"<Point><altitudeMode>relativeToGround</altitudeMode>"
        f"<coordinates>{p['lon']},{p['lat']},{p['alt_m']}</coordinates></Point></Placemark>"
        for p in puntos
    )
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>AgroDron - ruta de vuelo</name>
    <description>Altura {puntos[0]['alt_m']} m AGL, velocidad {velocidad_ms} m/s, disparo cada {intervalo_s} s</description>
    <Placemark><name>Parcela</name>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>{poligono}</coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
    <Placemark><name>Ruta</name>
      <LineString><altitudeMode>relativeToGround</altitudeMode><coordinates>{linea}</coordinates></LineString>
    </Placemark>
{marcas}
  </Document>
</kml>
"""
    with open(ruta_kml, "w", encoding="utf-8") as f:
        f.write(kml)


def escribir_waypoints_csv(ruta_csv, puntos, velocidad_ms):
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["waypoint", "linea", "latitude", "longitude", "altitude_m", "speed_ms"])
        for p in puntos:
            w.writerow([p["n"], p["linea"], p["lat"], p["lon"], p["alt_m"], velocidad_ms])


def calcular_cobertura(parcela, puntos_latlon, altura_m=25.0, cam=CAMARA, celda_m=1.0):
    # Porcentaje de la parcela cubierto por las huellas de las fotos
    import numpy as np
    huella_ancho, huella_alto = huella(altura_m, cam)
    nx = max(1, math.ceil(parcela.ancho_m / celda_m))
    ny = max(1, math.ceil(parcela.largo_m / celda_m))
    cubierta = np.zeros((ny, nx), dtype=bool)
    for lat, lon in puntos_latlon:
        x, y = parcela.a_local(lat, lon)
        x0 = max(0, math.floor((x - huella_ancho / 2) / celda_m))
        x1 = min(nx, math.ceil((x + huella_ancho / 2) / celda_m))
        y0 = max(0, math.floor((y - huella_alto / 2) / celda_m))
        y1 = min(ny, math.ceil((y + huella_alto / 2) / celda_m))
        if x0 < x1 and y0 < y1:
            cubierta[y0:y1, x0:x1] = True
    return round(float(cubierta.mean()) * 100, 2)


def evaluar_cobertura(reporte_csv, parcela, altura_m=25.0):
    # Evalua cobertura usando las fotos ACEPTADAS con GPS de un reporte QA
    puntos, por_cuadrante, sin_gps = [], {q: 0 for q in CUADRANTES.values()}, 0
    por_cuadrante["FUERA"] = 0
    with open(reporte_csv, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["dictamen"] != "ACEPTADA":
                continue
            if not fila.get("lat") or not fila.get("lon"):
                sin_gps += 1
                continue
            lat, lon = float(fila["lat"]), float(fila["lon"])
            por_cuadrante[asignar_cuadrante(parcela, lat, lon)] += 1
            puntos.append((lat, lon))
    pct = calcular_cobertura(parcela, puntos, altura_m)
    return {
        "fotos_usadas": len(puntos),
        "sin_coordenadas": sin_gps,
        "por_cuadrante": por_cuadrante,
        "cobertura_pct": pct,
        "cumple_cobertura": pct >= 100.0,
    }

