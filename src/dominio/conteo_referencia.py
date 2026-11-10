# Conteo de referencia en tierra / Ground Truth (1.2.1 / CA5)
import csv

# Conteo real en tierra reportado en la parcela piloto (2.352 plantas vivas de 2.500 esperadas)
CONTEO_DOCUMENTO = [
    {"cuadrante": "Q1", "esperadas": 625, "conteo": 598},
    {"cuadrante": "Q2", "esperadas": 625, "conteo": 584},
    {"cuadrante": "Q3", "esperadas": 625, "conteo": 579},
    {"cuadrante": "Q4", "esperadas": 625, "conteo": 591},
]


def comparar_conteo(filas):
    # Compara conteo manual por cuadrante contra plantas esperadas
    detalle, total_esp, total_cont = [], 0, 0
    for f in filas:
        esperadas, conteo = int(f["esperadas"]), int(f["conteo"])
        if esperadas <= 0 or conteo < 0:
            raise ValueError(f"Valores invalidos en el cuadrante {f['cuadrante']}")
        dif = conteo - esperadas
        detalle.append({
            "cuadrante": f["cuadrante"],
            "esperadas": esperadas,
            "conteo": conteo,
            "diferencia": dif,
            "porcentaje": round(dif * 100 / esperadas, 2),
        })
        total_esp += esperadas
        total_cont += conteo
    if not detalle:
        raise ValueError("La planilla no tiene cuadrantes")
    dif = total_cont - total_esp
    return {
        "detalle": detalle,
        "esperadas": total_esp,
        "conteo": total_cont,
        "diferencia": dif,
        "porcentaje": round(dif * 100 / total_esp, 2),
    }


def leer_planilla_conteo(ruta):
    # Lee un archivo CSV de conteo en tierra y calcula desviaciones
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return comparar_conteo(csv.DictReader(f))

