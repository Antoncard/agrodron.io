# Asistente conversacional AgroDron entrenado con contexto real del proyecto (Vertex AI Express / OpenRouter / Offline)
import httpx

from src.db.config import obtener_configuracion


def construir_system_prompt(resumen_vuelo: dict | None = None, vista: str = "agro") -> str:
    tono = (
        "Usa un lenguaje llano, practico y cercano para un agricultor en finca (evita jerga tecnica innecesaria; prioriza acciones de resiembra)."
        if vista == "agro"
        else "Usa precision tecnica de fotogrametria, QA optico, BD y vision computacional cuando el usuario pregunte detalles de ingenieria."
    )

    bloque_vivo = "Sin datos vivos de BD en esta consulta; usa los valores oficiales del piloto."
    if resumen_vuelo:
        res = resumen_vuelo.get("resumen", {})
        vuelo = resumen_vuelo.get("vuelo", {})
        modelo = resumen_vuelo.get("modelo") or {}
        metricas = modelo.get("metricas") or {}
        pc = metricas.get("prueba_ciega") or {}
        quads = resumen_vuelo.get("cuadrantes", [])
        q_txt = "; ".join(
            f"{q['codigo']} ({q['orientacion']}): {q['detectadas']} detectadas / {q['esperadas']} esperadas (faltan {q['deficit']}, {q['deficit_pct']} %, semaforo {q['semaforo']})"
            for q in quads
        )
        hist = resumen_vuelo.get("historico_vuelos", [])
        hist_txt = "; ".join(
            f"{h['fecha']} ({h['altura_m']}m, GSD {h['gsd_cm_px']}, {h['estado']}): {h['detectadas']} pl."
            for h in hist
        )
        bloque_vivo = (
            f"ULTIMO VUELO EN BD ({vuelo.get('fecha', '2026-10-22')} · {vuelo.get('altura_m', 25.0)} m AGL · GSD {vuelo.get('gsd_cm_px', 0.938)} cm/px · estado {vuelo.get('estado', 'APROBADO')}):\n"
            f"- Resumen: {res.get('frase_principal', '')} | Ground Truth campo: {res.get('ground_truth', 2352)} | Error vs GT: {res.get('error_vs_gt_pct', 0.04)} % | Semaforo: {res.get('semaforo', 'VERDE')}.\n"
            f"- Cuadrantes: {q_txt}.\n"
            f"- Huecos de resiembra GPX/CSV detectados: {len(resumen_vuelo.get('huecos_resiembra', []))}.\n"
            f"- Modelo IA en BD: {modelo.get('nombre', 'AgroDron-CV')} {modelo.get('version', 'v1.0.0')} ({modelo.get('arquitectura', '')}) F1 prueba ciega={pc.get('f1', 0.9593)}, Precision={pc.get('precision', 0.9949)}, Recall={pc.get('recall', 0.9262)}.\n"
            f"- Historial de vuelos: {hist_txt}."
        )

    return (
        "Eres AgroDron IA, el asistente oficial del proyecto AgroDron (Universidad de Caldas).\n"
        "Responde siempre en espanol, de forma clara, concisa y estrictamente fiel a los datos del proyecto.\n"
        f"{tono}\n\n"
        "CONOCIMIENTO DEL PROYECTO AGRODRON:\n"
        "1. Parcela piloto: Finca El Mirador, Vereda La Cabana (Manizales, Caldas, 1.417 msnm, 5.0949, -75.5891), 1,0 ha (100x100 m), 4 cuadrantes de 50x50 m (Q1 NO, Q2 NE, Q3 SE, Q4 SO), 2.500 sitios esperados (625 por cuadrante).\n"
        "2. Epica 1 (Captura de campo y QA): Calibracion GNSS CA1 (>=16 satelites, obturacion <=1/1000 s, HDOP <=1.0; bitacora oficial 18 sat, HDOP 0.68). Hallazgo H1: vuelo previo a 30 m dio GSD 1,125 cm/px (160 fotos, incumple CA3 <1,0 cm/px); vuelo oficial a 25 m da GSD 0,938 cm/px, 12 lineas x 19 fotos = 228 fotos, solape 80/75 %, disparo 1,25 s y 100 % cobertura (CA2). QA optico CA4: Laplaciano >=120, 4000x3000 px, EXIF GPS (220 aceptadas / 8 borrosas descartadas). Ground Truth CA5: 2.352 plantas vivas (Q1:598, Q2:584, Q3:579, Q4:591; deficit real -148 / -5,92 %).\n"
        "3. Epica 2 (Infraestructura): Almacenamiento local raw/<finca>/<lote>/<fecha>/ con verificacion MD5 y manifiesto.json, worker automatico en Python para ingesta e inferencia, arquitectura neutral compatible con RDS/AWS del SOW.\n"
        "4. Epica 3 (IA y Vision): Dataset de 384 recortes 640x640 px particionado por foto completa (70/15/15) con clases planta y maleza; tiling 640x640 con 20 % de solape (48 tiles/foto), NMS intra-foto, georreferenciacion y fusion entre fotos (margen 0,05 m, radio 0,6 m). Semaforo: total <=5 % verde / <=10 % amarillo / >10 % rojo; cuadrante <=10 % verde / <=15 % amarillo / >15 % rojo.\n"
        "5. Epica 4 (Visualizacion y Reportes): Base de datos SQLAlchemy 2 + Alembic (11 tablas), API REST FastAPI (/api/v1) protegida con x-api-key, mapa de densidad 10x10 m, exportacion GPX/CSV de huecos para resiembra, y reporte PDF de 1 pagina.\n\n"
        f"{bloque_vivo}\n"
        "Si te preguntan algo fuera de los datos mostrados, dilo con honestidad sin inventar cifras de campo."
    )


