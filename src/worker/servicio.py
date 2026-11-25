# Worker de automatizacion de eventos y ejecucion de corridas IA (Subtareas 2.2.1 y 2.2.2)
import argparse
import logging
import os
import time

logger = logging.getLogger("agrodron.worker")

from src.dominio.qa_fotos import auditar_lote
from src.db.config import obtener_configuracion
from src.db.models import CorridaIA, Imagen, ModeloIA, Vuelo
from src.db.session import create_session_factory
from src.ml.pipeline_vuelo import procesar_vuelo_en_bd
from src.servicios.importador import importar_lote_vuelo, registrar_vuelo
from src.servicios.reportes import crear_y_guardar_reporte


def procesar_siguiente_corrida(session, reportes_dir: str | None = None):
    corrida = (
        session.query(CorridaIA)
        .filter(CorridaIA.estado == "EN_COLA")
        .order_by(CorridaIA.id.asc())
        .first()
    )
    if corrida is None:
        return None
    res = procesar_vuelo_en_bd(session, corrida.vuelo_id, corrida.id)
    if res.get("estado") == "LISTA":
        crear_y_guardar_reporte(
            session,
            corrida.id,
            reportes_dir or obtener_configuracion().reportes_dir,
        )
    return res


def escanear_carpeta_raw(
    session,
    carpeta_raw: str,
    parcela_id: int,
    modelo_id: int | None = None,
    altura_m: float = 25.0,
):
    # Detecta lotes en raw/<finca>/<lote>/<fecha>/ que aun no esten procesados en BD
    if not os.path.isdir(carpeta_raw):
        return []
    encoladas = []
    modelo = (
        session.get(ModeloIA, modelo_id)
        if modelo_id
        else session.query(ModeloIA).order_by(ModeloIA.id.desc()).first()
    )

    for finca in sorted(os.listdir(carpeta_raw)):
        ruta_finca = os.path.join(carpeta_raw, finca)
        if not os.path.isdir(ruta_finca):
            continue
        for lote in sorted(os.listdir(ruta_finca)):
            ruta_lote = os.path.join(ruta_finca, lote)
            if not os.path.isdir(ruta_lote):
                continue
            for fecha in sorted(os.listdir(ruta_lote)):
                ruta_fecha = os.path.join(ruta_lote, fecha)
                if not os.path.isdir(ruta_fecha):
                    continue

                vuelo_ex = (
                    session.query(Vuelo)
                    .filter(Vuelo.parcela_id == parcela_id, Vuelo.fecha == fecha)
                    .first()
                )
                if vuelo_ex and session.query(Imagen).filter(Imagen.vuelo_id == vuelo_ex.id).count() > 0:
                    continue

                ruta_qa = os.path.join(ruta_fecha, "reporte_qa.csv")
                if not os.path.isfile(ruta_qa):
                    qa = auditar_lote(ruta_fecha, ruta_qa, recursivo=True)
                    if qa.get("extraidas", 0) == 0:
                        continue

                if vuelo_ex is None:
                    vuelo_ex = registrar_vuelo(
                        session,
                        parcela_id=parcela_id,
                        fecha=fecha,
                        altura_m=altura_m,
                        notas=f"Ingesta automatica desde {ruta_fecha}",
                    )
                ruta_man = os.path.join(ruta_fecha, "manifiesto.json")
                importar_lote_vuelo(
                    session,
                    vuelo_ex.id,
                    ruta_qa,
                    ruta_manifiesto_json=ruta_man if os.path.isfile(ruta_man) else None,
                    carpeta_fotos=ruta_fecha,
                )
                if modelo is not None:
                    corrida = CorridaIA(
                        vuelo_id=vuelo_ex.id,
                        modelo_id=modelo.id,
                        umbral_confianza=float((modelo.metricas_json or {}).get("umbral_calibrado", 0.45)),
                        radio_fusion_m=0.6,
                        estado="EN_COLA",
                        total_detectadas=0,
                        errores_json=[],
                    )
                    session.add(corrida)
                    session.commit()
                    encoladas.append(corrida.id)
    return encoladas


def ejecutar_bucle_worker(
    intervalo_s: float = 5.0,
    una_vez: bool = False,
    carpeta_raw: str | None = None,
    parcela_id: int = 1,
):
    cfg = obtener_configuracion()
    sf, _ = create_session_factory(cfg.database_url)
    ruta_raw = carpeta_raw or os.path.join(cfg.storage_dir, "raw")

    while True:
        try:
            with sf() as session:
                try:
                    escanear_carpeta_raw(session, ruta_raw, parcela_id=parcela_id)
                    while True:
                        res = procesar_siguiente_corrida(session, reportes_dir=cfg.reportes_dir)
                        if res is None:
                            break
                except Exception:
                    session.rollback()
                    raise
        except Exception as exc:
            logger.exception("Error en ciclo del worker AgroDron: %s", exc)
            if una_vez:
                raise
        if una_vez:
            break
        time.sleep(intervalo_s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Worker de automatizacion AgroDron")
    ap.add_argument("--intervalo", type=float, default=5.0)
    ap.add_argument("--una-vez", action="store_true")
    ap.add_argument("--carpeta-raw", default=None)
    ap.add_argument("--parcela-id", type=int, default=1)
    args = ap.parse_args()
    ejecutar_bucle_worker(args.intervalo, args.una_vez, args.carpeta_raw, args.parcela_id)
