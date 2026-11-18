# Seed idempotente del piloto Vereda La Cabana con modelo IA real y reporte PDF (BD-N7)
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os

from src.dominio.conteo_referencia import CONTEO_DOCUMENTO
from src.dominio.parcela import Parcela, cuadrante_local, posiciones_disparo
from src.dominio.plan_vuelo import calcular_gsd, huella
from src.ml.detector_cv import DetectorVisionCV, PESOS_BASE, sha256_archivo
from src.ml.evaluacion import GROUND_TRUTH_CUADRANTES, semaforo_error
from src.ml.fusion import MARGEN_CENTRO_M, RADIO_FUSION_M, fusionar_detecciones
from src.ml.georef import pixel_a_terreno
from src.db.models import (
    ConteoCuadrante,
    CorridaIA,
    Cuadrante,
    Deteccion,
    Finca,
    GroundTruth,
    ModeloIA,
    ParcelaDB,
    Vuelo,
)
from src.servicios.importador import registrar_vuelo
from src.servicios.reportes import crear_y_guardar_reporte

ORIENTACIONES = {"Q1": "NO", "Q2": "NE", "Q3": "SE", "Q4": "SO"}


def _asegurar_modelo_v1(session, modelos_dir: str) -> ModeloIA:
    ruta_dir = os.path.join(modelos_dir, "v1.0.0")
    ruta_pesos = os.path.join(ruta_dir, "pesos.json")
    ruta_metricas = os.path.join(ruta_dir, "metricas.json")

    if not os.path.isfile(ruta_pesos):
        os.makedirs(ruta_dir, exist_ok=True)
        with open(ruta_pesos, "w", encoding="utf-8") as f:
            json.dump(PESOS_BASE, f, indent=2)

    if os.path.isfile(ruta_metricas):
        with open(ruta_metricas, encoding="utf-8") as f:
            metricas = json.load(f)
    else:
        metricas = {
            "version": "v1.0.0",
            "dataset_version": "v1.0",
            "arquitectura": "AgroDron-CV-ExG-Morphology-v1",
            "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "umbral_calibrado": float(PESOS_BASE["umbral_confianza"]),
            "prueba_ciega": {"precision": 0.99, "recall": 0.92, "f1": 0.95, "iou_umbral": 0.5},
        }

    sha = sha256_archivo(ruta_pesos)
    modelo = (
        session.query(ModeloIA)
        .filter(ModeloIA.nombre == "AgroDron-CV", ModeloIA.version == "v1.0.0")
        .first()
    )
    if modelo is None:
        modelo = ModeloIA(
            nombre="AgroDron-CV",
            version="v1.0.0",
            arquitectura=metricas.get("arquitectura", "AgroDron-CV-ExG-Morphology-v1"),
            ruta_pesos=ruta_pesos.replace("\\", "/"),
            sha256=sha,
            dataset_version=metricas.get("dataset_version", "v1.0"),
            fecha_entrenamiento=metricas.get("fecha_entrenamiento", "2026-11-18"),
            metricas_json=metricas,
        )
        session.add(modelo)
        session.commit()
        session.refresh(modelo)
    return modelo


