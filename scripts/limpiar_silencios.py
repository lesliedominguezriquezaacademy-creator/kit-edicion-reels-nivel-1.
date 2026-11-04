import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CRUDO_DIR = (ROOT / "01-crudo").resolve()
OUTPUT_DIR = ROOT / "02-assets" / "sin_silencios"
SILENCE_DURATION = 0.5
SILENCE_NOISE = "-35dB"
MIN_CLIP_DURATION = 0.02


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


def require_command(name):
    command = shutil.which(name)
    if not command:
        raise RuntimeError(
            f"No se encontró '{name}' en PATH. Reinicia la terminal y vuelve a intentarlo."
        )
    return command


def run(command):
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "FFmpeg/FFprobe terminó con error.")
    return result


def get_duration(ffprobe, video_path):
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError as error:
        raise RuntimeError(f"No se pudo leer la duración del video: {video_path}") from error
    if duration <= 0:
        raise RuntimeError(f"El video tiene una duración no válida: {video_path}")
    return duration


def has_audio(ffprobe, video_path):
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(video_path),
        ]
    )
    return bool(result.stdout.strip())


def detect_silences(ffmpeg, video_path, minimum_duration):
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(video_path),
            "-af",
            f"silencedetect=noise={SILENCE_NOISE}:"
            f"d={minimum_duration + 0.0001}",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg no pudo analizar el audio:\n{result.stderr.strip()}"
        )

    events = []
    for line in result.stderr.splitlines():
        start_match = re.search(r"silence_start:\s*(-?\d+(?:\.\d+)?)", line)
        end_match = re.search(r"silence_end:\s*(-?\d+(?:\.\d+)?)", line)
        if start_match:
            events.append(("start", float(start_match.group(1))))
        if end_match:
            events.append(("end", float(end_match.group(1))))

    silences = []
    pending_start = None
    for event, time in sorted(events, key=lambda item: item[1]):
        if event == "start":
            pending_start = time
        elif pending_start is not None:
            if time - pending_start > minimum_duration:
                silences.append((pending_start, time))
            pending_start = None
    if pending_start is not None:
        silences.append((pending_start, float("inf")))
    return silences


def merged_ranges(duration, ranges):
    normalized = []
    for start, end in ranges:
        start = min(max(start, 0.0), duration)
        end = min(max(end, start), duration)
        if end > start:
            normalized.append((start, end))

    merged = []
    for start, end in sorted(normalized):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def kept_segments(duration, cut_ranges):
    segments = []
    cursor = 0.0
    for silence_start, silence_end in cut_ranges:
        if silence_start - cursor >= MIN_CLIP_DURATION:
            segments.append((cursor, silence_start))
        cursor = max(cursor, silence_end)
    if duration - cursor >= MIN_CLIP_DURATION:
        segments.append((cursor, duration))
    return segments


def apply_speeds(segments, speed_ranges, default_speed):
    """Divide los segmentos en los límites de cada rango de velocidad y asigna
    la velocidad a cada trozo. Devuelve lista de (inicio, fin, velocidad)."""
    result = []
    for start, end in segments:
        cuts = sorted(
            {start, end}
            | {b for r in speed_ranges for b in r[:2] if start < b < end}
        )
        for piece_start, piece_end in zip(cuts, cuts[1:]):
            middle = (piece_start + piece_end) / 2
            speed = next(
                (r[2] for r in speed_ranges if r[0] <= middle < r[1]),
                default_speed,
            )
            result.append((piece_start, piece_end, speed))
    return result


def ffmpeg_number(value):
    return f"{value:.6f}"


