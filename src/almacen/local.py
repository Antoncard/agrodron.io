# Almacenamiento local idempotente de lotes de fotos con verificacion MD5 (Epica 2)
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import os
import re
import shutil

EXTENSIONES = (".jpg", ".jpeg")
TAMANO_MINIMO = 10 * 1024  # bytes
SEGMENTO_VALIDO = re.compile(r"^[A-Za-z0-9_-]+$")


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


def validar_destino(finca, lote, fecha):
    # Valida que finca/lote sean seguros para rutas y fecha sea AAAA-MM-DD
    for nombre, valor in (("finca", finca), ("lote", lote)):
        if not SEGMENTO_VALIDO.match(str(valor)):
            raise ValueError(f"{nombre} solo admite letras, numeros, '_' y '-': {valor!r}")
    try:
        datetime.strptime(str(fecha), "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"fecha debe ser AAAA-MM-DD: {fecha!r}") from None


def md5_archivo(ruta):
    # Calcula el hash MD5 binario de un archivo en bloques
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.digest()


def ruta_relativa_lote(finca, lote, fecha):
    # Ruta relativa estandar dentro del almacen local
    return f"raw/{finca}/{lote}/{fecha}/"


def copiar_imagen(ruta, destino, finca, lote, fecha, rel=None):
    # Copia una foto validando tamano e idempotencia por MD5
    rel = (rel or os.path.basename(ruta)).replace(os.sep, "/")
    if not os.path.exists(ruta):
        return {"archivo": rel, "md5": "", "bytes": 0, "estado": "NO_EXISTE"}

    try:
        tamano = os.path.getsize(ruta)
        if tamano < TAMANO_MINIMO:
            return {"archivo": rel, "md5": "", "bytes": tamano, "estado": "MUY_PEQUENA"}

        md5_hex = md5_archivo(ruta).hex()
        ruta_dest = os.path.join(destino, "raw", finca, lote, fecha, *rel.split("/"))

        if os.path.exists(ruta_dest):
            try:
                if md5_archivo(ruta_dest).hex() == md5_hex:
                    return {
                        "archivo": rel,
                        "md5": md5_hex,
                        "bytes": tamano,
                        "estado": "YA_EXISTE",
                    }
            except Exception:
                pass

        os.makedirs(os.path.dirname(ruta_dest), exist_ok=True)
        shutil.copy2(ruta, ruta_dest)
        return {
            "archivo": rel,
            "md5": md5_hex,
            "bytes": tamano,
            "estado": "COPIADO",
        }
    except Exception as e:
        return {
            "archivo": rel,
            "md5": "",
            "bytes": 0,
            "estado": "ERROR",
            "error": str(e),
        }


def copiar_lote(carpeta, destino, finca, lote, fecha, solo=None, recursivo=False, hilos=8):
    # Copia las fotos del lote a destino/raw/<finca>/<lote>/<fecha>/
    validar_destino(finca, lote, fecha)
    if not os.path.isdir(carpeta):
        raise FileNotFoundError(f"No existe la carpeta {carpeta}")

    rels = listar_fotos(carpeta, recursivo or solo is not None)
    if solo is not None:
        rels = [r for r in rels if r in solo]

    with ThreadPoolExecutor(max_workers=hilos) as pool:
        return list(
            pool.map(
                lambda r: copiar_imagen(
                    os.path.join(carpeta, r), destino, finca, lote, fecha, rel=r
                ),
                rels,
            )
        )


def contar_estados(resultados):
    # Cuenta cuantos archivos quedaron en cada estado
    estados = {}
    for r in resultados:
        estados[r["estado"]] = estados.get(r["estado"], 0) + 1
    return estados
