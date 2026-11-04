---
name: edicion-reels-nivel-1
description: "Edita Reels, TikToks y Shorts verticales 9:16 de nivel 1 (limpio y minimalista) a partir de un video crudo: quita silencios, transcribe con Whisper, pone subtítulos estilo karaoke (blanco cálido con palabra activa en dorado suave sobre fondo azul marino), añade zoom suave de máximo 2,5 % y fundido final, con audio limpio. Actívala cuando la persona diga: edita mi reel, edita este video, quita los silencios, ponle subtítulos, subtítulos karaoke, convierte a vertical, hazme un reel, prepara este video para TikTok/Shorts/Instagram, limpia mi video, exporta el reel, haz el draft, versión final, edición nivel 1, edición clean & minimal."
---

# Edición de Reels — Nivel 1 (Clean & Minimal)

Convierte un video grabado en `01-crudo/` en un Reel vertical 9:16, limpio y listo para revisar: sin silencios, con subtítulos karaoke, movimiento discreto y fundido final.

**Regla fundamental: primero un DRAFT; la versión final solo se hace después de que la persona lo apruebe. Nunca uses servicios de pago sin preguntar antes.**

Todo el proceso es local y gratuito (Python + FFmpeg + Whisper). Los scripts ya vienen en `scripts/`. No los reescribas: úsalos.

---

## Paso 0 — Preparar herramientas (solo la primera vez)

Verifica en silencio que existan. Si falta algo, instálalo avisando con un mensaje amable ("Estoy preparando las herramientas, tarda unos minutos la primera vez"):

```bash
python --version
ffmpeg -version
ffprobe -version
python -c "import whisper"
```

Si falta algo:
- **Python**: pide a la persona que lo instale desde python.org (marca "Add Python to PATH") y reinicie la terminal.
- **FFmpeg** (Windows): `winget install Gyan.FFmpeg` — luego reiniciar la terminal. En Mac: `brew install ffmpeg`.
- **Whisper**: `pip install openai-whisper` (descarga el modelo `small` la primera vez, es gratis y corre en su computadora).

Si algo no se puede instalar, no te bloquees: explica qué falta y ofrece la alternativa más simple.

## Paso 1 — Revisar el material

1. Lista lo que hay en `01-crudo/` (y recursos en `02-assets/`).
2. Si hay un solo video, úsalo. Si hay varios, pregunta cuál. Si la carpeta está vacía, pide que copie ahí su video.
3. Confirma duración y si tiene audio:
   ```bash
   ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "01-crudo/NOMBRE.mp4"
   ```
4. Haz como máximo **una** pregunta de preferencias, solo si hace falta (por ejemplo: ¿hay muletillas que quiera cortar a mano?). Si no, avanza con los valores por defecto.

## Paso 2 — Generar el DRAFT

Ejecuta el pipeline completo (transcribe → limpia silencios → exporta vertical):

```bash
python scripts/pipeline.py "01-crudo/NOMBRE.mp4"
```

Qué hace cada paso (por si necesitas correrlos por separado o ajustar):

| Paso | Script | Resultado |
|------|--------|-----------|
| Transcripción con Whisper (`small`, tiempos por palabra) | `scripts/transcribir.py` | `02-assets/subtitulos/NOMBRE.srt` y `.words.json` |
| Quitar silencios (> 0,5 s a -35 dB) | `scripts/limpiar_silencios.py` | `02-assets/sin_silencios/NOMBRE.mp4` y `.timeline.json` |
| Exportar 9:16 con subtítulos, zoom y fundido | `scripts/exportar_reel.py` | `03-output/NOMBRE.mp4` |

Ajustes disponibles en `limpiar_silencios.py` (úsalos solo si la persona lo pide o el resultado lo necesita):
- `--silence-duration 0.35` → corta pausas más cortas (ritmo más rápido).
- `--cut-range INICIO FIN` (repetible) → corta un tramo exacto, en segundos del video original. Es la forma de quitar **muletillas** ("eh", "mmm", "o sea") o tomas falladas: léelas en `02-assets/subtitulos/NOMBRE.words.json`, localiza sus tiempos y pásalos como rangos. Muestra a la persona la lista de cortes antes de aplicarlos si son más de unos pocos.
- `--speed-range INICIO FIN VELOCIDAD` (repetible) → velocidad distinta en un tramo (segundos del original), por ejemplo `--speed 1.32 --speed-range 13 21.8 1.5`. Úsalo para acelerar más las partes lentas o explicativas y dejar normales las importantes. Si la persona pide una duración máxima (ej. 55 s), ajusta `--speed` hasta cumplirla y mide con `ffprobe`.
- `--speed 1.1` → acelera ligeramente manteniendo el tono (entre 0.5 y 2.0). Úsalo solo si lo pide.

