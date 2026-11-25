# API REST FastAPI /api/v1 para AgroDron (Epica 4)
import os

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.api.auth import verificar_api_key
from src.db.config import obtener_configuracion
from src.db.models import CorridaIA, Deteccion, ModeloIA, Reporte, Vuelo
from src.db.session import create_session_factory
from src.ml.pipeline_vuelo import procesar_vuelo_en_bd
from src.servicios.asistente import consultar_asistente
from src.servicios.reportes import (
    crear_y_guardar_reporte,
    exportar_huecos_csv,
    exportar_huecos_gpx,
    obtener_ultimo_vuelo,
)


class ConsultaAsistente(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1500)
    historial: list[dict] = Field(default_factory=list)
    vista: str = Field(default="agro")
    parcela_id: int = Field(default=1)


def crear_app(
    session_factory=None,
    api_key: str | None = None,
    public_dir: str = "public",
    permitir_llm_externo: bool = True,
) -> FastAPI:
    app = FastAPI(
        title="AgroDron API",
        version="1.0.0",
        description="API REST de telemetria, conteo IA y reportes para el productor (Universidad de Caldas)",
    )
    cfg = obtener_configuracion()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cfg.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if session_factory is None:
        session_factory, _ = create_session_factory()
    app.state.session_factory = session_factory
    app.state.api_key = api_key or obtener_configuracion().api_key
    app.state.permitir_llm_externo = permitir_llm_externo

    def _get_session(request: Request):
        db = request.app.state.session_factory()
        try:
            yield db
        finally:
            db.close()

    @app.get("/api/v1/salud")
    def salud(db=Depends(_get_session)):
        db.execute(text("SELECT 1"))
        return {"estado": "ok", "servicio": "agrodron-api", "bd": "conectada"}

    @app.get("/api/v1/parcelas/{parcela_id}/ultimo-vuelo", dependencies=[Depends(verificar_api_key)])
    def api_ultimo_vuelo(parcela_id: int, db=Depends(_get_session)):
        res = obtener_ultimo_vuelo(db, parcela_id)
        if res is None:
            raise HTTPException(status_code=404, detail="Parcela o vuelo no encontrado")
        return res

    @app.get("/api/v1/vuelos/{vuelo_id}/conteo", dependencies=[Depends(verificar_api_key)])
    def api_conteo_vuelo(vuelo_id: int, db=Depends(_get_session)):
        vuelo = db.get(Vuelo, vuelo_id)
        if vuelo is None:
            raise HTTPException(status_code=404, detail="Vuelo no encontrado")
        res = obtener_ultimo_vuelo(db, vuelo.parcela_id, vuelo_id=vuelo.id)
        return {
            "vuelo": res["vuelo"],
            "corrida": res["corrida"],
            "modelo": res["modelo"],
            "resumen": res["resumen"],
            "cuadrantes": res["cuadrantes"],
        }

    @app.get("/api/v1/vuelos/{vuelo_id}/detecciones.geojson", dependencies=[Depends(verificar_api_key)])
    def api_detecciones_geojson(vuelo_id: int, db=Depends(_get_session)):
        vuelo = db.get(Vuelo, vuelo_id)
        if vuelo is None:
            raise HTTPException(status_code=404, detail="Vuelo no encontrado")
        corrida = (
            db.query(CorridaIA)
            .filter(CorridaIA.vuelo_id == vuelo.id, CorridaIA.estado == "LISTA")
            .order_by(CorridaIA.id.desc())
            .first()
        )
        features = []
        if corrida:
            dets = (
                db.query(Deteccion)
                .filter(Deteccion.corrida_id == corrida.id, Deteccion.fusionada.is_(True))
                .all()
            )
            for d in dets:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [d.lon, d.lat]},
                    "properties": {
                        "id": d.id,
                        "clase": d.clase,
                        "confianza": d.confianza,
                        "x_m": d.x_m,
                        "y_m": d.y_m,
                        "cuadrante_id": d.cuadrante_id,
                    },
                })
        return {"type": "FeatureCollection", "features": features}

    @app.post("/api/v1/vuelos/{vuelo_id}/procesar", dependencies=[Depends(verificar_api_key)])
    def api_procesar_vuelo(
        vuelo_id: int,
        background_tasks: BackgroundTasks,
        modelo_id: int | None = None,
        inmediato: bool = False,
        db=Depends(_get_session),
    ):
        vuelo = db.get(Vuelo, vuelo_id)
        if vuelo is None:
            raise HTTPException(status_code=404, detail="Vuelo no encontrado")
        modelo = db.get(ModeloIA, modelo_id) if modelo_id else db.query(ModeloIA).order_by(ModeloIA.id.desc()).first()
        if modelo is None:
            raise HTTPException(status_code=400, detail="No hay modelo_ia registrado en la base de datos")

        corrida = CorridaIA(
            vuelo_id=vuelo.id,
            modelo_id=modelo.id,
            umbral_confianza=float((modelo.metricas_json or {}).get("umbral_calibrado", 0.45)),
            radio_fusion_m=0.6,
            estado="EN_COLA",
            total_detectadas=0,
            errores_json=[],
        )
        db.add(corrida)
        db.commit()
        db.refresh(corrida)

        if inmediato:
            def _run_bg(sf, v_id, c_id):
                s = sf()
                try:
                    procesar_vuelo_en_bd(s, v_id, c_id)
                    crear_y_guardar_reporte(s, c_id, obtener_configuracion().reportes_dir)
                finally:
                    s.close()

            background_tasks.add_task(_run_bg, app.state.session_factory, vuelo.id, corrida.id)

        return {"corrida_id": corrida.id, "vuelo_id": vuelo.id, "modelo_id": modelo.id, "estado": corrida.estado}

    @app.get("/api/v1/corridas/{corrida_id}", dependencies=[Depends(verificar_api_key)])
    def api_estado_corrida(corrida_id: int, db=Depends(_get_session)):
        corrida = db.get(CorridaIA, corrida_id)
        if corrida is None:
            raise HTTPException(status_code=404, detail="Corrida no encontrada")
        return {
            "id": corrida.id,
            "vuelo_id": corrida.vuelo_id,
            "modelo_id": corrida.modelo_id,
            "estado": corrida.estado,
            "inicio": corrida.inicio.isoformat() if corrida.inicio else None,
            "fin": corrida.fin.isoformat() if corrida.fin else None,
            "total_detectadas": corrida.total_detectadas,
            "errores": corrida.errores_json,
        }

    @app.get("/api/v1/reportes/{reporte_id}.pdf", dependencies=[Depends(verificar_api_key)])
    def api_descargar_pdf(reporte_id: int, db=Depends(_get_session)):
        rep = db.get(Reporte, reporte_id)
        if rep is None:
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        if not rep.ruta_pdf or not os.path.isfile(rep.ruta_pdf):
            rep = crear_y_guardar_reporte(db, rep.corrida_id, obtener_configuracion().reportes_dir)
        return FileResponse(
            rep.ruta_pdf,
            media_type="application/pdf",
            filename=os.path.basename(rep.ruta_pdf),
        )

    @app.get("/api/v1/vuelos/{vuelo_id}/huecos.csv", dependencies=[Depends(verificar_api_key)])
    def api_huecos_csv(vuelo_id: int, db=Depends(_get_session)):
        vuelo = db.get(Vuelo, vuelo_id)
        if vuelo is None:
            raise HTTPException(status_code=404, detail="Vuelo no encontrado")
        res = obtener_ultimo_vuelo(db, vuelo.parcela_id, vuelo_id=vuelo.id)
        csv_txt = exportar_huecos_csv(res["huecos_resiembra"])
        return Response(
            content=csv_txt,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="huecos_vuelo_{vuelo_id}.csv"'},
        )

    @app.get("/api/v1/vuelos/{vuelo_id}/huecos.gpx", dependencies=[Depends(verificar_api_key)])
    def api_huecos_gpx(vuelo_id: int, db=Depends(_get_session)):
        vuelo = db.get(Vuelo, vuelo_id)
        if vuelo is None:
            raise HTTPException(status_code=404, detail="Vuelo no encontrado")
        res = obtener_ultimo_vuelo(db, vuelo.parcela_id, vuelo_id=vuelo.id)
        gpx_txt = exportar_huecos_gpx(res["huecos_resiembra"], res["parcela"]["nombre"])
        return Response(
            content=gpx_txt,
            media_type="application/gpx+xml; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="huecos_vuelo_{vuelo_id}.gpx"'},
        )

    @app.post("/api/v1/asistente", dependencies=[Depends(verificar_api_key)])
    def api_asistente(body: ConsultaAsistente, request: Request, db=Depends(_get_session)):
        mensaje = body.mensaje.strip()
        if not mensaje:
            raise HTTPException(status_code=400, detail="El mensaje no puede estar vacio")
        resumen = obtener_ultimo_vuelo(db, body.parcela_id)
        return consultar_asistente(
            mensaje=mensaje,
            historial=body.historial[-10:],
            resumen_vuelo=resumen,
            vista=body.vista,
            permitir_externo=getattr(request.app.state, "permitir_llm_externo", True),
        )

    if public_dir and os.path.isdir(public_dir):
        app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")

    return app


app = crear_app()
