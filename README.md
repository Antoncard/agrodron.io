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

---

## Estructura del Proyecto

```text
agrodron.io/
├── src/
│   ├── dominio/
│   │   ├── plan_vuelo.py         # Calibración (CA1), GSD y plan de vuelo (25 m / 30 m)
│   │   ├── parcela.py            # Parcela, cuadrantes 50×50 m (Q1 NO..Q4 SO), KML y cobertura
│   │   ├── qa_fotos.py           # Auditoría óptica Laplaciana (CA4) y lectura EXIF GPS
│   │   └── conteo_referencia.py  # Comparación de Ground Truth por cuadrante (CA5)
│   ├── almacen/
│   │   ├── local.py              # Copia idempotente por lote con verificación MD5
│   │   └── manifiesto.py         # Creación y guardado de manifiesto.json (Épica 2)
│   ├── ml/
│   │   ├── detector.py           # Interfaz Detector y DetectorSimulado (Épica 3)
│   │   ├── georef.py             # Conversión píxel -> metros en terreno y GPS
│   │   ├── fusion.py             # Eliminación de duplicados en solape (radio 0,6 m, margen 0,05 m)
│   │   └── evaluacion.py         # Conteo por cuadrante, % de error y semáforo (≤5%, ≤10%, >10%)
│   ├── sim/
│   │   └── simulador.py          # Simulador de cultivo, fotos EXIF GPS, ortomosaico y panel
│   ├── web/
│   │   └── plantilla.py          # Plantilla HTML/CSS/JS offline (<200 KB) con vendor/ y assets/
│   └── cli.py                    # Interfaz de línea de comandos (CLI)
├── tests/
│   └── test_agrodron.py          # Suite de pruebas unitarias (unittest)
├── public/                       # Panel estático autogenerado (index.html, assets/, vendor/)
├── agrodron_sprint1_epica1_v3.py # Punto de entrada mínimo que invoca cli.main()
├── pyproject.toml
└── requirements.txt
```

---

## Instalación y Uso

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# Plan de vuelo oficial a 25 m (GSD 0,938 cm/px, 228 fotos)
.venv\Scripts\python -m src.cli plan

# Conteo por cuadrante con IA y % de error (Épica 3)
.venv\Scripts\python -m src.cli contar

# Demostración completa (por defecto genera el plan completo a 25 m: 228 fotos; con --fotos menor genera una muestra)
.venv\Scripts\python -m src.cli demo --no-abrir

# Ejecutar suite de pruebas unitarias
.venv\Scripts\python -m unittest discover -s tests -v
```
