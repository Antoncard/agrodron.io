# AgroDron - Sprint 1 / Epica 1 (v3)
# Calibracion (1.1.1), plan de vuelo y ruta KML (1.1.2), conteo de referencia (1.2.1),
# auditoria de fotos, cuadrantes y cobertura por GPS (1.2.2) y carga a S3 (Epica 2).
import argparse
import base64
import csv
import hashlib
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

# Requisitos del proyecto
GSD_MAX_CM_PX = 1.0
NITIDEZ_MINIMA = 120.0
RESOLUCION = (4000, 3000)      # ancho, alto en px
TAMANO_MINIMO = 10 * 1024      # bytes
UMBRAL_MULTIPARTE = 16 * 1024 * 1024   # desde este tamano se sube por partes
GPS_TAG = 0x8825               # bloque GPS en EXIF
GPS_LATITUD, GPS_LONGITUD = 2, 4   # etiquetas dentro del bloque GPS

# Requisitos de calibracion (CA1)
SATELITES_MINIMOS = 16
OBTURACION_MAXIMA_S = 1 / 1000
HDOP_MAXIMO = 1.0              # recomendado; por encima se advierte

EXTENSIONES = (".jpg", ".jpeg")

# Configuracion de AWS (se puede cambiar con variables de entorno)
BUCKET = os.environ.get("AGRODRON_BUCKET", "agrodron-manizales-prod-us-east-2")
REGION = os.environ.get("AGRODRON_REGION", "us-east-2")


# ---------- Calibracion (1.1.1) ----------

def leer_obturacion(texto):
    # Acepta "1/1000", "0.001" o "0,001" y devuelve segundos
    texto = str(texto).strip().replace(",", ".")
    if "/" in texto:
        num, den = texto.split("/", 1)
        return float(num) / float(den)
    return float(texto)


def validar_calibracion(satelites, obturacion_s, hdop=None):
    # Devuelve (fallos, advertencias). Sin fallos = cumple CA1.
    fallos, advertencias = [], []
    if satelites < SATELITES_MINIMOS:
        fallos.append(f"SATELITES: {satelites} < {SATELITES_MINIMOS}")
    if obturacion_s > OBTURACION_MAXIMA_S:
        fallos.append(f"OBTURACION: 1/{round(1 / obturacion_s)} s es mas lenta que 1/1000 s")
    if hdop is not None and hdop > HDOP_MAXIMO:
        advertencias.append(f"HDOP: {hdop} > {HDOP_MAXIMO} (precision GPS baja)")
    return fallos, advertencias


# ---------- Plan de vuelo (1.1.2) ----------

@dataclass(frozen=True)
class Camara:
    sensor_ancho_mm: float = 13.2
    focal_mm: float = 8.8
    ancho_px: int = 4000
    alto_px: int = 3000


CAMARA = Camara()


def calcular_gsd(altura_m, cam=CAMARA):
    # GSD en cm por pixel
    return cam.sensor_ancho_mm * altura_m * 100 / (cam.focal_mm * cam.ancho_px)


def altura_maxima(gsd_max=GSD_MAX_CM_PX, cam=CAMARA):
    # Altura mas alta que todavia cumple el GSD (en el limite exacto GSD == max)
    return gsd_max * cam.focal_mm * cam.ancho_px / (cam.sensor_ancho_mm * 100)


def altura_recomendada(gsd_max=GSD_MAX_CM_PX, cam=CAMARA, margen=0.05):
    # Altura maxima con un margen de seguridad, redondeada hacia abajo a 0,5 m
    return math.floor(altura_maxima(gsd_max, cam) * (1 - margen) * 2) / 2


def huella(altura_m, cam=CAMARA):
    # Tamano en terreno (m) de una foto: (a lo ancho de la linea, a lo largo de la linea)
    gsd = calcular_gsd(altura_m, cam)
    return cam.ancho_px * gsd / 100, cam.alto_px * gsd / 100


