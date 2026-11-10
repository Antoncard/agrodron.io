# Georreferenciacion de detecciones: pixel -> metros en terreno y GPS (Epica 3)
import math

from src.dominio.parcela import R_TIERRA
from src.dominio.qa_fotos import RESOLUCION


def pixel_a_terreno(px, py, centro_x_m, centro_y_m, gsd_cm_px, resolucion=RESOLUCION):
    # Convierte pixel (px, py) de una foto a metros locales (x, y) en la parcela
    ancho_px, alto_px = resolucion
    escala_m = gsd_cm_px / 100.0
    dx = (float(px) - ancho_px / 2.0) * escala_m
    dy = (alto_px / 2.0 - float(py)) * escala_m
    return centro_x_m + dx, centro_y_m + dy


def terreno_a_pixel(x_m, y_m, centro_x_m, centro_y_m, gsd_cm_px, resolucion=RESOLUCION):
    # Convierte metros locales (x, y) en la parcela a coordenadas pixel (px, py)
    ancho_px, alto_px = resolucion
    escala_m = gsd_cm_px / 100.0
    px = ancho_px / 2.0 + (x_m - centro_x_m) / escala_m
    py = alto_px / 2.0 - (y_m - centro_y_m) / escala_m
    return px, py


def pixel_a_gps(px, py, lat_centro, lon_centro, gsd_cm_px, rumbo_deg=0.0, resolucion=RESOLUCION):
    # Convierte pixel (px, py) a (lat, lon) usando GSD, rumbo y centro GPS de la foto
    ancho_px, alto_px = resolucion
    escala_m = gsd_cm_px / 100.0
    dx = (float(px) - ancho_px / 2.0) * escala_m
    dy = (alto_px / 2.0 - float(py)) * escala_m
    r = math.radians(rumbo_deg)
    c, s = math.cos(r), math.sin(r)
    este = dx * c + dy * s
    norte = -dx * s + dy * c
    lat = lat_centro + math.degrees(norte / R_TIERRA)
    lon = lon_centro + math.degrees(este / (R_TIERRA * math.cos(math.radians(lat_centro))))
    return round(lat, 7), round(lon, 7)

