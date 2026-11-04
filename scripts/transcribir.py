import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import argparse
import json
from pathlib import Path

import whisper


ROOT = Path(__file__).resolve().parent.parent
CRUDO_DIR = (ROOT / "01-crudo").resolve()
SUBTITULOS_DIR = ROOT / "02-assets" / "subtitulos"


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


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe un video de 01-crudo con Whisper small."
    )
    parser.add_argument("video", help="Ruta al video dentro de 01-crudo/")
    args = parser.parse_args()

    try:
        video_path = resolve_video(args.video)
        print("Cargando Whisper (modelo small)...", flush=True)
        model = whisper.load_model("small")
        result = model.transcribe(
            str(video_path),
            fp16=False,
            word_timestamps=True,
        )

        SUBTITULOS_DIR.mkdir(parents=True, exist_ok=True)
        subtitle_path = SUBTITULOS_DIR / f"{video_path.stem}.srt"
        word_timings_path = SUBTITULOS_DIR / f"{video_path.stem}.words.json"
        words = []
        with subtitle_path.open("w", encoding="utf-8", newline="\n") as subtitle_file:
            for index, segment in enumerate(result["segments"], start=1):
                text = segment["text"].strip()
                subtitle_file.write(
                    f"{index}\n"
                    f"{timestamp(segment['start'])} --> "
                    f"{timestamp(segment['end'])}\n"
                    f"{text}\n\n"
                )
                words.extend(
                    {
                        "start": word["start"],
                        "end": word["end"],
                        "word": word["word"],
                    }
                    for word in segment.get("words", [])
                )

        with word_timings_path.open(
            "w", encoding="utf-8", newline="\n"
        ) as word_file:
            json.dump(words, word_file, ensure_ascii=False, indent=2)

        print(f"Segmentos detectados: {len(result['segments'])}")
        print(f"Subtítulos guardados en: {subtitle_path}")
        print(f"Tiempos por palabra guardados en: {word_timings_path}")
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"Error al transcribir: {error}\n")


if __name__ == "__main__":
    main()