def calcular_plan_vuelo(ancho_m=100.0, largo_m=100.0, altura_m=25.0,
                        solape_frontal=0.80, solape_lateral=0.75,
                        velocidad_ms=4.5, cam=CAMARA, autonomia_min=15.0):
    if min(ancho_m, largo_m, altura_m, velocidad_ms, autonomia_min) <= 0:
        raise ValueError("Medidas, velocidad y autonomia deben ser positivas")
    if not (0 <= solape_frontal < 1 and 0 <= solape_lateral < 1):
        raise ValueError("Los solapes deben estar entre 0 y 1")

    gsd = calcular_gsd(altura_m, cam)
    huella_ancho, huella_alto = huella(altura_m, cam)
    paso_frontal = huella_alto * (1 - solape_frontal)
    paso_lateral = huella_ancho * (1 - solape_lateral)
    lineas = math.ceil(ancho_m / paso_lateral) + 1
    por_linea = math.ceil(largo_m / paso_frontal) + 1

    # Recorrido en "cortacesped": todas las lineas + los traslados entre ellas
    distancia = lineas * largo_m + (lineas - 1) * paso_lateral
    tiempo_min = distancia / velocidad_ms / 60

    return {
        "altura_m": altura_m,
        "gsd_cm_px": round(gsd, 3),
        "cumple_gsd": gsd < GSD_MAX_CM_PX,
        "huella_m": (round(huella_ancho, 2), round(huella_alto, 2)),
        "paso_frontal_m": round(paso_frontal, 2),
        "paso_lateral_m": round(paso_lateral, 2),
        "lineas": lineas,
        "fotos_por_linea": por_linea,
        "total_fotos": lineas * por_linea,
        "intervalo_disparo_s": round(paso_frontal / velocidad_ms, 2),
        "distancia_m": round(distancia, 1),
        "tiempo_vuelo_min": round(tiempo_min, 1),
        "baterias": math.ceil(tiempo_min / autonomia_min),
    }


# ---------- Parcela georreferenciada (rutas, cuadrantes y cobertura) ----------

R_TIERRA = 6371000.0
CUADRANTES = {"N": "Q1", "E": "Q2", "S": "Q3", "W": "Q4"}   # nombres del entregable


@dataclass(frozen=True)
class Parcela:
    # Rectangulo en terreno. (lat, lon) es la esquina de origen; el eje "largo" sigue
    # las lineas de vuelo con rumbo_deg (0 = norte, 90 = este) y el "ancho" queda a la derecha.
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
        # Metros locales -> (lat, lon). Aproximacion plana, valida para pocas hectareas.
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
    # Q1 Norte, Q2 Este, Q3 Sur, Q4 Oeste: la parcela se divide por las rectas a 45 grados
    # (en el mapa) que pasan por el centro, 1/4 del area cada uno. Los puntos justo sobre
    # una division se reparten "en molinete" para que ningun cuadrante salga favorecido.
    if not parcela.contiene(x, y):
        return "FUERA"
    este, norte = parcela.a_mundo(x - parcela.ancho_m / 2, y - parcela.largo_m / 2)
    if abs(abs(norte) - abs(este)) < 1e-6:
        if este >= 0:
            return CUADRANTES["N" if norte >= 0 else "E"]
        return CUADRANTES["S" if norte < 0 else "W"]
    if abs(norte) > abs(este):
        return CUADRANTES["N" if norte >= 0 else "S"]
    return CUADRANTES["E" if este >= 0 else "W"]


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
    # Waypoints en "cortacesped": inicio y fin de cada linea, alternando el sentido.
    # dist_m = distancia recorrida desde el despegue hasta ese punto.
    xs, paso = lineas_x(parcela, altura_m, solape_lateral, cam)
    puntos = []
    for i, x in enumerate(xs):
        extremos = (0.0, parcela.largo_m) if i % 2 == 0 else (parcela.largo_m, 0.0)
        for k, y in enumerate(extremos):
            lat, lon = parcela.a_geo(x, y)
            dist = i * (parcela.largo_m + paso) + k * parcela.largo_m
            puntos.append({"n": len(puntos) + 1, "linea": i + 1,
                           "lat": round(lat, 7), "lon": round(lon, 7), "alt_m": altura_m,
                           "dist_m": round(dist, 2)})
    return puntos


