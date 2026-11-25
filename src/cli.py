# Interfaz de linea de comandos (CLI) de AgroDron (< 300 lineas)
import argparse
import json
import os
import sys

from src.almacen import contar_estados, copiar_lote, crear_manifiesto, guardar_manifiesto
from src.dominio.conteo_referencia import leer_planilla_conteo
from src.dominio.parcela import (
    Parcela, escribir_kml, escribir_waypoints_csv, evaluar_cobertura, generar_ruta, posiciones_disparo,
)
from src.dominio.plan_vuelo import (
    GSD_MAX_CM_PX, altura_maxima, altura_recomendada, calcular_plan_vuelo, leer_obturacion, validar_calibracion,
)
from src.dominio.qa_fotos import auditar_lote, leer_aceptadas
from src.ml.evaluacion import ejecutar_conteo_simulado
from src.sim.simulador import LAT_CABANA, LON_CABANA, RUMBO_VIENTO_NE, generar_plantas_parcela


def parcela_desde_args(args):
    return Parcela(args.lat, args.lon, args.ancho, args.largo, args.rumbo)


def imprimir(datos, como_json=False):
    if como_json:
        print(json.dumps(datos, ensure_ascii=False, indent=2))
    else:
        for k, v in datos.items():
            print(f"{k}: {v}")


def cmd_calibracion(args):
    fallos, advertencias = validar_calibracion(args.satelites, leer_obturacion(args.obturacion), args.hdop)
    for a in advertencias:
        print(f"ADVERTENCIA {a}")
    for f in fallos:
        print(f"FALLA {f}")
    print("CA1: CUMPLE" if not fallos else "CA1: NO CUMPLE, recalibrar antes de volar")
    return 1 if fallos else 0


def cmd_plan(args):
    altura = altura_recomendada() if args.altura is None else args.altura
    plan = calcular_plan_vuelo(
        ancho_m=args.ancho, largo_m=args.largo, altura_m=altura,
        solape_frontal=args.solape_frontal, solape_lateral=args.solape_lateral,
        velocidad_ms=args.velocidad, autonomia_min=args.autonomia,
    )
    imprimir(plan, args.json)
    if args.json:
        return 0 if plan["cumple_gsd"] else 1
    print(f"altura maxima para GSD < {GSD_MAX_CM_PX}: {altura_maxima():.2f} m (recomendada: {altura_recomendada()} m)")
    if not plan["cumple_gsd"]:
        print(f"ADVERTENCIA: el GSD no cumple el requisito, baja la altura a {altura_recomendada()} m o menos")
        return 1
    return 0


def cmd_conteo(args):
    r = leer_planilla_conteo(args.planilla)
    if args.json:
        imprimir(r, True)
        return 0
    print(f"{'cuadrante':<12}{'esperadas':>10}{'conteo':>8}{'dif':>7}{'%':>8}")
    for d in r["detalle"]:
        print(f"{d['cuadrante']:<12}{d['esperadas']:>10}{d['conteo']:>8}{d['diferencia']:>7}{d['porcentaje']:>8}")
    print(f"{'TOTAL':<12}{r['esperadas']:>10}{r['conteo']:>8}{r['diferencia']:>7}{r['porcentaje']:>8}")
    return 0


def cmd_contar(args):
    parcela = Parcela(args.lat, args.lon, args.ancho, args.largo, args.rumbo)
    plantas = generar_plantas_parcela(parcela)
    disparos = posiciones_disparo(parcela, args.altura)
    r = ejecutar_conteo_simulado(parcela, plantas, disparos, altura_m=args.altura, ruido_px=args.ruido_px)
    if args.json:
        imprimir(r, True)
        return 0
    print(f"{'cuadrante':<10}{'ground_truth':>14}{'detectadas':>12}{'dif':>7}{'error_%':>10}{'semaforo':>10}")
    for d in r["detalle"]:
        print(f"{d['cuadrante']:<10}{d['ground_truth']:>14}{d['detectadas']:>12}{d['diferencia']:>7}{d['error_pct']:>9.2f}%{d['semaforo']:>10}")
    print(f"{'TOTAL':<10}{r['ground_truth']:>14}{r['detectadas']:>12}{r['diferencia']:>7}{r['error_pct']:>9.2f}%{r['semaforo']:>10}")
    return 0


