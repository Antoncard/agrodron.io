# Creacion y guardado de manifiesto.json por lote (Epica 2)
from datetime import datetime
import json
import os

from src.almacen.local import contar_estados, ruta_relativa_lote


def crear_manifiesto(resultados, finca, lote, fecha):
    # Construye el diccionario del manifiesto local del lote
    return {
        "proyecto": "AgroDron",
        "finca": finca,
        "lote": lote,
        "fecha_vuelo": fecha,
        "ruta_lote": ruta_relativa_lote(finca, lote, fecha),
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "totales": contar_estados(resultados),
        "bytes_totales": sum(r.get("bytes", 0) for r in resultados),
        "archivos": [
            {k: r[k] for k in ("archivo", "md5", "bytes", "estado") if k in r}
            for r in resultados
        ],
    }


def guardar_manifiesto(ruta, manifiesto):
    # Guarda el manifiesto del lote en disco como JSON
    carpeta_dir = os.path.dirname(os.path.abspath(ruta))
    if carpeta_dir:
        os.makedirs(carpeta_dir, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(manifiesto, f, ensure_ascii=False, indent=2)
    return ruta