def posiciones_disparo(parcela, altura_m=25.0, solape_frontal=0.80, solape_lateral=0.75,
                       cam=CAMARA):
    # Donde dispara la camara: fotos repartidas por igual en cada linea, sin pasar
    # del paso frontal maximo (asi el solape real es >= al pedido)
    xs, paso_lat = lineas_x(parcela, altura_m, solape_lateral, cam)
    _, huella_alto = huella(altura_m, cam)
    por_linea = math.ceil(parcela.largo_m / (huella_alto * (1 - solape_frontal))) + 1
    separacion = parcela.largo_m / (por_linea - 1)
    fotos = []
    for i, x in enumerate(xs):
        for j in range(por_linea):
            avance = j * separacion
            y = avance if i % 2 == 0 else parcela.largo_m - avance
            fotos.append({"n": len(fotos) + 1, "linea": i + 1, "x": x, "y": y,
                          "dist_m": i * (parcela.largo_m + paso_lat) + avance})
    return fotos


def escribir_kml(ruta_kml, puntos, parcela, velocidad_ms, intervalo_s):
    esquinas = [parcela.a_geo(x, y) for x, y in
                ((0, 0), (parcela.ancho_m, 0), (parcela.ancho_m, parcela.largo_m),
                 (0, parcela.largo_m), (0, 0))]
    poligono = " ".join(f"{lon:.7f},{lat:.7f},0" for lat, lon in esquinas)
    linea = " ".join(f"{p['lon']},{p['lat']},{p['alt_m']}" for p in puntos)
    marcas = "\n".join(
        f"    <Placemark><name>WP{p['n']}</name><description>linea {p['linea']}</description>"
        f"<Point><altitudeMode>relativeToGround</altitudeMode>"
        f"<coordinates>{p['lon']},{p['lat']},{p['alt_m']}</coordinates></Point></Placemark>"
        for p in puntos)
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
    # % de la parcela cubierto por las huellas de las fotos (rejilla de celda_m metros).
    # Supone la camara alineada con las lineas de vuelo (gimbal a nadir).
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
    # Usa las fotos ACEPTADAS (con lat/lon) de un reporte de QA
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
    return {"fotos_usadas": len(puntos), "sin_coordenadas": sin_gps,
            "por_cuadrante": por_cuadrante, "cobertura_pct": pct,
            "cumple_cobertura": pct >= 100.0}


# ---------- Conteo de referencia / Ground Truth (1.2.1) ----------

def comparar_conteo(filas):
    # filas: iterable de dicts con cuadrante, esperadas, conteo
    detalle, total_esp, total_cont = [], 0, 0
    for f in filas:
        esperadas, conteo = int(f["esperadas"]), int(f["conteo"])
        if esperadas <= 0 or conteo < 0:
            raise ValueError(f"Valores invalidos en el cuadrante {f['cuadrante']}")
        dif = conteo - esperadas
        detalle.append({"cuadrante": f["cuadrante"], "esperadas": esperadas,
                        "conteo": conteo, "diferencia": dif,
                        "porcentaje": round(dif * 100 / esperadas, 2)})
        total_esp += esperadas
        total_cont += conteo
    if not detalle:
        raise ValueError("La planilla no tiene cuadrantes")
    dif = total_cont - total_esp
    return {"detalle": detalle, "esperadas": total_esp, "conteo": total_cont,
            "diferencia": dif, "porcentaje": round(dif * 100 / total_esp, 2)}


