"""Esquema inicial de 11 tablas para AgroDron (SQLite y MySQL 8)

Revision ID: 0001_esquema_inicial
Revises:
Create Date: 2026-11-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_esquema_inicial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finca",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("vereda", sa.String(length=120), nullable=False),
        sa.Column("municipio", sa.String(length=120), nullable=False),
        sa.Column("altitud_msnm", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "modelo_ia",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("arquitectura", sa.String(length=64), nullable=False),
        sa.Column("ruta_pesos", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("dataset_version", sa.String(length=64), nullable=False),
        sa.Column("fecha_entrenamiento", sa.String(length=32), nullable=False),
        sa.Column("metricas_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre", "version", name="uq_modelo_nombre_version"),
    )
    op.create_table(
        "parcela",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("finca_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("lat_origen", sa.Float(), nullable=False),
        sa.Column("lon_origen", sa.Float(), nullable=False),
        sa.Column("ancho_m", sa.Float(), nullable=False),
        sa.Column("largo_m", sa.Float(), nullable=False),
        sa.Column("rumbo_deg", sa.Float(), nullable=False),
        sa.Column("plantas_esperadas", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["finca_id"], ["finca.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cuadrante",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parcela_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=8), nullable=False),
        sa.Column("orientacion", sa.String(length=8), nullable=False),
        sa.Column("esperadas", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["parcela_id"], ["parcela.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parcela_id", "codigo", name="uq_cuadrante_parcela_codigo"),
    )
    op.create_table(
        "vuelo",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parcela_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.String(length=20), nullable=False),
        sa.Column("altura_m", sa.Float(), nullable=False),
        sa.Column("gsd_cm_px", sa.Float(), nullable=False),
        sa.Column("solape_frontal", sa.Float(), nullable=False),
        sa.Column("solape_lateral", sa.Float(), nullable=False),
        sa.Column("velocidad_ms", sa.Float(), nullable=False),
        sa.Column("satelites", sa.Integer(), nullable=False),
        sa.Column("hdop", sa.Float(), nullable=False),
        sa.Column("obturacion", sa.String(length=32), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=False),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["parcela_id"], ["parcela.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vuelo_parcela_fecha", "vuelo", ["parcela_id", "fecha"], unique=False)
    op.create_table(
        "corrida_ia",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vuelo_id", sa.Integer(), nullable=False),
        sa.Column("modelo_id", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("umbral_confianza", sa.Float(), nullable=False),
        sa.Column("radio_fusion_m", sa.Float(), nullable=False),
        sa.Column("estado", sa.String(length=24), nullable=False),
        sa.Column("total_detectadas", sa.Integer(), nullable=False),
        sa.Column("errores_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["modelo_id"], ["modelo_ia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vuelo_id"], ["vuelo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ground_truth",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cuadrante_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.String(length=20), nullable=False),
        sa.Column("contadas", sa.Integer(), nullable=False),
        sa.Column("responsable", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["cuadrante_id"], ["cuadrante.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cuadrante_id", "fecha", name="uq_gt_cuadrante_fecha"),
    )
    op.create_table(
        "imagen",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vuelo_id", sa.Integer(), nullable=False),
        sa.Column("archivo", sa.String(length=180), nullable=False),
        sa.Column("ruta", sa.String(length=320), nullable=False),
        sa.Column("md5", sa.String(length=64), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("ancho_px", sa.Integer(), nullable=False),
        sa.Column("alto_px", sa.Integer(), nullable=False),
        sa.Column("nitidez", sa.Float(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("dictamen", sa.String(length=24), nullable=False),
        sa.Column("motivo", sa.String(length=120), nullable=False),
        sa.Column("cuadrante_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["cuadrante_id"], ["cuadrante.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vuelo_id"], ["vuelo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vuelo_id", "archivo", name="uq_imagen_vuelo_archivo"),
    )
    op.create_index("ix_imagen_vuelo", "imagen", ["vuelo_id"], unique=False)
    op.create_table(
        "conteo_cuadrante",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("corrida_id", sa.Integer(), nullable=False),
        sa.Column("cuadrante_id", sa.Integer(), nullable=False),
        sa.Column("detectadas", sa.Integer(), nullable=False),
        sa.Column("esperadas", sa.Integer(), nullable=False),
        sa.Column("deficit", sa.Integer(), nullable=False),
        sa.Column("error_vs_gt_pct", sa.Float(), nullable=False),
        sa.Column("semaforo", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["corrida_id"], ["corrida_ia.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cuadrante_id"], ["cuadrante.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("corrida_id", "cuadrante_id", name="uq_conteo_corrida_cuadrante"),
    )
    op.create_table(
        "deteccion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("corrida_id", sa.Integer(), nullable=False),
        sa.Column("imagen_id", sa.Integer(), nullable=True),
        sa.Column("x_m", sa.Float(), nullable=False),
        sa.Column("y_m", sa.Float(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("confianza", sa.Float(), nullable=False),
        sa.Column("clase", sa.String(length=32), nullable=False),
        sa.Column("cuadrante_id", sa.Integer(), nullable=True),
        sa.Column("fusionada", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["corrida_id"], ["corrida_ia.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cuadrante_id"], ["cuadrante.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["imagen_id"], ["imagen.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deteccion_corrida_cuadrante", "deteccion", ["corrida_id", "cuadrante_id"], unique=False)
    op.create_table(
        "reporte",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("corrida_id", sa.Integer(), nullable=False),
        sa.Column("resumen_json", sa.JSON(), nullable=False),
        sa.Column("ruta_pdf", sa.String(length=320), nullable=False),
        sa.Column("creado", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["corrida_id"], ["corrida_ia.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("corrida_id"),
    )


def downgrade() -> None:
    op.drop_table("reporte")
    op.drop_index("ix_deteccion_corrida_cuadrante", table_name="deteccion")
    op.drop_table("deteccion")
    op.drop_table("conteo_cuadrante")
    op.drop_index("ix_imagen_vuelo", table_name="imagen")
    op.drop_table("imagen")
    op.drop_table("ground_truth")
    op.drop_table("corrida_ia")
    op.drop_index("ix_vuelo_parcela_fecha", table_name="vuelo")
    op.drop_table("vuelo")
    op.drop_table("cuadrante")
    op.drop_table("parcela")
    op.drop_table("modelo_ia")
    op.drop_table("finca")