def cmd_qa(args):
    r = auditar_lote(args.carpeta, args.reporte, args.recursivo, args.hilos)
    if "error" in r:
        print(r["error"], file=sys.stderr)
        return 2
    if args.json:
        imprimir(r, True)
        return 0
    print(f"extraidas: {r['extraidas']}  aceptadas: {r['aceptadas']}  descartadas: {r['descartadas']}  nitidez promedio: {r['nitidez_promedio_aceptadas']}")
    for grupo, g in r["por_grupo"].items():
        print(f"  {grupo}: {g['aceptadas']} aceptadas / {g['descartadas']} descartadas")
    for nombre, motivo in r["detalle"]:
        print(f"  RECHAZADA {nombre}: {motivo}")
    print(f"reporte: {r['reporte']}")
    return 0


def cmd_guardar(args):
    solo = leer_aceptadas(args.solo_aceptadas) if args.solo_aceptadas else None
    resultados = copiar_lote(
        args.carpeta, args.destino, args.finca, args.lote, args.fecha,
        solo=solo, recursivo=args.recursivo, hilos=args.hilos,
    )
    for r in resultados:
        if r["estado"] == "ERROR":
            print(f"ERROR {r['archivo']}: {r['error']}", file=sys.stderr)
    print(contar_estados(resultados))
    manifiesto = crear_manifiesto(resultados, args.finca, args.lote, args.fecha)
    ruta_m = args.manifiesto or os.path.join(args.destino, "raw", args.finca, args.lote, args.fecha, "manifiesto.json")
    guardar_manifiesto(ruta_m, manifiesto)
    print(f"manifiesto local: {ruta_m}")
    return 1 if any(r["estado"] == "ERROR" for r in resultados) else 0


def cmd_subir(args):
    print("AVISO: el subcomando 'subir' esta en desuso; usa 'guardar'", file=sys.stderr)
    return cmd_guardar(args)


def cmd_ruta(args):
    parcela = parcela_desde_args(args)
    altura = altura_recomendada() if args.altura is None else args.altura
    plan = calcular_plan_vuelo(parcela.ancho_m, parcela.largo_m, altura, args.solape_frontal, args.solape_lateral, args.velocidad)
    puntos = generar_ruta(parcela, altura, args.solape_lateral)
    escribir_kml(args.salida, puntos, parcela, args.velocidad, plan["intervalo_disparo_s"])
    ruta_csv = os.path.splitext(args.salida)[0] + "_waypoints.csv"
    escribir_waypoints_csv(ruta_csv, puntos, args.velocidad)
    print(f"{len(puntos)} waypoints en {plan['lineas']} lineas a {altura} m (GSD {plan['gsd_cm_px']} cm/px, disparo cada {plan['intervalo_disparo_s']} s)")
    print(f"KML: {args.salida}\nCSV: {ruta_csv}")
    if not plan["cumple_gsd"]:
        print("ADVERTENCIA: a esta altura el GSD no cumple el requisito")
        return 1
    return 0


def cmd_cobertura(args):
    altura = altura_recomendada() if args.altura is None else args.altura
    r = evaluar_cobertura(args.reporte, parcela_desde_args(args), altura)
    if args.json:
        imprimir(r, True)
    else:
        print(f"fotos aceptadas con GPS: {r['fotos_usadas']}  (sin coordenadas: {r['sin_coordenadas']})")
        for q, n in r["por_cuadrante"].items():
            print(f"  {q}: {n}")
        print(f"cobertura de la parcela: {r['cobertura_pct']} %")
        print("CA2 cobertura: CUMPLE" if r["cumple_cobertura"] else "CA2 cobertura: NO CUMPLE, hay zonas sin fotos aceptadas")
    return 0 if r["cumple_cobertura"] else 1