def leer_planilla_conteo(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return comparar_conteo(csv.DictReader(f))


# ---------- Auditoria de fotos (1.2.2) ----------

def listar_fotos(carpeta, recursivo=False):
    # Rutas relativas (con "/") de las fotos JPG, ordenadas
    fotos = []
    for raiz, dirs, archivos in os.walk(carpeta):
        dirs.sort()
        for nombre in archivos:
            if nombre.lower().endswith(EXTENSIONES):
                rel = os.path.relpath(os.path.join(raiz, nombre), carpeta)
                fotos.append(rel.replace(os.sep, "/"))
        if not recursivo:
            break
    return sorted(fotos)


def _a_grados(valor, ref):
    # EXIF guarda (grados, minutos, segundos); S y W son negativos
    partes = [float(v) for v in valor] if isinstance(valor, (tuple, list)) else [float(valor)]
    partes += [0.0] * (3 - len(partes))
    dec = partes[0] + partes[1] / 60 + partes[2] / 3600
    return -dec if str(ref).upper().startswith(("S", "W")) else dec


def leer_gps(ruta):
    # (lat, lon) en grados decimales, o None si la foto no trae coordenadas
    from PIL import Image
    try:
        with Image.open(ruta) as img:
            gps = img.getexif().get_ifd(GPS_TAG)
            if GPS_LATITUD not in gps or GPS_LONGITUD not in gps:
                return None
            lat = _a_grados(gps[GPS_LATITUD], gps.get(1, "N"))
            lon = _a_grados(gps[GPS_LONGITUD], gps.get(3, "E"))
    except Exception:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return round(lat, 7), round(lon, 7)


def tiene_gps(ruta):
    # Cuenta como GPS solo si el bloque trae latitud y longitud validas
    return leer_gps(ruta) is not None


def leer_gris(ruta):
    # cv2.imread falla con tildes/enies en la ruta en Windows; se decodifica desde bytes
    import cv2
    import numpy as np
    datos = np.fromfile(ruta, dtype=np.uint8)
    if datos.size == 0:
        return None
    return cv2.imdecode(datos, cv2.IMREAD_GRAYSCALE)


def evaluar_imagen(ruta):
    # Devuelve (resolucion, nitidez, coords, motivos). coords = (lat, lon) o None.
    # Sin motivos = aceptada.
    import cv2
    if os.path.getsize(ruta) < TAMANO_MINIMO:
        return "N/A", 0.0, None, ["INCOMPLETA"]

    gris = leer_gris(ruta)
    if gris is None:
        return "N/A", 0.0, None, ["CORRUPTA"]

    alto, ancho = gris.shape
    nitidez = round(float(cv2.Laplacian(gris, cv2.CV_64F).var()), 2)
    coords = leer_gps(ruta)

    motivos = []
    if (ancho, alto) != RESOLUCION:
        motivos.append("RESOLUCION")
    if nitidez < NITIDEZ_MINIMA:
        motivos.append("BORROSA")
    if coords is None:
        motivos.append("SIN_GPS")
    return f"{ancho}x{alto}", nitidez, coords, motivos


def auditar_lote(carpeta, reporte_csv, recursivo=False, hilos=4):
    if not os.path.isdir(carpeta):
        return {"error": f"No existe la carpeta {carpeta}"}

    archivos = listar_fotos(carpeta, recursivo)
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        resultados = list(pool.map(
            lambda rel: evaluar_imagen(os.path.join(carpeta, rel)), archivos))

    aceptadas, descartadas, nitideces = [], [], []
    por_grupo = {}
    with open(reporte_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "grupo", "resolucion", "nitidez", "gps", "lat", "lon",
                    "dictamen", "motivo"])
        for rel, (res, nit, coords, motivos) in zip(archivos, resultados):
            grupo = rel.split("/")[0] if "/" in rel else "."
            dictamen = "RECHAZADA" if motivos else "ACEPTADA"
            lat, lon = coords if coords else ("", "")
            w.writerow([rel, grupo, res, nit, coords is not None, lat, lon,
                        dictamen, "+".join(motivos)])
            g = por_grupo.setdefault(grupo, {"aceptadas": 0, "descartadas": 0})
            if motivos:
                descartadas.append((rel, "+".join(motivos)))
                g["descartadas"] += 1
            else:
                aceptadas.append(rel)
                nitideces.append(nit)
                g["aceptadas"] += 1

    promedio = round(sum(nitideces) / len(nitideces), 1) if nitideces else 0.0
    return {"extraidas": len(archivos), "aceptadas": len(aceptadas),
            "descartadas": len(descartadas), "detalle": descartadas,
            "nitidez_promedio_aceptadas": promedio, "por_grupo": por_grupo,
            "reporte": reporte_csv}


def leer_aceptadas(reporte_csv):
    # Archivos con dictamen ACEPTADA en un reporte de auditoria
    with open(reporte_csv, newline="", encoding="utf-8") as f:
        return {fila["archivo"] for fila in csv.DictReader(f)
                if fila["dictamen"] == "ACEPTADA"}


# ---------- Carga a S3 (Epica 2) ----------

SEGMENTO_VALIDO = re.compile(r"^[A-Za-z0-9_-]+$")


def validar_destino(finca, lote, fecha):
    for nombre, valor in (("finca", finca), ("lote", lote)):
        if not SEGMENTO_VALIDO.match(valor):
            raise ValueError(f"{nombre} solo admite letras, numeros, '_' y '-': {valor!r}")
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"fecha debe ser AAAA-MM-DD: {fecha!r}") from None


def md5_archivo(ruta):
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.digest()


