# agrodron.io

**AgroDron — Plataforma de Conteo de Cultivos con Visión Artificial (Sprint 1 · Épica 1 y preparación Épica 2)**  
Universidad de Caldas · Ingeniería de Sistemas y Computación · Vereda La Cabaña (Manizales, Caldas).

---

## Contenido del repositorio

| Archivo | Descripción |
|---|---|
| `agrodron_sprint1_epica1_v3.py` | Script principal CLI: calibración (`CA1`), plan de vuelo (`CA2/CA3`), ruta KML/CSV, conteo en tierra (`CA5`), auditoría óptica (`CA4`), cobertura real por GPS, carga a AWS S3 con manifiesto (`Épica 2`) y modo `demo`. |
| `simulador_agrodron.py` | Generador de cultivo sintético en la Vereda La Cabaña (1,0 ha, 2.352 plantas), fotos aéreas `.jpg` con EXIF GPS, ortomosaico y panel interactivo HTML con mapa satelital y animación del dron. |
| `test_agrodron.py` | Suite de 41 pruebas unitarias (`unittest`). |
| `requirements.txt` | Dependencias (`numpy`, `opencv-python-headless`, `Pillow`, `boto3`). |
| `PLAN_MEJORAS.md` | Plan detallado de mejoras, fases implementadas y guía de arquitectura. |
| `Entregable_Sprint1_Epica1_AgroDron_v3.docx` | Documento de entregable base del Sprint 1 / Épica 1. |

---

## Instalación rápida

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Ejecución de la simulación completa (Mapa + Dron + Fotos + QA)

Genera el cultivo en la zona rural de la **Vereda La Cabaña (`5.0949, -75.5891`)**, las fotos con GPS, el ortomosaico, el reporte de auditoría, el manifiesto S3 y abre el panel interactivo en el navegador:

```powershell
.venv\Scripts\python agrodron_sprint1_epica1_v3.py demo
```

## Ejecución de las pruebas

```powershell
.venv\Scripts\python -m unittest test_agrodron -v
```
