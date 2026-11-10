# Calibracion (1.1.1) y calculo de plan de vuelo (1.1.2)
from dataclasses import dataclass
import math

GSD_MAX_CM_PX = 1.0
SATELITES_MINIMOS = 16
OBTURACION_MAXIMA_S = 1 / 1000
HDOP_MAXIMO = 1.0


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
    # Altura maxima que cumple el limite de GSD
    return gsd_max * cam.focal_mm * cam.ancho_px / (cam.sensor_ancho_mm * 100)


def altura_recomendada(gsd_max=GSD_MAX_CM_PX, cam=CAMARA, margen=0.05):
    # Altura maxima con margen de seguridad, redondeada hacia abajo a 0,5 m
    return math.floor(altura_maxima(gsd_max, cam) * (1 - margen) * 2) / 2


def huella(altura_m, cam=CAMARA):
    # Tamano en terreno (m) de una foto: (ancho, alto)
    gsd = calcular_gsd(altura_m, cam)
    return cam.ancho_px * gsd / 100, cam.alto_px * gsd / 100


def calcular_plan_vuelo(
    ancho_m=100.0,
    largo_m=100.0,
    altura_m=25.0,
    solape_frontal=0.80,
    solape_lateral=0.75,
    velocidad_ms=4.5,
    cam=CAMARA,
    autonomia_min=15.0,
):
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

    # Recorrido en cortacesped: todas las lineas + traslados laterales
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