def ya_existe(cliente, clave, md5_hex):
    # True si S3 ya tiene el mismo archivo. En subidas simples el ETag es el MD5;
    # en multiparte no, por eso tambien se guarda el MD5 en los metadatos.
    try:
        cab = cliente.head_object(Bucket=BUCKET, Key=clave)
    except Exception:
        return False
    return (cab.get("ETag", "").strip('"') == md5_hex
            or cab.get("Metadata", {}).get("md5") == md5_hex)


def subir_imagen(ruta, finca, lote, fecha, dry_run=True, cliente=None, rel=None):
    rel = rel or os.path.basename(ruta)
    if not os.path.exists(ruta):
        return {"archivo": rel, "estado": "NO_EXISTE"}
    tamano = os.path.getsize(ruta)
    if tamano < TAMANO_MINIMO:
        return {"archivo": rel, "estado": "MUY_PEQUENA"}

    clave = f"{prefijo_s3(finca, lote, fecha)}{rel}"
    md5 = md5_archivo(ruta)
    multiparte = tamano >= UMBRAL_MULTIPARTE
    resultado = {"archivo": rel, "clave": clave, "md5": md5.hex(), "bytes": tamano,
                 "multiparte": multiparte}

    if dry_run:
        return {**resultado, "estado": "SIMULADO"}

    extra = {"ContentType": "image/jpeg", "ServerSideEncryption": "AES256",
             "Metadata": {"md5": md5.hex()}}
    try:
        if ya_existe(cliente, clave, md5.hex()):
            return {**resultado, "estado": "YA_EXISTE"}
        if multiparte:
            # boto3 parte el archivo y reintenta cada parte por separado
            cliente.upload_file(ruta, BUCKET, clave, ExtraArgs=extra)
        else:
            # S3 rechaza el archivo si el MD5 no coincide
            with open(ruta, "rb") as f:
                cliente.put_object(Bucket=BUCKET, Key=clave, Body=f,
                                   ContentMD5=base64.b64encode(md5).decode(), **extra)
    except Exception as e:  # un fallo no detiene el resto del lote
        return {**resultado, "estado": "ERROR", "error": str(e)}
    return {**resultado, "estado": "SUBIDO"}


def prefijo_s3(finca, lote, fecha):
    return f"raw/{finca}/{lote}/{fecha}/"


def crear_cliente_s3():
    import boto3
    from botocore.config import Config
    return boto3.client("s3", region_name=REGION,
                        config=Config(retries={"max_attempts": 5, "mode": "standard"}))


def subir_lote(carpeta, finca, lote, fecha, dry_run=True, hilos=8,
               solo=None, recursivo=False, cliente=None):
    # solo: conjunto de rutas relativas permitidas (p. ej. las ACEPTADAS del QA)
    validar_destino(finca, lote, fecha)
    if not os.path.isdir(carpeta):
        raise FileNotFoundError(f"No existe la carpeta {carpeta}")

    if not dry_run and cliente is None:
        cliente = crear_cliente_s3()

    rels = listar_fotos(carpeta, recursivo or solo is not None)
    if solo is not None:
        rels = [r for r in rels if r in solo]
    with ThreadPoolExecutor(max_workers=hilos) as pool:
        return list(pool.map(
            lambda r: subir_imagen(os.path.join(carpeta, r), finca, lote, fecha,
                                   dry_run, cliente, rel=r), rels))


def contar_estados(resultados):
    estados = {}
    for r in resultados:
        estados[r["estado"]] = estados.get(r["estado"], 0) + 1
    return estados


def crear_manifiesto(resultados, finca, lote, fecha):
    # Inventario del lote: que se subio, con que MD5 y en que estado quedo
    return {
        "proyecto": "AgroDron",
        "finca": finca, "lote": lote, "fecha_vuelo": fecha,
        "bucket": BUCKET, "prefijo": prefijo_s3(finca, lote, fecha),
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "totales": contar_estados(resultados),
        "bytes_totales": sum(r.get("bytes", 0) for r in resultados),
        "archivos": [{k: r[k] for k in ("archivo", "clave", "md5", "bytes", "estado")
                      if k in r} for r in resultados],
    }


