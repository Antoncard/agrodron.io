# Respaldo y prueba de restauracion de base de datos SQLite o MySQL (BD-N6)
import argparse
from contextlib import closing
from datetime import datetime
import os
import sqlite3
import subprocess
import sys
from urllib.parse import urlparse

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from src.db.config import obtener_configuracion


def respaldar_sqlite(ruta_origen: str, carpeta_destino: str) -> str:
    if not os.path.isfile(ruta_origen):
        raise FileNotFoundError(f"No existe base de datos SQLite en {ruta_origen}")
    os.makedirs(carpeta_destino, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(carpeta_destino, f"agrodron_backup_{ts}.sqlite3")
    with closing(sqlite3.connect(ruta_origen)) as src_conn, closing(sqlite3.connect(destino)) as dst_conn:
        src_conn.backup(dst_conn)
    return destino


def restaurar_y_verificar_sqlite(ruta_respaldo: str, ruta_destino: str) -> dict:
    with closing(sqlite3.connect(ruta_respaldo)) as src_conn, closing(sqlite3.connect(ruta_destino)) as dst_conn:
        src_conn.backup(dst_conn)
    with closing(sqlite3.connect(ruta_destino)) as conn:
        tablas = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        vuelos = conn.execute("SELECT COUNT(*) FROM vuelo").fetchone()[0] if "vuelo" in tablas else 0
    return {"tablas": len(tablas), "vuelos": vuelos, "ruta_restaurada": ruta_destino}


def respaldar_mysql(database_url: str, carpeta_destino: str) -> str:
    os.makedirs(carpeta_destino, exist_ok=True)
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(carpeta_destino, f"agrodron_mysql_{ts}.sql")
    cmd = [
        "mysqldump",
        f"--host={parsed.hostname or 'localhost'}",
        f"--port={parsed.port or 3306}",
        f"--user={parsed.username or 'root'}",
        db_name,
    ]
    env = os.environ.copy()
    if parsed.password:
        env["MYSQL_PWD"] = parsed.password
    with open(destino, "w", encoding="utf-8") as f:
        subprocess.run(cmd, stdout=f, check=True, env=env)
    return destino


def main():
    ap = argparse.ArgumentParser(description="Respaldo de BD AgroDron (BD-N6)")
    ap.add_argument("--destino", default="backups")
    ap.add_argument("--verificar", action="store_true", help="Prueba restaurar el respaldo en un archivo temporal")
    args = ap.parse_args()

    url = obtener_configuracion().database_url
    if url.startswith("sqlite:///"):
        ruta_db = url.replace("sqlite:///", "", 1)
        respaldo = respaldar_sqlite(ruta_db, args.destino)
        print(f"Respaldo SQLite creado: {respaldo}")
        if args.verificar:
            tmp_rest = os.path.join(args.destino, "verificacion_restore.tmp.sqlite3")
            try:
                info = restaurar_y_verificar_sqlite(respaldo, tmp_rest)
                print(f"Prueba de restauracion OK: {info}")
            finally:
                if os.path.exists(tmp_rest):
                    os.remove(tmp_rest)
    elif url.startswith("mysql"):
        respaldo = respaldar_mysql(url, args.destino)
        print(f"Respaldo MySQL creado: {respaldo}")
    else:
        raise ValueError(f"Motor no soportado para respaldo automatico: {url}")


if __name__ == "__main__":
    main()
