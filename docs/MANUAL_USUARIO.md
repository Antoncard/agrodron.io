# Manual de Usuario y Operación — AgroDron (Sprint 3 · Épica 4)

**Proyecto:** AgroDron — Conteo de Plantas por Hectárea con Imágenes de Dron (Universidad de Caldas)  
**Piloto:** Finca El Mirador, Vereda La Cabaña (Manizales, Caldas · `5.0949, -75.5891`, 1.417 msnm · 1,0 ha).

---

## 1. Guía para el Agricultor (Vista Agricultor)

Al abrir el panel web (`http://127.0.0.1:8000` o `public/index.html` sin internet), se presenta la **Vista Agricultor**:

1. **Tarjeta Principal (UI-01):** Muestra tres cifras claras: **Plantas Esperadas (2.500)**, **Plantas Estimadas (IA)** y **Faltantes / Déficit** con su porcentaje y semáforo (`VERDE`, `AMARILLO`, `ROJO`).
2. **Mapa de Densidad 10 × 10 m (UI-02):** Cuadrícula de 100 celdas sobre la hectárea dividida en los cuatro cuadrantes (`Q1 NO`, `Q2 NE`, `Q3 SE`, `Q4 SO`). Al tocar o pasar el cursor sobre cada cuadro se ve la cantidad de plantas detectadas y la densidad equivalente en plantas/ha.
3. **Tabla por Cuadrante en Lenguaje Llano (UI-03):** Resume el déficit de cada cuadrante con una recomendación directa de resiembra (por ejemplo: *"En el cuadrante Q3 (Sureste) faltan unas 46 plantas..."*).
4. **Exportación de Huecos para Resiembra (Idea 1):**
   - **Exportar Huecos (.GPX):** Archivo GPS para abrir en el celular en campo (OsmAnd, Gaia GPS, Google Earth) y caminar directo a los sitios vacíos.
   - **Exportar Huecos (.CSV):** Tabla con `id, cuadrante, lat, lon, x_m, y_m` para hoja de cálculo o QGIS.
5. **Reporte PDF de 1 Página (Idea 4 / API-05):** Descarga o imprime un resumen ejecutivo de una sola hoja con las 3 cifras, el mapa de densidad, la tabla por cuadrante y la recomendación de resiembra.
6. **Comparación entre Vuelos (Idea 6):** Historial de vuelos de la parcela (p. ej., vuelo a 30 m rechazado por GSD vs. vuelo oficial a 25 m aprobado).

---

## 2. Guía para el Operador / Ingeniero (Vista Técnica y CLI)

### 2.1 Instalación y configuración segura (BD-N5)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
```

> **Seguridad (BD-N5):** Las credenciales (`AGRODRON_API_KEY`, `DATABASE_URL`, `VERTEX_API_KEY`, `OPENROUTER_API_KEY`) se configuran únicamente en `.env` o en variables de entorno del servidor, nunca en el código fuente.

### 2.2 Comandos principales (CLI)

```powershell
# Inicializar esquema Alembic (11 tablas) + seed piloto + corrida IA + PDF
.venv\Scripts\python -m src.cli db-init

# Simulación de vuelo con bitácora real y generación del panel en public/index.html
.venv\Scripts\python -m src.cli demo --fecha 2026-10-22 --satelites 18 --obturacion 1/1000 --hdop 0.68 --no-abrir

# Importar auditoría QA, manifiesto y planilla Ground Truth a la BD
.venv\Scripts\python -m src.cli importar --fecha 2026-10-22 --qa-csv output/reportes/reporte_qa.csv --manifiesto output/reportes/manifiesto.json --conteo-csv output/reportes/planilla_conteo.csv

# Levantar API REST FastAPI (/api/v1) y Dashboard
.venv\Scripts\python -m src.cli api --host 127.0.0.1 --port 8000

# Ejecutar worker automático de inferencia (una pasada o servicio continuo)
.venv\Scripts\python -m src.cli worker --una-vez

# Entrenar modelo detector desde cero
.venv\Scripts\python -m src.cli entrenar --backend cv

# Respaldo y verificación de restauración de BD (BD-N6)
.venv\Scripts\python scripts/backup_db.py
```

### 2.3 Endpoints de la API REST (`/api/v1`)

Todos los endpoints protegidos requieren el header `x-api-key` (validado con `hmac.compare_digest`):

| Método y Ruta | Descripción | Requerimiento |
|---|---|---|
| `GET /api/v1/salud` | Estado de salud de la API y conexión a BD | Operación |
| `GET /api/v1/parcelas/{id}/ultimo-vuelo` | Resumen completo del último vuelo, déficit, densidad 10×10, huecos e histórico | API-01, BD-07 |
| `GET /api/v1/vuelos/{id}/conteo` | Conteo total y por cuadrante con error vs. Ground Truth y semáforo | API-02, BD-06 |
| `GET /api/v1/vuelos/{id}/detecciones.geojson` | Capa GeoJSON de plantas detectadas para mapa y QGIS | API-03 |
| `POST /api/v1/vuelos/{id}/procesar` | Encola una corrida de IA (`EN_COLA` → `PROCESANDO` → `LISTA`) | API-04, IA-26 |
| `GET /api/v1/corridas/{id}` | Consulta el estado y trazabilidad de una corrida IA | IA-24, IA-26 |
| `GET /api/v1/reportes/{id}.pdf` | Descarga el reporte PDF de 1 página para el agricultor | API-05, BD-08 |
| `GET /api/v1/vuelos/{id}/huecos.csv` | Exportación CSV de huecos de resiembra | Idea 1 |
| `GET /api/v1/vuelos/{id}/huecos.gpx` | Exportación GPX de huecos de resiembra para GPS móvil | Idea 1 |

### 2.4 Despliegue con Docker (MySQL 8 + API + Worker)

```bash
copy .env.example .env
docker compose up --build
```
