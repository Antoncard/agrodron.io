# Eliminacion de duplicados entre fotos solapadas (Epica 3)
import math

RADIO_FUSION_M = 0.6
MARGEN_CENTRO_M = 0.05


def fusionar_detecciones(detecciones_por_foto, radio_m=RADIO_FUSION_M, margen_m=MARGEN_CENTRO_M):
    # Cada punto se cuenta en la foto cuyo centro este mas cerca (con margen de 0,05 m)
    # y se eliminan duplicados dentro de un radio de 0,6 m.
    if not detecciones_por_foto:
        return []

    centros = [(float(f["x"]), float(f["y"])) for f in detecciones_por_foto]
    candidatos = []

    for idx_foto, foto in enumerate(detecciones_por_foto):
        cx, cy = centros[idx_foto]
        for pt in foto.get("puntos", ()):
            x, y = float(pt[0]), float(pt[1])
            conf = float(pt[2]) if len(pt) > 2 else 1.0
            dist_propia = math.hypot(x - cx, y - cy)
            dist_min = min(math.hypot(x - ox, y - oy) for ox, oy in centros)
            if dist_propia <= dist_min + margen_m:
                candidatos.append((dist_propia, -conf, x, y, conf))

    # Priorizar detecciones mas cercanas al centro optico y de mayor confianza
    candidatos.sort(key=lambda item: (item[0], item[1]))

    fusionados = []
    r2 = radio_m * radio_m
    for _, _, x, y, conf in candidatos:
        duplicado = False
        for fx, fy, _ in fusionados:
            dx, dy = x - fx, y - fy
            if dx * dx + dy * dy <= r2:
                duplicado = True
                break
        if not duplicado:
            fusionados.append((round(x, 3), round(y, 3), round(conf, 3)))

    return fusionados