def cmd_flujo(args):
    r = auditar_lote(args.carpeta, args.reporte, args.recursivo, args.hilos)
    if "error" in r:
        print(r["error"], file=sys.stderr)
        return 2
    print(f"QA: {r['aceptadas']} aceptadas / {r['descartadas']} descartadas")
    args.solo_aceptadas = args.reporte
    return cmd_guardar(args)


def cmd_demo(args):
    from src.sim import simulador as sim
    bitacora = {}
    if getattr(args, "bitacora", None):
        with open(args.bitacora, encoding="utf-8") as f:
            bitacora.update(json.load(f))
    for campo in ("fecha", "satelites", "obturacion", "hdop", "finca", "lote"):
        val = getattr(args, campo, None)
        if val is not None:
            bitacora[campo] = val
    res = sim.ejecutar_simulacion(
        carpeta_salida=args.carpeta, total_fotos=args.fotos, descartadas=args.descartadas,
        altura_m=args.altura, lat=args.lat, lon=args.lon, rumbo=args.rumbo,
        abrir_navegador=not args.no_abrir, bitacora=bitacora or None,
    )
    nota_muestra = " (muestra)" if res.get("es_muestra") else ""
    print(f"Simulacion completada en: {res['carpeta_salida']}")
    print(f"  Fotos generadas: {res['fotos_generadas']}{nota_muestra} ({res['aceptadas']} aceptadas / {res['descartadas']} descartadas)")
    print(f"  Cobertura parcela: {res['cobertura_pct']} %")
    print(f"  Fotos guardadas en almacen: {res['guardadas']}")
    print(f"  Panel interactivo (mapa + dron): {res['panel_html']}")
    return 0


def cmd_db_init(args):
    from alembic import command as alembic_cmd
    from alembic.config import Config
    from src.db.config import obtener_configuracion
    from src.db.session import create_session_factory
    from src.servicios.seed import sembrar_piloto

    cfg_env = obtener_configuracion()
    alembic_cfg = Config("alembic.ini")
    if args.url:
        alembic_cfg.set_main_option("sqlalchemy.url", args.url)
    alembic_cmd.upgrade(alembic_cfg, "head")
    sf, _ = create_session_factory(args.url or cfg_env.database_url)
    with sf() as session:
        res = sembrar_piloto(
            session,
            modelos_dir=cfg_env.modelos_dir,
            reportes_dir=cfg_env.reportes_dir,
            ejecutar_ia_real=not args.rapido,
        )
    imprimir(res, getattr(args, "json", False))
    return 0


def cmd_importar(args):
    from src.db.config import obtener_configuracion
    from src.db.session import create_session_factory
    from src.servicios.importador import importar_ground_truth_csv, importar_lote_vuelo, registrar_vuelo

    sf, _ = create_session_factory(obtener_configuracion().database_url)
    with sf() as session:
        vuelo = registrar_vuelo(
            session,
            parcela_id=args.parcela_id,
            fecha=args.fecha,
            altura_m=args.altura,
            satelites=args.satelites,
            hdop=args.hdop,
            obturacion=args.obturacion,
        )
        n_imgs = 0
        if args.qa_csv:
            n_imgs = importar_lote_vuelo(session, vuelo.id, args.qa_csv, args.manifiesto, args.carpeta_fotos)
        if args.conteo_csv:
            importar_ground_truth_csv(session, args.parcela_id, args.conteo_csv, fecha=args.fecha)
    print(f"Importado vuelo id={vuelo.id} estado={vuelo.estado} imagenes={n_imgs}")
    return 0


