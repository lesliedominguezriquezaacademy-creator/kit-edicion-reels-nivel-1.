# Kit: Edición de Reels — Nivel 1

Edita tus videos cortos con Claude Code sin saber de edición ni de programación. Tú grabas; Claude quita los silencios, pone subtítulos estilo karaoke, añade un zoom muy suave y un fundido final.

## Qué necesitas

| Requisito | Cómo conseguirlo |
|-----------|------------------|
| Claude Code | Ya instalado (VS Code o terminal) |
| Python 3.10+ | python.org → durante la instalación marca **"Add Python to PATH"** |
| FFmpeg | Windows: `winget install Gyan.FFmpeg` · Mac: `brew install ffmpeg` |
| Whisper (transcripción local y gratuita) | `pip install openai-whisper` |

No necesitas pagar ningún servicio. Si Claude te propone uno, te preguntará antes.

> Si te falta algo, Claude lo detecta y te guía. Después de instalar FFmpeg o Python, reinicia la terminal.

## Pasos

1. **Abre esta carpeta** (`kit-edicion-reels-nivel-1`) en VS Code con Claude Code.
2. **Copia tu video** dentro de `01-crudo/` (formato `.mp4` o `.mov`).
3. **Escribe** en Claude: `edita mi reel`.
4. **Espera el borrador.** Claude lo abrirá en `03-output/` con el nombre `..._draft.mp4`. Velo y escúchalo completo.
5. **Dile qué ajustar** (por ejemplo: "corta la muletilla del segundo 12", "más rápido", "los subtítulos más pequeños") o **apruébalo**.
6. Cuando digas que sí, Claude genera `..._final.mp4`, listo para publicar.

La primera vez tarda más porque Whisper descarga su modelo (unos cientos de MB).

## Qué hace Claude por ti

- Recorta silencios y espacios muertos (y las muletillas que le indiques).
- Transcribe en tu computadora (tu video no se sube a ningún servicio).
- Subtítulos karaoke: blanco cálido, palabra activa en dorado suave, fondo azul marino translúcido, máximo dos líneas y dentro de la zona segura.
- Formato vertical 9:16 (1080×1920).
- Zoom/paneo de máximo 2,5 % y fundido al final.
- Audio original limpio y con volumen normalizado.
- Opcional: un sonido de inicio **tuyo** (tu marca sonora). Dile a Claude que quieres uno y te ayuda a crearlo o a usar el que ya tengas.

## Estructura de carpetas

```
kit-edicion-reels-nivel-1/
├── CLAUDE.md                  ← Guía de estilo y mensaje de bienvenida
├── INSTRUCCIONES.md           ← Este archivo
├── .claude/skills/edicion-reels-nivel-1/SKILL.md   ← La skill
├── scripts/                   ← Herramientas que usa Claude (no las toques)
├── 01-crudo/                  ← Tus videos originales (aquí copias el tuyo)
├── 02-assets/                 ← Subtítulos y videos intermedios (automático)
└── 03-output/                 ← Borradores y versión final
```

## Problemas comunes

- **"No se encontró ffmpeg"** → instálalo y reinicia la terminal.
- **Whisper tarda mucho** → es normal en la primera vez y en videos largos; funciona sin internet después de descargar el modelo.
- **Un subtítulo salió mal escrito** → díselo a Claude y lo corrige en el siguiente borrador.

## Límites del nivel 1

Este kit cubre limpieza, subtítulos y movimiento discreto. No hace motion graphics, edición multicámara ni corrección de color avanzada.
