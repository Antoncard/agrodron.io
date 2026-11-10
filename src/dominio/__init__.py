# Dominio principal de AgroDron: plan de vuelo, parcela, QA de fotos y conteo
from src.dominio.conteo_referencia import (
    CONTEO_DOCUMENTO,
    comparar_conteo,
    leer_planilla_conteo,
)
from src.dominio.parcela import (
    CUADRANTES,
    R_TIERRA,
    Parcela,
    asignar_cuadrante,
    calcular_cobertura,
    cuadrante_local,
    escribir_kml,
    escribir_waypoints_csv,
    evaluar_cobertura,
    generar_ruta,
    lineas_x,
    posiciones_disparo,
)
from src.dominio.plan_vuelo import (
    CAMARA,
    GSD_MAX_CM_PX,
    HDOP_MAXIMO,
    OBTURACION_MAXIMA_S,
    SATELITES_MINIMOS,
    Camara,
    altura_maxima,
    altura_recomendada,
    calcular_gsd,
    calcular_plan_vuelo,
    huella,
    leer_obturacion,
    validar_calibracion,
)
from src.dominio.qa_fotos import (
    EXTENSIONES,
    GPS_LATITUD,
    GPS_LONGITUD,
    GPS_TAG,
    NITIDEZ_MINIMA,
    RESOLUCION,
    TAMANO_MINIMO,
    auditar_lote,
    evaluar_imagen,
    leer_aceptadas,
    leer_gps,
    leer_gris,
    listar_fotos,
    tiene_gps,
)

