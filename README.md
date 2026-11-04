# agrodron.io

**AgroDron — Plataforma de Conteo de Cultivos con Visión Artificial (Sprint 1 · Épica 1 y preparación Épica 2)**  
Universidad de Caldas · Ingeniería de Sistemas y Computación · Vereda La Cabaña (Manizales, Caldas).

---

## Estructura del Proyecto

```text
agrodron.io/
├── src/
│   ├── core.py            # Plan de vuelo, calibración, QA óptico, cobertura GPS y carga S3
│   ├── simulator.py       # Simulador rural (Vereda La Cabaña), fotos EXIF GPS y ortomosaico
│   └── ui_template.py     # Estación web editorial-técnica + Walkthrough CSS (960×620)
├── tests/
│   └── test_agrodron.py   # Suite de 41 pruebas unitarias (unittest)
├── docs/
│   ├── PLAN_MEJORAS.md
│   ├── agrodron-vuelo-brief.md
│   └── Entregable_Sprint1_Epica1_AgroDron_v3.docx
├── output/                # Salidas generadas automáticamente al correr `demo`
│   ├── fotos_sd/          # Fotografías JPG (4000×3000) por cuadrante (Q1..Q4) con GPS EXIF
│   ├── reportes/          # reporte_qa.csv, planilla_conteo.csv, manifiesto.json
│   ├── rutas/             # ruta_vuelo.kml, ruta_vuelo_waypoints.csv
│   └── web/               # panel_agrodron.html, ortomosaico.jpg
├── agrodron_sprint1_epica1_v3.py  # Punto de entrada CLI (trazabilidad H5)
└── requirements.txt
```

---

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Ejecución de la demostración completa

Genera el cultivo en la zona rural de la **Vereda La Cabaña (`5.0949, -75.5891`)**, las fotos por cuadrante (`output/fotos_sd/Q1..Q4`), los reportes (`output/reportes/`), las rutas KML/CSV (`output/rutas/`) y abre la estación web (`output/web/panel_agrodron.html`):

```powershell
.venv\Scripts\python agrodron_sprint1_epica1_v3.py demo
```

## Ejecución de las pruebas

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```
