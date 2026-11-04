import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import re
import shutil
import subprocess
import sys

MIN_PYTHON = (3, 10)
OK, FALTA = "OK    ", "FALTA "


def run(command):
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return result.returncode, result.stdout + result.stderr


def check_python(problems):
    version = sys.version_info[:3]
    text = ".".join(map(str, version))
    if version >= MIN_PYTHON:
        print(f"{OK}Python {text}")
    else:
        print(f"{FALTA}Python {text} (se necesita {MIN_PYTHON[0]}.{MIN_PYTHON[1]} o superior)")
        problems.append("Actualiza Python desde python.org.")


def check_ffmpeg(problems):
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        if not path:
            print(f"{FALTA}{tool} no está en el PATH")
            problems.append(
                f"Instala FFmpeg (Windows: winget install Gyan.FFmpeg; Mac: brew install ffmpeg) y reinicia la terminal."
            )
            return
        _, output = run([path, "-version"])
        match = re.search(r"version\s+(\S+)", output)
        print(f"{OK}{tool} {match.group(1) if match else '(versión desconocida)'}")

    # Filtros que usa exportar_reel.py
    _, filters = run([shutil.which("ffmpeg"), "-hide_banner", "-filters"])
    for name, why in (
        ("subtitles", "subtítulos incrustados (necesita libass)"),
        ("zoompan", "zoom suave"),
        ("loudnorm", "normalizar el volumen"),
        ("silencedetect", "detectar silencios"),
    ):
        if re.search(rf"\s{name}\s", filters):
            print(f"{OK}filtro {name}: {why}")
        else:
            print(f"{FALTA}filtro {name}: {why}")
            problems.append(
                f"Tu FFmpeg no incluye el filtro '{name}'. Instala una compilación completa (full build)."
            )


def check_whisper(problems):
    try:
        import whisper  # noqa: F401
        from importlib.metadata import version

        print(f"{OK}openai-whisper {version('openai-whisper')}")
    except Exception:
        print(f"{FALTA}openai-whisper no está instalado")
        problems.append("Instala Whisper: pip install openai-whisper")


def main():
    print("Verificación del entorno para el kit de edición de Reels\n")
    problems = []
    check_python(problems)
    check_ffmpeg(problems)
    check_whisper(problems)
    print()
    if problems:
        print("Hay que resolver esto antes de editar:")
        for item in dict.fromkeys(problems):
            print(f" - {item}")
        sys.exit(1)
    print("Todo listo. Puedes pedir: edita mi reel")


if __name__ == "__main__":
    main()