def cmd_api(args):
    import uvicorn
    uvicorn.run("src.api.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def cmd_worker(args):
    from src.worker.servicio import ejecutar_bucle_worker
    ejecutar_bucle_worker(args.intervalo, args.una_vez, args.carpeta_raw, args.parcela_id)
    return 0


def cmd_entrenar(args):
    from ml_training.preparar_dataset import preparar_dataset
    from ml_training.entrenar import entrenar
    if not args.solo_entrenar:
        preparar_dataset(args.dataset)
    res = entrenar(args.config, args.dataset, args.version, args.backend, args.modelos_dir)
    imprimir(res, True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="AgroDron CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("calibracion", help="valida la calibracion del dron (CA1)")
    c.add_argument("--satelites", type=int, required=True)
    c.add_argument("--obturacion", required=True, help="p. ej. 1/1000")
    c.add_argument("--hdop", type=float)
    c.set_defaults(fn=cmd_calibracion)

    p = sub.add_parser("plan", help="calcula el plan de vuelo")
    p.add_argument("--altura", type=float, help="por defecto usa la recomendada (25 m)")
    p.add_argument("--ancho", type=float, default=100.0)
    p.add_argument("--largo", type=float, default=100.0)
    p.add_argument("--solape-frontal", type=float, default=0.80)
    p.add_argument("--solape-lateral", type=float, default=0.75)
    p.add_argument("--velocidad", type=float, default=4.5)
    p.add_argument("--autonomia", type=float, default=15.0)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_plan)

    g = sub.add_parser("conteo", help="compara el conteo en tierra con lo esperado (CA5)")
    g.add_argument("planilla", help="CSV con columnas cuadrante,esperadas,conteo")
    g.add_argument("--json", action="store_true")
    g.set_defaults(fn=cmd_conteo)

    ct = sub.add_parser("contar", help="conteo por cuadrante con IA y % de error (Epica 3)")
    ct.add_argument("--altura", type=float, default=25.0)
    ct.add_argument("--lat", type=float, default=LAT_CABANA)
    ct.add_argument("--lon", type=float, default=LON_CABANA)
    ct.add_argument("--ancho", type=float, default=100.0)
    ct.add_argument("--largo", type=float, default=100.0)
    ct.add_argument("--rumbo", type=float, default=RUMBO_VIENTO_NE)
    ct.add_argument("--ruido-px", type=float, default=0.0)
    ct.add_argument("--json", action="store_true")
    ct.set_defaults(fn=cmd_contar)

    def opciones_qa(x):
        x.add_argument("carpeta")
        x.add_argument("--reporte", default="reporte_qa.csv")
        x.add_argument("--recursivo", action="store_true")
        x.add_argument("--hilos", type=int, default=4)

    def opciones_guardar(x):
        x.add_argument("--destino", default="almacen")
        x.add_argument("--finca", required=True)
        x.add_argument("--lote", required=True)
        x.add_argument("--fecha", required=True)
        x.add_argument("--manifiesto", metavar="JSON")

    def opciones_parcela(x):
        x.add_argument("--lat", type=float, required=True)
        x.add_argument("--lon", type=float, required=True)
        x.add_argument("--ancho", type=float, default=100.0)
        x.add_argument("--largo", type=float, default=100.0)
        x.add_argument("--rumbo", type=float, default=0.0)
        x.add_argument("--altura", type=float)

    r = sub.add_parser("ruta", help="exporta la ruta de vuelo a KML y CSV de waypoints")
    opciones_parcela(r)
    r.add_argument("--solape-frontal", type=float, default=0.80)
    r.add_argument("--solape-lateral", type=float, default=0.75)
    r.add_argument("--velocidad", type=float, default=4.5)
    r.add_argument("--salida", default="ruta_vuelo.kml")
    r.set_defaults(fn=cmd_ruta)

    cb = sub.add_parser("cobertura", help="cuadrantes por GPS y % de la parcela cubierto (CA2)")
    cb.add_argument("reporte")
    opciones_parcela(cb)
    cb.add_argument("--json", action="store_true")
    cb.set_defaults(fn=cmd_cobertura)

    q = sub.add_parser("qa", help="audita las fotos de una carpeta (CA4)")
    opciones_qa(q)
    q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_qa)

    for nombre_cmd, fn_cmd in (("guardar", cmd_guardar), ("subir", cmd_subir)):
        s = sub.add_parser(nombre_cmd)
        s.add_argument("carpeta")
        opciones_guardar(s)
        s.add_argument("--solo-aceptadas", metavar="REPORTE_CSV")
        s.add_argument("--recursivo", action="store_true")
        s.add_argument("--hilos", type=int, default=8)
        s.set_defaults(fn=fn_cmd)

    fl = sub.add_parser("flujo", help="QA y luego guarda solo las aceptadas")
    opciones_qa(fl)
    opciones_guardar(fl)
    fl.set_defaults(fn=cmd_flujo)

    dm = sub.add_parser("demo", help="simula vuelo a 25 m (228 fotos por defecto) y genera panel")
    dm.add_argument("--carpeta", default="output")
    dm.add_argument("--fotos", type=int, default=None, help="por defecto usa el total del plan a 25 m (228); menor genera una muestra")
    dm.add_argument("--descartadas", type=int, default=8)
    dm.add_argument("--altura", type=float, default=25.0)
    dm.add_argument("--lat", type=float, default=LAT_CABANA)
    dm.add_argument("--lon", type=float, default=LON_CABANA)
    dm.add_argument("--rumbo", type=float, default=RUMBO_VIENTO_NE)
    dm.add_argument("--fecha", default=None, help="fecha real de bitacora (AAAA-MM-DD)")
    dm.add_argument("--satelites", type=int, default=None, help="satelites GNSS de bitacora (CA1)")
    dm.add_argument("--obturacion", default=None, help="velocidad de obturacion de bitacora (ej. 1/1000)")
    dm.add_argument("--hdop", type=float, default=None, help="HDOP de bitacora (CA1)")
    dm.add_argument("--finca", default=None, help="slug de la finca")
    dm.add_argument("--lote", default=None, help="slug del lote")
    dm.add_argument("--bitacora", default=None, help="archivo JSON con datos reales de bitacora de vuelo")
    dm.add_argument("--no-abrir", action="store_true")
    dm.set_defaults(fn=cmd_demo)

    dbi = sub.add_parser("db-init", help="aplica migraciones Alembic y siembra el piloto en BD")
    dbi.add_argument("--url", default=None)
    dbi.add_argument("--rapido", action="store_true")
    dbi.add_argument("--json", action="store_true")
    dbi.set_defaults(fn=cmd_db_init)

    imp = sub.add_parser("importar", help="importa QA, manifiesto y ground truth CSV a la BD")
    imp.add_argument("--parcela-id", type=int, default=1)
    imp.add_argument("--fecha", required=True)
    imp.add_argument("--altura", type=float, default=25.0)
    imp.add_argument("--satelites", type=int, default=18)
    imp.add_argument("--hdop", type=float, default=0.68)
    imp.add_argument("--obturacion", default="1/1000")
    imp.add_argument("--qa-csv", default=None)
    imp.add_argument("--manifiesto", default=None)
    imp.add_argument("--carpeta-fotos", default=None)
    imp.add_argument("--conteo-csv", default=None)
    imp.set_defaults(fn=cmd_importar)

    ap_cmd = sub.add_parser("api", help="inicia servidor REST FastAPI (/api/v1)")
    ap_cmd.add_argument("--host", default="127.0.0.1")
    ap_cmd.add_argument("--port", type=int, default=8000)
    ap_cmd.add_argument("--reload", action="store_true")
    ap_cmd.set_defaults(fn=cmd_api)

    wk = sub.add_parser("worker", help="ejecuta servicio de eventos e inferencia IA")
    wk.add_argument("--intervalo", type=float, default=5.0)
    wk.add_argument("--una-vez", action="store_true")
    wk.add_argument("--carpeta-raw", default=None)
    wk.add_argument("--parcela-id", type=int, default=1)
    wk.set_defaults(fn=cmd_worker)

    tr = sub.add_parser("entrenar", help="prepara dataset YOLO y entrena detector")
    tr.add_argument("--config", default="ml_training/config_yolo.yaml")
    tr.add_argument("--dataset", default="dataset/v1")
    tr.add_argument("--version", default="v1.0.0")
    tr.add_argument("--backend", choices=("cv", "yolo"), default="cv")
    tr.add_argument("--modelos-dir", default="modelos")
    tr.add_argument("--solo-entrenar", action="store_true")
    tr.set_defaults(fn=cmd_entrenar)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
