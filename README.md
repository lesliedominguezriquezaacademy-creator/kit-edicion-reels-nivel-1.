# Kit de edición de Reels — Nivel 1

Convierte un video grabado en un Reel vertical 9:16 con subtítulos estilo karaoke, sin silencios y con zoom suave, usando Claude Code. Todo se procesa en tu computadora.

## Qué incluye
- `.claude/skills/edicion-reels-nivel-1/SKILL.md`: la skill que guía el proceso.
- `scripts/`: transcripción con Whisper, recorte de silencios y exportación 9:16.
- `CLAUDE.md` e `INSTRUCCIONES.md`: guía de estilo y pasos para empezar.

## Empezar
1. Instala Python, FFmpeg y Whisper (`pip install openai-whisper`). Más detalle en `INSTRUCCIONES.md`.
2. Abre esta carpeta en VS Code con Claude Code.
3. Copia tu video en `01-crudo/`.
4. Escribe: `edita mi reel`.

## Mantener el kit al día

Este repositorio existe para que la skill siga funcionando cuando cambian las herramientas que usa (Claude Code, FFmpeg, Whisper, Python).

- **Comprobar tu equipo:** `python scripts/verificar_entorno.py` te dice qué falta o qué versión no es compatible.
- **Recibir mejoras:** si descargaste el kit con Git, ejecuta `git pull`. Si lo descargaste como zip, vuelve a descargar la última versión (etiqueta) y copia tu carpeta `01-crudo`.
- **Qué cambió:** mira `CHANGELOG.md`.
- **Si algo se rompe tras actualizar FFmpeg o Whisper:** abre un issue con el resultado de `verificar_entorno.py`.

## Versiones
Las versiones finales se marcan con etiquetas (`v1.0.0`, `v1.1.0`...). Cada cambio importante va en un commit propio.

## Límites
Nivel 1: limpieza, subtítulos y movimiento discreto. No hace animaciones complejas ni edición multicámara.

## Licencia
Pendiente de definir por la autora.