def subir_manifiesto(cliente, manifiesto):
    # Se guarda junto a las fotos como manifiesto.json
    cuerpo = json.dumps(manifiesto, ensure_ascii=False, indent=2).encode("utf-8")
    clave = f"{manifiesto['prefijo']}manifiesto.json"
    cliente.put_object(Bucket=BUCKET, Key=clave, Body=cuerpo,
                       ContentMD5=base64.b64encode(hashlib.md5(cuerpo).digest()).decode(),
                       ContentType="application/json", ServerSideEncryption="AES256")
    return clave


def parcela_desde_args(args):
    return Parcela(args.lat, args.lon, args.ancho, args.largo, args.rumbo)


# ---------- Linea de comandos ----------

def imprimir(datos, como_json=False):
    if como_json:
        print(json.dumps(datos, ensure_ascii=False, indent=2))
    else:
        for k, v in datos.items():
            print(f"{k}: {v}")


def cmd_calibracion(args):
    fallos, advertencias = validar_calibracion(
        args.satelites, leer_obturacion(args.obturacion), args.hdop)
    for a in advertencias:
        print(f"ADVERTENCIA {a}")
    for f in fallos:
        print(f"FALLA {f}")
    print("CA1: CUMPLE" if not fallos else "CA1: NO CUMPLE, recalibrar antes de volar")
    return 1 if fallos else 0


def cmd_plan(args):
    altura = altura_recomendada() if args.altura is None else args.altura
    plan = calcular_plan_vuelo(ancho_m=args.ancho, largo_m=args.largo, altura_m=altura,
                               solape_frontal=args.solape_frontal,
                               solape_lateral=args.solape_lateral,
                               velocidad_ms=args.velocidad, autonomia_min=args.autonomia)
    imprimir(plan, args.json)
    if args.json:
        return 0 if plan["cumple_gsd"] else 1
    print(f"altura maxima para GSD < {GSD_MAX_CM_PX}: {altura_maxima():.2f} m "
          f"(recomendada: {altura_recomendada()} m)")
    if not plan["cumple_gsd"]:
        print(f"ADVERTENCIA: el GSD no cumple el requisito, baja la altura a "
              f"{altura_recomendada()} m o menos")
        return 1
    return 0


def cmd_conteo(args):
    r = leer_planilla_conteo(args.planilla)
    if args.json:
        imprimir(r, True)
        return 0
    print(f"{'cuadrante':<12}{'esperadas':>10}{'conteo':>8}{'dif':>7}{'%':>8}")
    for d in r["detalle"]:
        print(f"{d['cuadrante']:<12}{d['esperadas']:>10}{d['conteo']:>8}"
              f"{d['diferencia']:>7}{d['porcentaje']:>8}")
    print(f"{'TOTAL':<12}{r['esperadas']:>10}{r['conteo']:>8}"
          f"{r['diferencia']:>7}{r['porcentaje']:>8}")
    return 0


def cmd_qa(args):
    r = auditar_lote(args.carpeta, args.reporte, args.recursivo, args.hilos)
    if "error" in r:
        print(r["error"], file=sys.stderr)
        return 2
    if args.json:
        imprimir(r, True)
        return 0
    print(f"extraidas: {r['extraidas']}  aceptadas: {r['aceptadas']}  "
          f"descartadas: {r['descartadas']}  nitidez promedio: {r['nitidez_promedio_aceptadas']}")
    for grupo, g in r["por_grupo"].items():
        print(f"  {grupo}: {g['aceptadas']} aceptadas / {g['descartadas']} descartadas")
    for nombre, motivo in r["detalle"]:
        print(f"  RECHAZADA {nombre}: {motivo}")
    print(f"reporte: {r['reporte']}")
    return 0


def cmd_subir(args):
    solo = leer_aceptadas(args.solo_aceptadas) if args.solo_aceptadas else None
    cliente = crear_cliente_s3() if args.real else None
    resultados = subir_lote(args.carpeta, args.finca, args.lote, args.fecha,
                            dry_run=not args.real, hilos=args.hilos,
                            solo=solo, recursivo=args.recursivo, cliente=cliente)
    for r in resultados:
        if r["estado"] == "ERROR":
            print(f"ERROR {r['archivo']}: {r['error']}", file=sys.stderr)
    print(contar_estados(resultados))

    manifiesto = crear_manifiesto(resultados, args.finca, args.lote, args.fecha)
    if args.manifiesto:
        with open(args.manifiesto, "w", encoding="utf-8") as f:
            json.dump(manifiesto, f, ensure_ascii=False, indent=2)
        print(f"manifiesto local: {args.manifiesto}")
    if args.real:
        try:
            print(f"manifiesto en S3: {subir_manifiesto(cliente, manifiesto)}")
        except Exception as e:
            print(f"ERROR al subir el manifiesto: {e}", file=sys.stderr)
            return 1
    return 1 if any(r["estado"] == "ERROR" for r in resultados) else 0