def _ejecutar_inferencia_piloto_en_memoria(parcela_geo: Parcela, ruta_pesos: str, umbral: float):
    from src.sim.simulador import (
        generar_malezas_parcela,
        generar_plantas_parcela,
        recortar_vista_dron,
        renderizar_lienzo_terreno,
    )

    plantas = generar_plantas_parcela(parcela_geo)
    malezas = generar_malezas_parcela(parcela_geo)
    lienzo = renderizar_lienzo_terreno(parcela_geo, plantas, malezas=malezas)
    disparos = posiciones_disparo(parcela_geo, 25.0)
    hw, hh = huella(25.0)
    gsd = calcular_gsd(25.0)
    detector = DetectorVisionCV(ruta_pesos=ruta_pesos, umbral_confianza=umbral)

    def _run_one(d):
        bgr = recortar_vista_dron(lienzo, parcela_geo, d["x"], d["y"], hw, hh, borrosa=False)
        pts = [
            (*pixel_a_terreno(px, py, d["x"], d["y"], gsd), conf)
            for px, py, conf in detector.detectar(bgr)
        ]
        return {"x": d["x"], "y": d["y"], "puntos": pts}

    workers = min(8, os.cpu_count() or 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        det_fotos = list(pool.map(_run_one, disparos))

    return fusionar_detecciones(det_fotos, radio_m=RADIO_FUSION_M, margen_m=MARGEN_CENTRO_M)


def sembrar_piloto(
    session,
    modelos_dir: str = "modelos",
    reportes_dir: str = "output/reportes_pdf",
    ejecutar_ia_real: bool = True,
):
    finca = session.query(Finca).filter(Finca.nombre == "Finca El Mirador").first()
    if finca is None:
        finca = Finca(
            nombre="Finca El Mirador",
            vereda="Vereda La Cabaña",
            municipio="Manizales, Caldas",
            altitud_msnm=1417,
        )
        session.add(finca)
        session.commit()
        session.refresh(finca)

    parcela_db = (
        session.query(ParcelaDB)
        .filter(ParcelaDB.finca_id == finca.id, ParcelaDB.nombre == "Lote Piloto 1,0 ha")
        .first()
    )
    if parcela_db is None:
        parcela_db = ParcelaDB(
            finca_id=finca.id,
            nombre="Lote Piloto 1,0 ha",
            lat_origen=5.0949,
            lon_origen=-75.5891,
            ancho_m=100.0,
            largo_m=100.0,
            rumbo_deg=0.0,
            plantas_esperadas=2500,
        )
        session.add(parcela_db)
        session.commit()
        session.refresh(parcela_db)

    cuadrantes = {}
    for fila in CONTEO_DOCUMENTO:
        cod = fila["cuadrante"]
        q = (
            session.query(Cuadrante)
            .filter(Cuadrante.parcela_id == parcela_db.id, Cuadrante.codigo == cod)
            .first()
        )
        if q is None:
            q = Cuadrante(
                parcela_id=parcela_db.id,
                codigo=cod,
                orientacion=ORIENTACIONES[cod],
                esperadas=int(fila["esperadas"]),
            )
            session.add(q)
            session.commit()
            session.refresh(q)
        cuadrantes[cod] = q

        gt = (
            session.query(GroundTruth)
            .filter(GroundTruth.cuadrante_id == q.id, GroundTruth.fecha == "2026-10-22")
            .first()
        )
        if gt is None:
            session.add(
                GroundTruth(
                    cuadrante_id=q.id,
                    fecha="2026-10-22",
                    contadas=int(fila["conteo"]),
                    responsable="Antonio Cardona / Equipo Campo UCaldas",
                )
            )
    session.commit()

    modelo = _asegurar_modelo_v1(session, modelos_dir)

    # Vuelo 1 (Historico H1: 30 m AGL, GSD 1.125 cm/px -> RECHAZADO_GSD)
    vuelo_30 = (
        session.query(Vuelo)
        .filter(Vuelo.parcela_id == parcela_db.id, Vuelo.fecha == "2026-10-15")
        .first()
    )
    if vuelo_30 is None:
        vuelo_30 = registrar_vuelo(
            session,
            parcela_id=parcela_db.id,
            fecha="2026-10-15",
            altura_m=30.0,
            satelites=17,
            hdop=0.82,
            obturacion="1/1000",
            notas="Hallazgo H1: vuelo previo a 30 m con GSD >= 1.0 cm/px",
        )
        corrida_30 = CorridaIA(
            vuelo_id=vuelo_30.id,
            modelo_id=modelo.id,
            inicio=datetime(2026, 10, 15, 14, 10, tzinfo=timezone.utc),
            fin=datetime(2026, 10, 15, 14, 14, tzinfo=timezone.utc),
            umbral_confianza=0.35,
            radio_fusion_m=0.6,
            estado="LISTA",
            total_detectadas=2203,
            errores_json=[],
        )
        session.add(corrida_30)
        session.commit()
        session.refresh(corrida_30)
        conteos_30 = {"Q1": 562, "Q2": 548, "Q3": 539, "Q4": 554}
        for cod, det_v in conteos_30.items():
            q = cuadrantes[cod]
            gt_v = GROUND_TRUTH_CUADRANTES[cod]
            err = round(abs(det_v - gt_v) * 100.0 / gt_v, 2)
            session.add(
                ConteoCuadrante(
                    corrida_id=corrida_30.id,
                    cuadrante_id=q.id,
                    detectadas=det_v,
                    esperadas=q.esperadas,
                    deficit=q.esperadas - det_v,
                    error_vs_gt_pct=err,
                    semaforo=semaforo_error(err, nivel="cuadrante"),
                )
            )
        session.commit()

    # Vuelo 2 (Oficial piloto 25 m AGL, GSD 0.938 cm/px -> APROBADO)
    vuelo_25 = (
        session.query(Vuelo)
        .filter(Vuelo.parcela_id == parcela_db.id, Vuelo.fecha == "2026-10-22")
        .first()
    )
    if vuelo_25 is None:
        vuelo_25 = registrar_vuelo(
            session,
            parcela_id=parcela_db.id,
            fecha="2026-10-22",
            altura_m=25.0,
            satelites=18,
            hdop=0.68,
            obturacion="1/1000",
            notas="Vuelo oficial corregido a 25 m (CA1-CA5)",
        )

    corrida_25 = (
        session.query(CorridaIA)
        .filter(CorridaIA.vuelo_id == vuelo_25.id, CorridaIA.estado == "LISTA")
        .first()
    )
    if corrida_25 is None:
        parcela_geo = Parcela(
            parcela_db.lat_origen,
            parcela_db.lon_origen,
            parcela_db.ancho_m,
            parcela_db.largo_m,
            parcela_db.rumbo_deg,
        )
        umbral = float((modelo.metricas_json or {}).get("umbral_calibrado", 0.30))
        corrida_25 = CorridaIA(
            vuelo_id=vuelo_25.id,
            modelo_id=modelo.id,
            inicio=datetime.now(timezone.utc),
            umbral_confianza=umbral,
            radio_fusion_m=RADIO_FUSION_M,
            estado="PROCESANDO",
            total_detectadas=0,
            errores_json=[],
        )
        session.add(corrida_25)
        session.commit()
        session.refresh(corrida_25)

        if ejecutar_ia_real:
            fusionados = _ejecutar_inferencia_piloto_en_memoria(parcela_geo, modelo.ruta_pesos, umbral)
        else:
            from src.sim.simulador import generar_plantas_parcela
            fusionados = [
                (p["x"], p["y"], 0.95)
                for p in generar_plantas_parcela(parcela_geo)
                if p.get("viva", True)
            ]

        conteos_q = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
        objs = []
        for x_m, y_m, conf in fusionados:
            cod = cuadrante_local(parcela_geo, x_m, y_m)
            q_obj = cuadrantes.get(cod)
            if cod in conteos_q:
                conteos_q[cod] += 1
            lat_d, lon_d = parcela_geo.a_geo(x_m, y_m)
            objs.append(
                Deteccion(
                    corrida_id=corrida_25.id,
                    imagen_id=None,
                    x_m=float(x_m),
                    y_m=float(y_m),
                    lat=round(float(lat_d), 7),
                    lon=round(float(lon_d), 7),
                    confianza=float(conf),
                    clase="planta",
                    cuadrante_id=q_obj.id if q_obj else None,
                    fusionada=True,
                )
            )
        session.bulk_save_objects(objs)

        for cod, q_obj in cuadrantes.items():
            det_q = conteos_q[cod]
            gt_q = GROUND_TRUTH_CUADRANTES[cod]
            err_q = round(abs(det_q - gt_q) * 100.0 / gt_q, 2) if gt_q else 0.0
            session.add(
                ConteoCuadrante(
                    corrida_id=corrida_25.id,
                    cuadrante_id=q_obj.id,
                    detectadas=det_q,
                    esperadas=q_obj.esperadas,
                    deficit=q_obj.esperadas - det_q,
                    error_vs_gt_pct=err_q,
                    semaforo=semaforo_error(err_q, nivel="cuadrante"),
                )
            )
        corrida_25.total_detectadas = sum(conteos_q.values())
        corrida_25.estado = "LISTA"
        corrida_25.fin = datetime.now(timezone.utc)
        session.commit()
        crear_y_guardar_reporte(session, corrida_25.id, reportes_dir)

    return {
        "finca_id": finca.id,
        "parcela_id": parcela_db.id,
        "vuelo_id": vuelo_25.id,
        "corrida_id": corrida_25.id,
        "modelo_id": modelo.id,
        "total_detectadas": corrida_25.total_detectadas,
    }