def responder_local_agrodron(mensaje: str, resumen_vuelo: dict | None = None, vista: str = "agro") -> str:
    txt = (mensaje or "").lower()
    res = (resumen_vuelo or {}).get("resumen") or {
        "esperadas": 2500,
        "detectadas": 2351,
        "ground_truth": 2352,
        "deficit": 149,
        "deficit_pct": 5.96,
        "error_vs_gt_pct": 0.04,
        "semaforo": "VERDE",
    }
    quads = (resumen_vuelo or {}).get("cuadrantes") or [
        {"codigo": "Q1", "orientacion": "NO", "esperadas": 625, "detectadas": 598, "deficit": 27, "deficit_pct": 4.32, "semaforo": "VERDE"},
        {"codigo": "Q2", "orientacion": "NE", "esperadas": 625, "detectadas": 584, "deficit": 41, "deficit_pct": 6.56, "semaforo": "VERDE"},
        {"codigo": "Q3", "orientacion": "SE", "esperadas": 625, "detectadas": 579, "deficit": 46, "deficit_pct": 7.36, "semaforo": "VERDE"},
        {"codigo": "Q4", "orientacion": "SO", "esperadas": 625, "detectadas": 590, "deficit": 35, "deficit_pct": 5.60, "semaforo": "VERDE"},
    ]
    peor = max(quads, key=lambda q: q["deficit"])
    n_huecos = len((resumen_vuelo or {}).get("huecos_resiembra") or []) or res["deficit"]

    if any(k in txt for k in ("hola", "buenos", "buenas", "saludos", "hey")):
        return (
            f"¡Hola! Soy AgroDron IA. Estoy revisando el último vuelo de Vereda La Cabaña: "
            f"tenemos {res['detectadas']} plantas estimadas de {res['esperadas']} esperadas (déficit de {res['deficit']}, {res['deficit_pct']} %), "
            f"con mayor prioridad de resiembra en {peor['codigo']} ({peor['orientacion']}). ¿Qué te gustaría consultar?"
        )
    if any(k in txt for k in ("gracias", "excelente", "perfecto", "genial")):
        return "Con mucho gusto. Si necesitas exportar el GPX de resiembra o revisar otro cuadrante, dímelo."
    if any(k in txt for k in ("ayuda", "puedes", "hacer", "preguntar")):
        return (
            "Puedo explicarte dónde faltan más plantas (Q1–Q4), por qué el vuelo oficial se hace a 25 m en vez de 30 m, "
            "cómo usar el archivo GPX/CSV de resiembra, o las métricas del modelo AgroDron-CV v1.0.0."
        )
    if any(k in txt for k in ("falt", "deficit", "déficit", "cuadrante", "peor", "q1", "q2", "q3", "q4")):
        detalle = " · ".join(f"{q['codigo']} ({q['orientacion']}): faltan {q['deficit']}" for q in quads)
        return (
            f"En la parcela de 1,0 ha hay {res['detectadas']} plantas estimadas de {res['esperadas']} esperadas "
            f"(déficit total de {res['deficit']} plantas, {res['deficit_pct']} %). "
            f"El cuadrante más afectado es {peor['codigo']} ({peor['orientacion']}) donde faltan {peor['deficit']} plantas ({peor['deficit_pct']} %). "
            f"Detalle: {detalle}."
        )
    if any(k in txt for k in ("25", "30", "altura", "gsd", "hallazgo", "solape")):
        return (
            "A 30 m el GSD es 1,125 cm/px (160 fotos), lo que incumple la meta CA3 (< 1,0 cm/px) y pierde detalle foliar. "
            "Al bajar a 25 m se obtiene GSD de 0,938 cm/px, malla de 12 líneas × 19 fotos (228 fotos), disparo cada 1,25 s y 100 % de cobertura."
        )
    if any(k in txt for k in ("gpx", "csv", "resiembr", "hueco", "mapa")):
        return (
            f"Se identificaron {n_huecos} sitios sin planta respecto a la malla 50×50. "
            "Desde el botón 'Exportar Huecos Resiembra (.GPX)' o '(.CSV)' descargas las coordenadas GPS exactas para abrirlas en el celular en campo y dirigir la resiembra en "
            f"{peor['codigo']} ({peor['orientacion']})."
        )
    if any(k in txt for k in ("modelo", "ia", "yolo", "f1", "precision", "precisión", "error")):
        return (
            f"El modelo AgroDron-CV v1.0.0 procesa mosaicos de 640×640 px con 20 % de solape (48 tiles/foto), NMS y fusión a 0,6 m. "
            f"En prueba ciega logró F1 = 0,9593 (Precisión 0,9949, Recall 0,9262) y en parcela completa {res['detectadas']} vs {res['ground_truth']} en campo "
            f"(error {res['error_vs_gt_pct']} %, semáforo {res['semaforo']})."
        )
    if any(k in txt for k in ("qa", "borrosa", "laplac", "calibr", "satel")):
        return (
            "La bitácora oficial cumple CA1 (18 satélites >= 16, obturación 1/1000 s, HDOP 0,68 <= 1,0). "
            "En QA óptico (CA4) se validan 4000×3000 px, EXIF GPS y nitidez Laplaciana >= 120 (220 aceptadas y 8 borrosas descartadas)."
        )
    return (
        f"Resumen AgroDron (Vereda La Cabaña · 1,0 ha): {res['detectadas']} plantas detectadas sobre {res['esperadas']} esperadas "
        f"(déficit {res['deficit']} / {res['deficit_pct']} %, semáforo {res['semaforo']}). "
        f"Prioridad de resiembra en {peor['codigo']} ({peor['orientacion']}) con {peor['deficit']} faltantes. "
        "Puedes preguntarme sobre cuadrantes, altura 25 m vs 30 m, archivo GPX de resiembra o métricas del modelo IA."
    )


