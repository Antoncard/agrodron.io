# Servicios de importacion de vuelos, imagenes QA y ground truth en transaccion (BD-01, BD-02, BD-05, BD-09)
import csv
import json
import os

from src.dominio.conteo_referencia import leer_planilla_conteo
from src.dominio.parcela import Parcela, asignar_cuadrante
from src.dominio.plan_vuelo import GSD_MAX_CM_PX, calcular_gsd, leer_obturacion, validar_calibracion
from src.db.models import Cuadrante, GroundTruth, Imagen, ParcelaDB, Vuelo


def registrar_vuelo(
    session,
    parcela_id: int,
    fecha: str,
    altura_m: float,
    solape_frontal: float = 0.80,
    solape_lateral: float = 0.75,
    velocidad_ms: float = 4.5,
    satelites: int = 18,
    hdop: float = 0.68,
    obturacion: str = "1/1000",
    notas: str | None = None,
) -> Vuelo:
    # BD-01: si satelites < 16 o obturacion > 1/1000 s queda RECHAZADO
    gsd = round(calcular_gsd(altura_m), 3)
    fallos_cal, _ = validar_calibracion(satelites, leer_obturacion(obturacion), hdop)
    if fallos_cal:
        estado = "RECHAZADO"
    elif gsd >= GSD_MAX_CM_PX:
        estado = "RECHAZADO_GSD"
    else:
        estado = "APROBADO"

    vuelo = Vuelo(
        parcela_id=parcela_id,
        fecha=fecha,
        altura_m=float(altura_m),
        gsd_cm_px=gsd,
        solape_frontal=float(solape_frontal),
        solape_lateral=float(solape_lateral),
        velocidad_ms=float(velocidad_ms),
        satelites=int(satelites),
        hdop=float(hdop),
        obturacion=str(obturacion),
        estado=estado,
        notas=notas,
    )
    session.add(vuelo)
    session.commit()
    session.refresh(vuelo)
    return vuelo


def importar_ground_truth_csv(
    session,
    parcela_id: int,
    ruta_csv: str,
    fecha: str = "2026-10-22",
    responsable: str = "Equipo Campo UCaldas",
):
    # BD-05: carga planilla_conteo.csv sin duplicar si se repite para (cuadrante, fecha)
    res = leer_planilla_conteo(ruta_csv)
    cuadrantes = {
        c.codigo: c
        for c in session.query(Cuadrante).filter(Cuadrante.parcela_id == parcela_id).all()
    }
    registros = []
    for fila in res["detalle"]:
        cod = fila["cuadrante"]
        q_obj = cuadrantes.get(cod)
        if q_obj is None:
            raise ValueError(f"Cuadrante {cod} no existe en parcela_id={parcela_id}")
        gt = (
            session.query(GroundTruth)
            .filter(GroundTruth.cuadrante_id == q_obj.id, GroundTruth.fecha == fecha)
            .first()
        )
        if gt is None:
            gt = GroundTruth(
                cuadrante_id=q_obj.id,
                fecha=fecha,
                contadas=int(fila["conteo"]),
                responsable=responsable,
            )
            session.add(gt)
        else:
            gt.contadas = int(fila["conteo"])
            gt.responsable = responsable
        registros.append(gt)
    session.commit()
    return registros


def importar_lote_vuelo(
    session,
    vuelo_id: int,
    ruta_qa_csv: str,
    ruta_manifiesto_json: str | None = None,
    carpeta_fotos: str | None = None,
):
    # BD-02 / BD-N4: importa fotos del vuelo en una transaccion atomica
    vuelo = session.get(Vuelo, vuelo_id)
    if vuelo is None:
        raise ValueError(f"No existe vuelo id={vuelo_id}")
    parcela_db = session.get(ParcelaDB, vuelo.parcela_id)
    parcela_geo = Parcela(
        parcela_db.lat_origen,
        parcela_db.lon_origen,
        parcela_db.ancho_m,
        parcela_db.largo_m,
        parcela_db.rumbo_deg,
    )
    cuadrantes = {
        c.codigo: c.id
        for c in session.query(Cuadrante).filter(Cuadrante.parcela_id == parcela_db.id).all()
    }

    manifiesto_por_archivo = {}
    ruta_lote = ""
    if ruta_manifiesto_json and os.path.isfile(ruta_manifiesto_json):
        with open(ruta_manifiesto_json, encoding="utf-8") as fm:
            man = json.load(fm)
        ruta_lote = man.get("ruta_lote", "")
        for item in man.get("archivos", []):
            manifiesto_por_archivo[item["archivo"]] = item

    insertadas = 0
    try:
        with open(ruta_qa_csv, newline="", encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                archivo = fila["archivo"]
                res_txt = fila.get("resolucion", "4000x3000")
                if "x" in res_txt:
                    w_s, h_s = res_txt.split("x", 1)
                    ancho_px, alto_px = int(w_s), int(h_s)
                else:
                    ancho_px, alto_px = 0, 0

                lat = float(fila["lat"]) if fila.get("lat") else None
                lon = float(fila["lon"]) if fila.get("lon") else None
                cuad_id = None
                if lat is not None and lon is not None:
                    cod = asignar_cuadrante(parcela_geo, lat, lon)
                    cuad_id = cuadrantes.get(cod)

                info_man = manifiesto_por_archivo.get(archivo, {})
                ruta_img = (
                    os.path.join(carpeta_fotos, *archivo.split("/"))
                    if carpeta_fotos
                    else os.path.join(ruta_lote, *archivo.split("/"))
                )
                tamano = int(info_man.get("bytes", 0))
                if tamano == 0 and ruta_img and os.path.isfile(ruta_img):
                    tamano = os.path.getsize(ruta_img)

                existente = (
                    session.query(Imagen)
                    .filter(Imagen.vuelo_id == vuelo_id, Imagen.archivo == archivo)
                    .first()
                )
                if existente is None:
                    img = Imagen(
                        vuelo_id=vuelo_id,
                        archivo=archivo,
                        ruta=ruta_img.replace("\\", "/"),
                        md5=info_man.get("md5", ""),
                        bytes=tamano,
                        ancho_px=ancho_px,
                        alto_px=alto_px,
                        nitidez=float(fila.get("nitidez") or 0.0),
                        lat=lat,
                        lon=lon,
                        dictamen=fila["dictamen"],
                        motivo=fila.get("motivo", ""),
                        cuadrante_id=cuad_id,
                    )
                    session.add(img)
                else:
                    existente.ruta = ruta_img.replace("\\", "/")
                    existente.md5 = info_man.get("md5", existente.md5)
                    existente.bytes = tamano or existente.bytes
                    existente.nitidez = float(fila.get("nitidez") or 0.0)
                    existente.lat = lat
                    existente.lon = lon
                    existente.dictamen = fila["dictamen"]
                    existente.motivo = fila.get("motivo", "")
                    existente.cuadrante_id = cuad_id
                insertadas += 1
        session.commit()
    except Exception:
        session.rollback()
        raise

    return insertadas
