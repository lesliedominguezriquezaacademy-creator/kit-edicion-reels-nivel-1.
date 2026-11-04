import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CRUDO_DIR = (ROOT / "01-crudo").resolve()
SCRIPTS_DIR = Path(__file__).resolve().parent


def resolve_video(value):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve(strict=True)

    if not path.is_file():
        raise ValueError(f"No es un archivo: {path}")
    if CRUDO_DIR not in path.parents:
        raise ValueError(f"El video debe estar dentro de {CRUDO_DIR}")
    return path


def run_step(label, script_path, *arguments):
    print(f"\n[{label}]", flush=True)
    subprocess.run(
        [sys.executable, str(script_path), *map(str, arguments)],
        check=True,
        cwd=ROOT,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe, limpia y exporta un Reel desde 01-crudo/."
    )
    parser.add_argument("video", help="Ruta al video dentro de 01-crudo/")
    args = parser.parse_args()

    try:
        video_path = resolve_video(args.video)
        subtitle_path = ROOT / "02-assets" / "subtitulos" / f"{video_path.stem}.srt"
        clean_video_path = (
            ROOT / "02-assets" / "sin_silencios" / video_path.name
        )
        final_video_path = ROOT / "03-output" / f"{video_path.stem}.mp4"

        run_step("Paso 1 de 3: transcripción", SCRIPTS_DIR / "transcribir.py", video_path)
        run_step(
            "Paso 2 de 3: limpieza de silencios",
            SCRIPTS_DIR / "limpiar_silencios.py",
            video_path,
        )
        run_step(
            "Paso 3 de 3: exportación vertical",
            SCRIPTS_DIR / "exportar_reel.py",
            clean_video_path,
            subtitle_path,
        )
        print(f"\nReel listo: {final_video_path}")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"\nPipeline detenido: {error}\n")


if __name__ == "__main__":
    main()
