# Auditoria optica y verificacion EXIF GPS de fotografias (1.2.2 / CA4)
from concurrent.futures import ThreadPoolExecutor
import csv
import os

NITIDEZ_MINIMA = 120.0
RESOLUCION = (4000, 3000)  # ancho, alto en px
TAMANO_MINIMO = 10 * 1024  # bytes
GPS_TAG = 0x8825
GPS_LATITUD, GPS_LONGITUD = 2, 4
EXTENSIONES = (".jpg", ".jpeg")


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
    # Convierte (grados, minutos, segundos) EXIF a grados decimales
    partes = [float(v) for v in valor] if isinstance(valor, (tuple, list)) else [float(valor)]
    partes += [0.0] * (3 - len(partes))
    dec = partes[0] + partes[1] / 60 + partes[2] / 3600
    return -dec if str(ref).upper().startswith(("S", "W")) else dec


def leer_gps(ruta):
    # Devuelve (lat, lon) en grados decimales o None si no tiene GPS valido
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
    # True solo si el bloque EXIF GPS contiene latitud y longitud validas
    return leer_gps(ruta) is not None


def leer_gris(ruta):
    # Decodifica en escala de grises soportando rutas con tildes o enies en Windows
    import cv2
    import numpy as np
    datos = np.fromfile(ruta, dtype=np.uint8)
    if datos.size == 0:
        return None
    return cv2.imdecode(datos, cv2.IMREAD_GRAYSCALE)


def evaluar_imagen(ruta):
    # Devuelve (resolucion, nitidez, coords, motivos). Sin motivos = ACEPTADA.
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
        resultados = list(
            pool.map(lambda rel: evaluar_imagen(os.path.join(carpeta, rel)), archivos)
        )

    aceptadas, descartadas, nitideces = [], [], []
    por_grupo = {}
    with open(reporte_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "archivo", "grupo", "resolucion", "nitidez", "gps",
            "lat", "lon", "dictamen", "motivo",
        ])
        for rel, (res, nit, coords, motivos) in zip(archivos, resultados):
            grupo = rel.split("/")[0] if "/" in rel else "."
            dictamen = "RECHAZADA" if motivos else "ACEPTADA"
            lat, lon = coords if coords else ("", "")
            w.writerow([
                rel, grupo, res, nit, coords is not None,
                lat, lon, dictamen, "+".join(motivos),
            ])
            g = por_grupo.setdefault(grupo, {"aceptadas": 0, "descartadas": 0})
            if motivos:
                descartadas.append((rel, "+".join(motivos)))
                g["descartadas"] += 1
            else:
                aceptadas.append(rel)
                nitideces.append(nit)
                g["aceptadas"] += 1

    promedio = round(sum(nitideces) / len(nitideces), 1) if nitideces else 0.0
    return {
        "extraidas": len(archivos),
        "aceptadas": len(aceptadas),
        "descartadas": len(descartadas),
        "detalle": descartadas,
        "nitidez_promedio_aceptadas": promedio,
        "por_grupo": por_grupo,
        "reporte": reporte_csv,
    }


def leer_aceptadas(reporte_csv):
    # Conjunto de archivos con dictamen ACEPTADA en un reporte QA
    with open(reporte_csv, newline="", encoding="utf-8") as f:
        return {
            fila["archivo"]
            for fila in csv.DictReader(f)
            if fila["dictamen"] == "ACEPTADA"
        }

