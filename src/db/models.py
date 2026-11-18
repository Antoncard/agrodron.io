# Modelo relacional SQLAlchemy 2 (11 tablas de la seccion 3.1, compatible SQLite y MySQL 8)
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _ahora_utc():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Finca(Base):
    __tablename__ = "finca"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    vereda: Mapped[str] = mapped_column(String(120), nullable=False)
    municipio: Mapped[str] = mapped_column(String(120), nullable=False)
    altitud_msnm: Mapped[int] = mapped_column(Integer, nullable=False, default=1417)

    parcelas: Mapped[list["ParcelaDB"]] = relationship(back_populates="finca", cascade="all, delete-orphan")


class ParcelaDB(Base):
    __tablename__ = "parcela"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finca_id: Mapped[int] = mapped_column(ForeignKey("finca.id", ondelete="CASCADE"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    lat_origen: Mapped[float] = mapped_column(Float, nullable=False)
    lon_origen: Mapped[float] = mapped_column(Float, nullable=False)
    ancho_m: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    largo_m: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    rumbo_deg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    plantas_esperadas: Mapped[int] = mapped_column(Integer, nullable=False, default=2500)

    finca: Mapped["Finca"] = relationship(back_populates="parcelas")
    cuadrantes: Mapped[list["Cuadrante"]] = relationship(back_populates="parcela", cascade="all, delete-orphan")
    vuelos: Mapped[list["Vuelo"]] = relationship(back_populates="parcela", cascade="all, delete-orphan")


class Cuadrante(Base):
    __tablename__ = "cuadrante"
    __table_args__ = (UniqueConstraint("parcela_id", "codigo", name="uq_cuadrante_parcela_codigo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcela.id", ondelete="CASCADE"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(8), nullable=False)
    orientacion: Mapped[str] = mapped_column(String(8), nullable=False)
    esperadas: Mapped[int] = mapped_column(Integer, nullable=False, default=625)

    parcela: Mapped["ParcelaDB"] = relationship(back_populates="cuadrantes")
    ground_truths: Mapped[list["GroundTruth"]] = relationship(back_populates="cuadrante", cascade="all, delete-orphan")


class Vuelo(Base):
    __tablename__ = "vuelo"
    __table_args__ = (Index("ix_vuelo_parcela_fecha", "parcela_id", "fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parcela_id: Mapped[int] = mapped_column(ForeignKey("parcela.id", ondelete="CASCADE"), nullable=False)
    fecha: Mapped[str] = mapped_column(String(20), nullable=False)
    altura_m: Mapped[float] = mapped_column(Float, nullable=False)
    gsd_cm_px: Mapped[float] = mapped_column(Float, nullable=False)
    solape_frontal: Mapped[float] = mapped_column(Float, nullable=False, default=0.80)
    solape_lateral: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)
    velocidad_ms: Mapped[float] = mapped_column(Float, nullable=False, default=4.5)
    satelites: Mapped[int] = mapped_column(Integer, nullable=False)
    hdop: Mapped[float] = mapped_column(Float, nullable=False)
    obturacion: Mapped[str] = mapped_column(String(32), nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="APROBADO")
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    parcela: Mapped["ParcelaDB"] = relationship(back_populates="vuelos")
    imagenes: Mapped[list["Imagen"]] = relationship(back_populates="vuelo", cascade="all, delete-orphan")
    corridas: Mapped[list["CorridaIA"]] = relationship(back_populates="vuelo", cascade="all, delete-orphan")


class Imagen(Base):
    __tablename__ = "imagen"
    __table_args__ = (
        UniqueConstraint("vuelo_id", "archivo", name="uq_imagen_vuelo_archivo"),
        Index("ix_imagen_vuelo", "vuelo_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vuelo_id: Mapped[int] = mapped_column(ForeignKey("vuelo.id", ondelete="CASCADE"), nullable=False)
    archivo: Mapped[str] = mapped_column(String(180), nullable=False)
    ruta: Mapped[str] = mapped_column(String(320), nullable=False)
    md5: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ancho_px: Mapped[int] = mapped_column(Integer, nullable=False, default=4000)
    alto_px: Mapped[int] = mapped_column(Integer, nullable=False, default=3000)
    nitidez: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    dictamen: Mapped[str] = mapped_column(String(24), nullable=False, default="ACEPTADA")
    motivo: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    cuadrante_id: Mapped[int | None] = mapped_column(ForeignKey("cuadrante.id", ondelete="SET NULL"), nullable=True)

    vuelo: Mapped["Vuelo"] = relationship(back_populates="imagenes")


class ModeloIA(Base):
    __tablename__ = "modelo_ia"
    __table_args__ = (UniqueConstraint("nombre", "version", name="uq_modelo_nombre_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    arquitectura: Mapped[str] = mapped_column(String(64), nullable=False)
    ruta_pesos: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fecha_entrenamiento: Mapped[str] = mapped_column(String(32), nullable=False)
    metricas_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    corridas: Mapped[list["CorridaIA"]] = relationship(back_populates="modelo")


class CorridaIA(Base):
    __tablename__ = "corrida_ia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vuelo_id: Mapped[int] = mapped_column(ForeignKey("vuelo.id", ondelete="CASCADE"), nullable=False)
    modelo_id: Mapped[int] = mapped_column(ForeignKey("modelo_ia.id", ondelete="RESTRICT"), nullable=False)
    inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    umbral_confianza: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    radio_fusion_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    estado: Mapped[str] = mapped_column(String(24), nullable=False, default="EN_COLA")
    total_detectadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errores_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    vuelo: Mapped["Vuelo"] = relationship(back_populates="corridas")
    modelo: Mapped["ModeloIA"] = relationship(back_populates="corridas")
    detecciones: Mapped[list["Deteccion"]] = relationship(back_populates="corrida", cascade="all, delete-orphan")
    conteos: Mapped[list["ConteoCuadrante"]] = relationship(back_populates="corrida", cascade="all, delete-orphan")
    reporte: Mapped["Reporte | None"] = relationship(back_populates="corrida", uselist=False, cascade="all, delete-orphan")


class Deteccion(Base):
    __tablename__ = "deteccion"
    __table_args__ = (Index("ix_deteccion_corrida_cuadrante", "corrida_id", "cuadrante_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corrida_id: Mapped[int] = mapped_column(ForeignKey("corrida_ia.id", ondelete="CASCADE"), nullable=False)
    imagen_id: Mapped[int | None] = mapped_column(ForeignKey("imagen.id", ondelete="SET NULL"), nullable=True)
    x_m: Mapped[float] = mapped_column(Float, nullable=False)
    y_m: Mapped[float] = mapped_column(Float, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    confianza: Mapped[float] = mapped_column(Float, nullable=False)
    clase: Mapped[str] = mapped_column(String(32), nullable=False, default="planta")
    cuadrante_id: Mapped[int | None] = mapped_column(ForeignKey("cuadrante.id", ondelete="SET NULL"), nullable=True)
    fusionada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    corrida: Mapped["CorridaIA"] = relationship(back_populates="detecciones")


class ConteoCuadrante(Base):
    __tablename__ = "conteo_cuadrante"
    __table_args__ = (UniqueConstraint("corrida_id", "cuadrante_id", name="uq_conteo_corrida_cuadrante"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corrida_id: Mapped[int] = mapped_column(ForeignKey("corrida_ia.id", ondelete="CASCADE"), nullable=False)
    cuadrante_id: Mapped[int] = mapped_column(ForeignKey("cuadrante.id", ondelete="CASCADE"), nullable=False)
    detectadas: Mapped[int] = mapped_column(Integer, nullable=False)
    esperadas: Mapped[int] = mapped_column(Integer, nullable=False)
    deficit: Mapped[int] = mapped_column(Integer, nullable=False)
    error_vs_gt_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    semaforo: Mapped[str] = mapped_column(String(16), nullable=False, default="VERDE")

    corrida: Mapped["CorridaIA"] = relationship(back_populates="conteos")


class GroundTruth(Base):
    __tablename__ = "ground_truth"
    __table_args__ = (UniqueConstraint("cuadrante_id", "fecha", name="uq_gt_cuadrante_fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cuadrante_id: Mapped[int] = mapped_column(ForeignKey("cuadrante.id", ondelete="CASCADE"), nullable=False)
    fecha: Mapped[str] = mapped_column(String(20), nullable=False)
    contadas: Mapped[int] = mapped_column(Integer, nullable=False)
    responsable: Mapped[str] = mapped_column(String(120), nullable=False, default="Equipo Campo UCaldas")

    cuadrante: Mapped["Cuadrante"] = relationship(back_populates="ground_truths")


class Reporte(Base):
    __tablename__ = "reporte"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    corrida_id: Mapped[int] = mapped_column(ForeignKey("corrida_ia.id", ondelete="CASCADE"), nullable=False, unique=True)
    resumen_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ruta_pdf: Mapped[str] = mapped_column(String(320), nullable=False)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_ahora_utc)

    corrida: Mapped["CorridaIA"] = relationship(back_populates="reporte")