Para volver a ejecutar solo el paso de limpieza con ajustes y luego exportar:
```bash
python scripts/limpiar_silencios.py "01-crudo/NOMBRE.mp4" --cut-range 12.4 13.1
python scripts/exportar_reel.py "02-assets/sin_silencios/NOMBRE.mp4" "02-assets/subtitulos/NOMBRE.srt" --output "03-output/NOMBRE_draft.mp4"
```

Guarda el borrador con sufijo `_draft` (y `_draft2`, `_draft3`… si hay más iteraciones) para no sobrescribir versiones anteriores. Si usaste `pipeline.py`, renombra la salida a `NOMBRE_draft.mp4`.

### Estándar de estilo (ya incorporado en los scripts — no lo cambies sin pedirlo)

- **Formato**: vertical 9:16, 1080×1920, 30 fps.
- **Subtítulos karaoke**: texto blanco cálido, palabra activa en dorado suave, fondo azul marino translúcido y discreto, **máximo dos líneas**, dentro de la zona segura (lejos del borde inferior y de los botones de la app).
- **Movimiento**: zoom y paneo de baja intensidad, **máximo 2,5 %**. Sin apilar efectos ni añadir gráficos encima de imágenes ya recargadas.
- **Cierre**: fundido de salida (imagen y audio).
- **Audio**: original limpio, normalizado a -14 LUFS, sin música ni efectos decorativos añadidos (el sonido de inicio es opcional y propio de cada persona, ver abajo).
- **Ritmo**: ganchos condensados; si la persona pide destacar palabras clave, hazlo con el color dorado, sin saturar.

### Sonido de inicio propio (opcional)

Por defecto el reel no lleva ningún sonido añadido. Si la persona quiere una marca sonora al inicio, debe ser **suya**: pregúntale si ya tiene un archivo (`.wav` o `.mp3`) o ayúdala a crear uno propio (por ejemplo, sintetizándolo con FFmpeg o Python, o con un recurso que ella tenga derecho a usar). Luego se mezcla bajo la voz al exportar:

```bash
python scripts/exportar_reel.py "02-assets/sin_silencios/NOMBRE.mp4" "02-assets/subtitulos/NOMBRE.srt" --sonido "ruta/a/mi_sonido.wav" --output "03-output/NOMBRE_draft.mp4"
```

- Si tapa la voz, baja `SOUND_VOLUME` (0,55 por defecto) en `scripts/exportar_reel.py`.
- No descargues ni uses sonidos de terceros o de pago sin preguntar y sin confirmar que se pueden usar.

## Paso 3 — Revisar el draft antes de entregarlo

Antes de decir que está listo:
1. Confirma que el archivo existe en `03-output/` y mide su duración con `ffprobe`.
2. Extrae 2–3 fotogramas para verificar que los subtítulos se ven y no se salen de la zona segura:
   ```bash
   ffmpeg -y -ss 5 -i "03-output/NOMBRE_draft.mp4" -frames:v 1 "03-output/_chequeo.png"
   ```
   Revísalos y borra los `_chequeo.png` al terminar.
3. Compara duración original vs. final.

Si algo falla (Whisper no transcribe, FFmpeg da error), explica el problema en lenguaje simple, corrige y reintenta. No entregues un draft con subtítulos mal sincronizados o cortados.

## Paso 4 — Presentar y esperar aprobación

Abre el draft para que la persona lo escuche y lo vea:
- Windows: `start "" "03-output/NOMBRE_draft.mp4"`
- Mac: `open "03-output/NOMBRE_draft.mp4"`

Resume en pocas líneas:
- Ruta del archivo y duración (original → final).
- Qué se cortó (silencios y, si aplica, muletillas o tramos manuales).
- Qué se aplicó (subtítulos, zoom, fundido).

Termina preguntando: **"¿Lo apruebas o qué quieres ajustar?"** (audio, subtítulos, ritmo, zooms, cortes).

**No generes la versión final hasta recibir un sí explícito.**

## Paso 5 — Iterar y entregar la versión final

- Si pide cambios: aplícalos, genera un nuevo draft (`_draft2`) y vuelve al Paso 3.
- Cuando apruebe: exporta la versión final con el mismo comando de exportación, usando `--output "03-output/NOMBRE_final.mp4"`.
- Entrega la ruta del archivo final y sugiere publicarlo en Reels / TikTok / Shorts.

---

## Reglas

- **Pregunta antes de usar cualquier servicio de pago** (APIs, editores en la nube, bancos de música, voces con IA). El flujo estándar no necesita ninguno.
- **Whisper local** para transcribir. No subas el video a servicios externos.
- **No borres ni sobrescribas** archivos de `01-crudo/`. El original siempre se conserva.
- Guarda resultados en `03-output/` y archivos intermedios en `02-assets/`.
- Habla con lenguaje simple: la persona puede no saber de edición ni de programación.
- Si la persona pide algo fuera del nivel 1 (animaciones complejas, motion graphics, varias cámaras, color grading), dilo con honestidad: este flujo cubre limpieza, subtítulos y movimiento discreto; ofrece hacerlo como un paso aparte.