def cmd_ruta(args):
    parcela = parcela_desde_args(args)
    altura = altura_recomendada() if args.altura is None else args.altura
    plan = calcular_plan_vuelo(parcela.ancho_m, parcela.largo_m, altura,
                               args.solape_frontal, args.solape_lateral, args.velocidad)
    puntos = generar_ruta(parcela, altura, args.solape_lateral)
    escribir_kml(args.salida, puntos, parcela, args.velocidad, plan["intervalo_disparo_s"])
    ruta_csv = os.path.splitext(args.salida)[0] + "_waypoints.csv"
    escribir_waypoints_csv(ruta_csv, puntos, args.velocidad)
    print(f"{len(puntos)} waypoints en {plan['lineas']} lineas a {altura} m "
          f"(GSD {plan['gsd_cm_px']} cm/px, disparo cada {plan['intervalo_disparo_s']} s)")
    print(f"KML: {args.salida}\nCSV: {ruta_csv}")
    if not plan["cumple_gsd"]:
        print("ADVERTENCIA: a esta altura el GSD no cumple el requisito")
        return 1
    return 0


def cmd_cobertura(args):
    altura = altura_recomendada() if args.altura is None else args.altura
    r = evaluar_cobertura(args.reporte, parcela_desde_args(args), altura)
    if args.json:
        imprimir(r, True)
    else:
        print(f"fotos aceptadas con GPS: {r['fotos_usadas']}  "
              f"(sin coordenadas: {r['sin_coordenadas']})")
        for q, n in r["por_cuadrante"].items():
            print(f"  {q}: {n}")
        print(f"cobertura de la parcela: {r['cobertura_pct']} %")
        print("CA2 cobertura: CUMPLE" if r["cumple_cobertura"]
              else "CA2 cobertura: NO CUMPLE, hay zonas sin fotos aceptadas")
    return 0 if r["cumple_cobertura"] else 1


def cmd_flujo(args):
    # QA + carga solo de las aceptadas, en un paso
    r = auditar_lote(args.carpeta, args.reporte, args.recursivo, args.hilos)
    if "error" in r:
        print(r["error"], file=sys.stderr)
        return 2
    print(f"QA: {r['aceptadas']} aceptadas / {r['descartadas']} descartadas")
    args.solo_aceptadas = args.reporte
    return cmd_subir(args)