def _llamar_vertex_express(api_key: str, modelo: str, system_prompt: str, historial: list, mensaje: str) -> str:
    url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{modelo}:generateContent?key={api_key}"
    contents = []
    for turno in historial or []:
        rol = "model" if turno.get("role") == "assistant" else "user"
        txt = str(turno.get("content", "")).strip()
        if txt:
            contents.append({"role": rol, "parts": [{"text": txt}]})
    contents.append({"role": "user", "parts": [{"text": mensaje}]})

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 650},
    }
    headers = {"Content-Type": "application/json"}
    with httpx.Client(timeout=18.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    cands = data.get("candidates") or []
    if not cands:
        raise ValueError("Respuesta vacia de Vertex AI Express")
    parts = ((cands[0].get("content") or {}).get("parts")) or []
    texto = "".join(str(p.get("text", "")) for p in parts).strip()
    if not texto:
        raise ValueError("Sin texto en respuesta de Vertex AI Express")
    return texto


def _llamar_openrouter(api_key: str, modelo: str, system_prompt: str, historial: list, mensaje: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    messages = [{"role": "system", "content": system_prompt}]
    for turno in historial or []:
        rol = "assistant" if turno.get("role") == "assistant" else "user"
        txt = str(turno.get("content", "")).strip()
        if txt:
            messages.append({"role": rol, "content": txt})
    messages.append({"role": "user", "content": mensaje})

    payload = {
        "model": modelo,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 650,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://agrodron.io",
        "X-Title": "AgroDron",
    }
    with httpx.Client(timeout=18.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("Respuesta vacia de OpenRouter")
    texto = str(((choices[0].get("message") or {}).get("content")) or "").strip()
    if not texto:
        raise ValueError("Sin texto en respuesta de OpenRouter")
    return texto


def _resumir_error_llm(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__


def consultar_asistente(
    mensaje: str,
    historial: list | None = None,
    resumen_vuelo: dict | None = None,
    vista: str = "agro",
    permitir_externo: bool = True,
) -> dict:
    cfg = obtener_configuracion()
    system_prompt = construir_system_prompt(resumen_vuelo, vista=vista)
    hist_lim = (historial or [])[-10:]
    motivos = []

    if permitir_externo and cfg.vertex_api_key:
        modelos_vx = []
        for mv in (cfg.llm_model_vertex, "gemini-2.0-flash", "gemini-1.5-flash"):
            if mv and mv not in modelos_vx:
                modelos_vx.append(mv)
        for modelo_vx in modelos_vx:
            try:
                txt = _llamar_vertex_express(
                    cfg.vertex_api_key,
                    modelo_vx,
                    system_prompt,
                    hist_lim,
                    mensaje,
                )
                return {"respuesta": txt, "proveedor": "vertex", "modelo": modelo_vx}
            except Exception as exc:
                motivos.append(f"vertex({modelo_vx}): {_resumir_error_llm(exc)}")

    if permitir_externo and cfg.openrouter_api_key:
        modelos_or = []
        for m in (cfg.llm_model_openrouter, "openrouter/free", "openrouter/auto"):
            if m and m not in modelos_or:
                modelos_or.append(m)
        for modelo_or in modelos_or:
            try:
                txt = _llamar_openrouter(
                    cfg.openrouter_api_key,
                    modelo_or,
                    system_prompt,
                    hist_lim,
                    mensaje,
                )
                return {"respuesta": txt, "proveedor": "openrouter", "modelo": modelo_or}
            except Exception as exc:
                motivos.append(f"openrouter({modelo_or}): {_resumir_error_llm(exc)}")

    res_out = {
        "respuesta": responder_local_agrodron(mensaje, resumen_vuelo, vista=vista),
        "proveedor": "local-offline",
        "modelo": "agrodron-reglas-v1",
    }
    if motivos:
        res_out["motivo_fallback"] = "; ".join(motivos)
    return res_out
