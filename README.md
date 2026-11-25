# agrodron.io

**AgroDron — Conteo de Plantas por Hectárea con Fotos de Dron (Universidad de Caldas)**  
Parcela piloto de **1,0 ha (100 m × 100 m)** en la **Vereda La Cabaña (Manizales, Caldas · `5.0949, -75.5891`, 1.417 msnm)**.

---

## Parámetros Oficiales de Vuelo y Cámara

- **Cámara:** sensor `13,2 mm`, focal `8,8 mm`, resolución `4000 × 3000 px`.
- **Vuelo a 25 m (oficial, cumple CA3):** GSD de **`0,938 cm/px`** (`< 1,0 cm/px`), huella de `37,5 × 28,12 m`, malla de `12 líneas × 19 fotos` = **`228 fotos`**, intervalo de disparo `1,25 s`, cobertura `100 %`.
- **Vuelo a 30 m (caso anterior, incumple CA3):** GSD de **`1,125 cm/px`** (`≥ 1,0 cm/px`), huella de `45,0 × 33,75 m`, malla de `10 líneas × 16 fotos` = **`160 fotos`**, intervalo de disparo `1,5 s`.
- **Cuadrantes reales:** cuatro cuadrantes de **`50 × 50 m`** (`2.500 m²` c/u): **Q1 (NO)**, **Q2 (NE)**, **Q3 (SE)** y **Q4 (SO)**.
- **Ground Truth en tierra (CA5):** `2.352 plantas` vivas sobre `2.500` sitios esperados (`Q1: 598`, `Q2: 584`, `Q3: 579`, `Q4: 591`).
- **Almacenamiento (Épica 2):** carpeta local `raw/<finca>/<lote>/<fecha>/` con verificación `MD5` y `manifiesto.json`.
- **Base de datos e IA (Épicas 3 y 4):** SQLAlchemy 2 + Alembic (SQLite en desarrollo/CI, MySQL 8 en Docker), detector entrenado (`modelos/v1.0.0/` con tiling `640×640` + NMS + georreferenciación + fusión `0,6 m`), API REST FastAPI (`/api/v1`) y worker automático de eventos.

---

## Estructura del Proyecto

```text
agrodron.io/
├── alembic/                      # Migraciones de esquema SQLite / MySQL 8
├── docs/
│   ├── GUION_PRUEBA_USUARIO.md   # Guion de prueba de usabilidad con agricultores (UI-04)
│   ├── MANUAL_USUARIO.md         # Manual de usuario (agricultor y operador, Sprint 3)
│   ├── PLAN_MEJORAS.md
│   └── agrodron-vuelo-brief.md
├── ml_training/
│   ├── config_yolo.yaml          # Hiperparámetros reproducibles (GSD fijo, scale=0)
│   ├── preparar_dataset.py       # Partición estricta por foto completa (train/val/test)
│   └── entrenar.py               # Entrenamiento reproducible CV o Ultralytics YOLO
├── modelos/v1.0.0/               # Pesos calibrados, sha256, curvas y metricas.json
├── scripts/backup_db.py          # Respaldo y verificación de restauración SQLite/MySQL
├── src/
│   ├── almacen/                  # Copia idempotente MD5 y manifiesto.json (Épica 2)
│   ├── api/                      # FastAPI /api/v1 protegido con x-api-key + PDF + GeoJSON
│   ├── db/                       # Modelos SQLAlchemy 2 (11 tablas) y sesiones
│   ├── dominio/                  # Plan de vuelo, parcela, QA óptico Laplaciano y Ground Truth
│   ├── ml/                       # Tiling, NMS, DetectorVisionCV, DetectorYOLO, georef y fusión
│   ├── servicios/                # Seed, importador transaccional, densidad, huecos y PDF 1 pág.
│   ├── sim/                      # Simulador rural, EXIF GPS y ortomosaico
│   ├── web/                      # Dashboard dual (Vista Agricultor / Vista Técnica, < 200 KB)
│   ├── worker/                   # Servicio automático de ingesta y ejecución de corridas IA
│   └── cli.py                    # Interfaz de línea de comandos (CLI)
├── tests/                        # Suite integral de pruebas unitarias e integración
├── public/                       # Panel estático offline/online autogenerado (Vercel / USB)
├── PRODUCT.md & DESIGN.md        # Contexto de producto y sistema visual (Impeccable)
├── Dockerfile & docker-compose.yml
├── requirements.txt
└── requirements-ml.txt           # Dependencias opcionales PyTorch / Ultralytics YOLO
```

---

## Instalación y Uso

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 1. Inicializar BD (migraciones Alembic + seed piloto + corrida IA + PDF 1 página)
.venv\Scripts\python -m src.cli db-init

# 2. Simulación completa a 25 m (228 fotos) y generación de public/index.html
.venv\Scripts\python -m src.cli demo --no-abrir

# 3. Levantar API REST y Dashboard en http://127.0.0.1:8000
.venv\Scripts\python -m src.cli api

# 4. Ejecutar worker automático (una pasada o servicio continuo)
.venv\Scripts\python -m src.cli worker --una-vez

# 5. Entrenar detector desde cero (dataset YOLO particionado por foto)
.venv\Scripts\python -m src.cli entrenar --backend cv

# 6. Ejecutar toda la suite de pruebas
.venv\Scripts\python -m unittest discover -s tests -v
```

### Ejecución con Docker (MySQL 8 + API + Worker)

```bash
copy .env.example .env
docker compose up --build
```
