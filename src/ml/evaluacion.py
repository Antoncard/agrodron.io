# Evaluacion de conteo IA por cuadrante contra el Ground Truth (Epica 3)
from src.dominio.conteo_referencia import CONTEO_DOCUMENTO
from src.dominio.parcela import CUADRANTES, cuadrante_local
from src.dominio.plan_vuelo import calcular_gsd
from src.ml.detector import DetectorSimulado
from src.ml.fusion import fusionar_detecciones
from src.ml.georef import pixel_a_terreno

GROUND_TRUTH_CUADRANTES = {f["cuadrante"]: f["conteo"] for f in CONTEO_DOCUMENTO}
TOTAL_GROUND_TRUTH = sum(GROUND_TRUTH_CUADRANTES.values())  # 2352 plantas


def semaforo_error(error_pct):
    # Umbrales provisionales (los define el Product Owner): <= 5% verde, <= 10% amarillo, > 10% rojo
    val = abs(float(error_pct))
    if val <= 5.0:
        return "VERDE"
    if val <= 10.0:
        return "AMARILLO"
    return "ROJO"


def evaluar_conteo_ia(puntos_terreno, parcela, ground_truth=None):
    # Cuenta plantas fusionadas por cuadrante y calcula % de error frente al ground truth
    gt_map = ground_truth or GROUND_TRUTH_CUADRANTES
    conteo_q = {q: 0 for q in CUADRANTES.values()}
    fuera = 0
    for pt in puntos_terreno:
        x, y = float(pt[0]), float(pt[1])
        q = cuadrante_local(parcela, x, y)
        if q in conteo_q:
            conteo_q[q] += 1
        else:
            fuera += 1

    detalle = []
    total_gt, total_det = 0, 0
    for q in ("Q1", "Q2", "Q3", "Q4"):
        gt = int(gt_map[q])
        det = conteo_q[q]
        dif = det - gt
        err = round(abs(dif) * 100.0 / gt, 2) if gt > 0 else 0.0
        desv = round(dif * 100.0 / gt, 2) if gt > 0 else 0.0
        detalle.append({
            "cuadrante": q,
            "ground_truth": gt,
            "detectadas": det,
            "diferencia": dif,
            "error_pct": err,
            "desviacion_pct": desv,
            "semaforo": semaforo_error(err),
        })
        total_gt += gt
        total_det += det

    dif_total = total_det - total_gt
    err_total = round(abs(dif_total) * 100.0 / total_gt, 2) if total_gt > 0 else 0.0
    desv_total = round(dif_total * 100.0 / total_gt, 2) if total_gt > 0 else 0.0
    return {
        "detalle": detalle,
        "ground_truth": total_gt,
        "detectadas": total_det,
        "diferencia": dif_total,
        "error_pct": err_total,
        "desviacion_pct": desv_total,
        "semaforo": semaforo_error(err_total),
        "fuera": fuera,
    }


def ejecutar_conteo_simulado(parcela, plantas, disparos, altura_m=25.0, ruido_px=0.0):
    # Ejecuta DetectorSimulado + georef + fusion + evaluacion sobre los disparos del vuelo
    detector = DetectorSimulado(plantas=plantas, altura_m=altura_m, ruido_px=ruido_px)
    gsd = calcular_gsd(altura_m)
    detecciones_por_foto = []
    for d in disparos:
        if d.get("dictamen", "ACEPTADA") != "ACEPTADA":
            continue
        dets_px = detector.detectar(d)
        pts_m = [
            (*pixel_a_terreno(px, py, d["x"], d["y"], gsd), conf)
            for px, py, conf in dets_px
        ]
        detecciones_por_foto.append({"x": d["x"], "y": d["y"], "puntos": pts_m})

    fusionados = fusionar_detecciones(detecciones_por_foto)
    res = evaluar_conteo_ia(fusionados, parcela)
    res["puntos_fusionados"] = len(fusionados)
    return res

