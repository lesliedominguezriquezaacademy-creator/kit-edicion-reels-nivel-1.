# Registro de cambios

Formato: versión, fecha y qué cambió. Las versiones finales se marcan con etiquetas de Git.

## v1.1.0 — 2026-11-04
- Nuevo `scripts/verificar_entorno.py`: comprueba Python, FFmpeg (y los filtros que usa el kit) y Whisper antes de editar.
- La skill ejecuta esa verificación en el Paso 0.
- Nueva sección "Mantener el kit al día" en el README.
- Este registro de cambios.

## v1.0.0 — 2026-11-04
- Versión inicial: skill, scripts de transcripción (Whisper), limpieza de silencios y exportación 9:16 con subtítulos karaoke, zoom suave (máx. 2,5 %) y fundido final.
- Sonido de inicio opcional y propio (`--sonido`).
- Velocidades por tramo (`--speed-range`).

## Integraciones de las que depende
| Pieza | Para qué | Si cambia |
|---|---|---|
| Claude Code | Ejecuta la skill | Revisa que `.claude/skills/` siga siendo la ruta de skills |
| FFmpeg | Cortes, zoom, subtítulos, audio | Corre `verificar_entorno.py` |
| openai-whisper | Transcripción con tiempo por palabra | Corre `verificar_entorno.py` y prueba con un video corto |
| Python | Scripts | Se necesita 3.10 o superior |