def cmd_demo(args):
    from src import simulator as sim
    res = sim.ejecutar_simulacion(
        carpeta_salida=args.carpeta,
        total_fotos=args.fotos,
        descartadas=args.descartadas,
        altura_m=args.altura,
        lat=args.lat,
        lon=args.lon,
        rumbo=args.rumbo,
        abrir_navegador=not args.no_abrir,
    )
    print(f"Simulacion completada en: {res['carpeta_salida']}")
    print(f"  Fotos generadas: {res['fotos_generadas']} "
          f"({res['aceptadas']} aceptadas / {res['descartadas']} descartadas)")
    print(f"  Cobertura parcela: {res['cobertura_pct']} %")
    print(f"  Subidas S3 simuladas: {res['subidas_simuladas']}")
    print(f"  Panel interactivo (mapa + dron): {res['panel_html']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="AgroDron Sprint 1 / Epica 1")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("calibracion", help="valida la calibracion del dron (CA1)")
    c.add_argument("--satelites", type=int, required=True)
    c.add_argument("--obturacion", required=True, help="p. ej. 1/1000")
    c.add_argument("--hdop", type=float)
    c.set_defaults(fn=cmd_calibracion)

    p = sub.add_parser("plan", help="calcula el plan de vuelo")
    p.add_argument("--altura", type=float, help="por defecto usa la recomendada")
    p.add_argument("--ancho", type=float, default=100.0)
    p.add_argument("--largo", type=float, default=100.0)
    p.add_argument("--solape-frontal", type=float, default=0.80)
    p.add_argument("--solape-lateral", type=float, default=0.75)
    p.add_argument("--velocidad", type=float, default=4.5)
    p.add_argument("--autonomia", type=float, default=15.0, help="minutos utiles por bateria")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_plan)

    g = sub.add_parser("conteo", help="compara el conteo en tierra con lo esperado (CA5)")
    g.add_argument("planilla", help="CSV con columnas cuadrante,esperadas,conteo")
    g.add_argument("--json", action="store_true")
    g.set_defaults(fn=cmd_conteo)

    def opciones_qa(x):
        x.add_argument("carpeta")
        x.add_argument("--reporte", default="reporte_qa.csv")
        x.add_argument("--recursivo", action="store_true",
                       help="incluye subcarpetas (p. ej. Q1..Q4)")
        x.add_argument("--hilos", type=int, default=4)

    def opciones_subir(x):
        x.add_argument("--finca", required=True)
        x.add_argument("--lote", required=True)
        x.add_argument("--fecha", required=True, help="AAAA-MM-DD")
        x.add_argument("--real", action="store_true", help="sube de verdad a AWS")
        x.add_argument("--manifiesto", metavar="JSON",
                       help="guarda el manifiesto del lote en este archivo local")

    def opciones_parcela(x):
        x.add_argument("--lat", type=float, required=True, help="latitud de la esquina de origen")
        x.add_argument("--lon", type=float, required=True, help="longitud de la esquina de origen")
        x.add_argument("--ancho", type=float, default=100.0)
        x.add_argument("--largo", type=float, default=100.0)
        x.add_argument("--rumbo", type=float, default=0.0,
                       help="direccion de las lineas de vuelo en grados (0 = norte)")
        x.add_argument("--altura", type=float, help="por defecto usa la recomendada")

    r = sub.add_parser("ruta", help="exporta la ruta de vuelo a KML y CSV de waypoints")
    opciones_parcela(r)
    r.add_argument("--solape-frontal", type=float, default=0.80)
    r.add_argument("--solape-lateral", type=float, default=0.75)
    r.add_argument("--velocidad", type=float, default=4.5)
    r.add_argument("--salida", default="ruta_vuelo.kml")
    r.set_defaults(fn=cmd_ruta)

    cb = sub.add_parser("cobertura", help="cuadrantes por GPS y % de la parcela cubierto (CA2)")
    cb.add_argument("reporte", help="reporte CSV generado por qa")
    opciones_parcela(cb)
    cb.add_argument("--json", action="store_true")
    cb.set_defaults(fn=cmd_cobertura)

    q = sub.add_parser("qa", help="audita las fotos de una carpeta (CA4)")
    opciones_qa(q)
    q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_qa)

    s = sub.add_parser("subir", help="sube las fotos a S3 (simulacion por defecto)")
    s.add_argument("carpeta")
    opciones_subir(s)
    s.add_argument("--solo-aceptadas", metavar="REPORTE_CSV",
                   help="sube solo las fotos ACEPTADAS en ese reporte de QA")
    s.add_argument("--recursivo", action="store_true")
    s.add_argument("--hilos", type=int, default=8)
    s.set_defaults(fn=cmd_subir)

    fl = sub.add_parser("flujo", help="QA y luego sube solo las aceptadas")
    opciones_qa(fl)
    opciones_subir(fl)
    fl.set_defaults(fn=cmd_flujo)

    dm = sub.add_parser("demo", help="genera cultivo, fotos con GPS, corre QA y abre el mapa con el dron")
    dm.add_argument("--carpeta", default="output", help="carpeta donde se guardan las subcarpetas de salida")
    dm.add_argument("--fotos", type=int, default=48, help="cantidad de fotos a simular (usa 148 para el lote completo)")
    dm.add_argument("--descartadas", type=int, default=2, help="fotos borrosas en giros de cabecera (8 para 148)")
    dm.add_argument("--altura", type=float, default=25.0)
    dm.add_argument("--lat", type=float, default=5.0949,
                    help="latitud en Vereda La Cabana (zona rural de Manizales)")
    dm.add_argument("--lon", type=float, default=-75.5891,
                    help="longitud en Vereda La Cabana (zona rural de Manizales)")
    dm.add_argument("--rumbo", type=float, default=45.0)
    dm.add_argument("--no-abrir", action="store_true", help="no abrir el navegador automaticamente")
    dm.set_defaults(fn=cmd_demo)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