def main():
    parser = argparse.ArgumentParser(
        description="Elimina los silencios largos de un video de 01-crudo/."
    )
    parser.add_argument("video", help="Ruta al video dentro de 01-crudo/")
    parser.add_argument(
        "--cut-range",
        nargs=2,
        type=float,
        action="append",
        default=[],
        metavar=("INICIO", "FIN"),
        help="Rango adicional, en segundos del original, que se eliminará. Repetible.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Velocidad de reproducción manteniendo el tono (entre 0.5 y 2.0).",
    )
    parser.add_argument(
        "--speed-range",
        nargs=3,
        type=float,
        action="append",
        default=[],
        metavar=("INICIO", "FIN", "VELOCIDAD"),
        help="Velocidad distinta para un tramo (segundos del original). Repetible.",
    )
    parser.add_argument(
        "--silence-duration",
        type=float,
        default=SILENCE_DURATION,
        help="Duración mínima, en segundos, para eliminar un silencio.",
    )
    args = parser.parse_args()

    try:
        video_path = resolve_video(args.video)
        if not 0.5 <= args.speed <= 2.0:
            raise ValueError("--speed debe estar entre 0.5 y 2.0")
        if any(
            start < 0 or end <= start or not 0.5 <= speed <= 2.0
            for start, end, speed in args.speed_range
        ):
            raise ValueError(
                "Cada --speed-range necesita inicio >= 0, fin > inicio y velocidad entre 0.5 y 2.0"
            )
        if args.silence_duration <= 0:
            raise ValueError("--silence-duration debe ser mayor que cero")
        if any(start < 0 or end <= start for start, end in args.cut_range):
            raise ValueError("Cada --cut-range necesita inicio >= 0 y fin > inicio")

        ffmpeg = require_command("ffmpeg")
        ffprobe = require_command("ffprobe")
        duration = get_duration(ffprobe, video_path)
        audio_available = has_audio(ffprobe, video_path)
        silences = (
            detect_silences(ffmpeg, video_path, args.silence_duration)
            if audio_available
            else []
        )
        all_cut_ranges = merged_ranges(duration, [*silences, *args.cut_range])
        source_segments = apply_speeds(
            kept_segments(duration, all_cut_ranges), args.speed_range, args.speed
        )
        if not source_segments:
            raise RuntimeError(
                "No quedaron clips después de quitar los silencios; "
                "revisa el audio o ajusta el umbral."
            )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / video_path.name
        temporary_path = OUTPUT_DIR / f"{video_path.stem}.partial{video_path.suffix}"
        manifest_path = OUTPUT_DIR / f"{video_path.stem}.timeline.json"
        temporary_manifest = OUTPUT_DIR / f"{video_path.stem}.timeline.partial.json"
        filters = []
        concat_inputs = []
        output_segments = []
        output_cursor = 0.0

        for index, (start, end, speed) in enumerate(source_segments):
            duration_kept = end - start
            filters.append(
                f"[0:v:0]trim=start={ffmpeg_number(start)}:"
                f"end={ffmpeg_number(end)},"
                f"setpts=(PTS-STARTPTS)/{ffmpeg_number(speed)}[v{index}]"
            )
            concat_inputs.append(f"[v{index}]")
            if audio_available:
                filters.append(
                    f"[0:a:0]atrim=start={ffmpeg_number(start)}:"
                    f"end={ffmpeg_number(end)},"
                    f"asetpts=PTS-STARTPTS,atempo={ffmpeg_number(speed)}[a{index}]"
                )
                concat_inputs.append(f"[a{index}]")
            output_segments.append(
                {
                    "source_start": start,
                    "source_end": end,
                    "output_start": output_cursor,
                    "output_end": output_cursor + duration_kept / speed,
                    "speed": speed,
                }
            )
            output_cursor += duration_kept / speed

        audio_count = 1 if audio_available else 0
        filters.append(
            "".join(concat_inputs)
            + f"concat=n={len(source_segments)}:v=1:a={audio_count}[vout]"
            + ("[aout]" if audio_available else "")
        )
        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
        ]
        if audio_available:
            command.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
        else:
            command.append("-an")
        command.extend(
            [
                "-map_metadata",
                "0",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-movflags",
                "+faststart",
                str(temporary_path),
            ]
        )

        try:
            run(command)
            temporary_path.replace(output_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        manifest = {
            "source_video": str(video_path),
            "cleaned_video": str(output_path),
            "segments": output_segments,
        }
        try:
            with temporary_manifest.open("w", encoding="utf-8", newline="\n") as file:
                json.dump(manifest, file, ensure_ascii=False, indent=2)
            temporary_manifest.replace(manifest_path)
        finally:
            if temporary_manifest.exists():
                temporary_manifest.unlink()

        final_duration = get_duration(ffprobe, output_path)
        print(f"Duración original: {duration:.2f} s")
        print(f"Duración final: {final_duration:.2f} s")
        print(f"Video limpio guardado en: {output_path}")
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"Error al limpiar silencios: {error}\n")


if __name__ == "__main__":
    main()
