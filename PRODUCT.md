# PRODUCT.md — AgroDron (Universidad de Caldas)

## 1. Propósito del Producto
**AgroDron** convierte imágenes aéreas capturadas con dron en un conteo georreferenciado de plantas por hectárea y en una guía accionable de resiembra para cultivos en ladera y parcela piloto (**Vereda La Cabaña, Manizales, Caldas · 1,417 msnm · 1,0 ha**).

## 2. Audiencias y Contextos de Uso

### A. Agricultor / Administrador de Finca (Audiencia Primaria — Vista por Defecto)
* **Contexto:** Revisa el resultado en campo (celular, tablet o portátil sin internet / desde USB) bajo luz solar directa.
* **Qué necesita resolver en < 5 segundos:**
  1. ¿Cuántas plantas hay vivas frente a las 2.500 esperadas y cuál es el déficit total?
  2. ¿Qué cuadrante (`Q1 NO`, `Q2 NE`, `Q3 SE`, `Q4 SO`) presenta más pérdidas?
  3. ¿Dónde están exactamente los huecos para mandar al equipo de resiembra (archivo GPX/CSV o PDF de 1 página)?
* **Lenguaje:** Llano, agronómico, directo (*"En el cuadrante Q3 (SE) faltan unas 46 plantas — prioridad alta de resiembra"*), nunca jerga de fotogrametría ni visión artificial en la primera pantalla.

### B. Ingeniero de Drones / Analista de Datos IA (Audiencia Técnica — Vista Técnica)
* **Contexto:** Audita cumplimiento de criterios de aceptación (`CA1–CA5`), diagnostica el Hallazgo H1 (30 m vs 25 m), verifica integridad `MD5` del lote, evalúa el modelo IA (`F1`, `Precision`, `Recall`, sensibilidad GPS) y dispara corridas desde la API.
* **Qué necesita:** Trazabilidad completa a `modelo_ia`, varianza Laplaciana, GSD (`0,938 cm/px`), coordenadas EXIF GPS, cobertura por cuadrante y métricas de evaluación por cuadrante.

## 3. Restricciones No Negociables
* **Operación 100 % Offline / USB y Online API:** El mismo HTML (`public/index.html` < 200 KB) se conecta en vivo a `/api/v1/...` cuando detecta el servidor FastAPI, y degrada sin errores a datos embebidos cuando se abre desde USB o despliegue estático (Vercel).
* **Claridad en Campo:** Alto contraste (WCAG AA >= 4.5:1), botones táctiles amplios (>= 44 px), sin dependencia de CDNs externos ni tipografías remotas.
