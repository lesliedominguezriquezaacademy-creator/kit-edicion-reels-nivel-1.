import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "03-output"
TIMESTAMP_PATTERN = re.compile(
    r"^(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+"
    r"(\d{2}:\d{2}:\d{2},\d{3})(.*)$"
)


def require_command(name):
    command = shutil.which(name)
    if not command:
        raise RuntimeError(
            f"No se encontró '{name}' en PATH. Reinicia la terminal y vuelve a intentarlo."
        )
    return command


def timestamp_to_seconds(value):
    hours, minutes, remainder = value.split(":")
    seconds, milliseconds = remainder.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )


def seconds_to_timestamp(value):
    milliseconds = max(0, round(value * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def load_subtitles(subtitle_path):
    text = subtitle_path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    cues = []
    for block in blocks:
        lines = block.splitlines()
        timing_index = next(
            (index for index, line in enumerate(lines) if "-->" in line), None
        )
        if timing_index is None:
            continue
        match = TIMESTAMP_PATTERN.match(lines[timing_index])
        if not match:
            raise ValueError(f"Marca de tiempo SRT no válida: {lines[timing_index]}")
        cues.append(
            {
                "start": timestamp_to_seconds(match.group(1)),
                "end": timestamp_to_seconds(match.group(2)),
                "settings": match.group(3),
                "text": "\n".join(lines[timing_index + 1 :]).strip(),
            }
        )
    if not cues:
        raise ValueError(f"El archivo SRT no contiene subtítulos: {subtitle_path}")
    return cues


def remap_cues(cues, segments):
    remapped = []
    for cue in cues:
        for segment in segments:
            start = max(cue["start"], segment["source_start"])
            end = min(cue["end"], segment["source_end"])
            if end <= start:
                continue
            speed = segment.get("speed", 1.0)
            output_start = (
                segment["output_start"] + (start - segment["source_start"]) / speed
            )
            output_end = (
                segment["output_start"] + (end - segment["source_start"]) / speed
            )
            remapped.append(
                {
                    "start": output_start,
                    "end": output_end,
                    "settings": cue["settings"],
                    "text": cue["text"],
                }
            )
    remapped.sort(key=lambda cue: (cue["start"], cue["end"]))
    return remapped


def remap_words(words, segments):
    remapped = []
    for word in words:
        word_start = float(word["start"])
        word_end = float(word["end"])
        for segment in segments:
            start = max(word_start, segment["source_start"])
            end = min(word_end, segment["source_end"])
            if end <= start or end - start < (word_end - word_start) * 0.6:
                continue
            speed = segment.get("speed", 1.0)
            remapped.append(
                {
                    "start": segment["output_start"]
                    + (start - segment["source_start"]) / speed,
                    "end": segment["output_start"]
                    + (end - segment["source_start"]) / speed,
                    "word": word["word"].strip(),
                }
            )
            break
    return remapped


def group_word_cues(words, max_line_length=25, max_words=6):
    cues = []
    group = []
    current_line = ""
    line_count = 1

    def finish_group():
        nonlocal group, current_line, line_count
        if group:
            cues.append(
                {
                    "start": group[0]["start"],
                    "end": group[-1]["end"],
                    "words": group,
                }
            )
        group = []
        current_line = ""
        line_count = 1

    for word in words:
        token = word["word"].strip()
        if not token:
            continue
        candidate = f"{current_line} {token}".strip()
        line_break = False
        if group and (len(group) >= max_words or len(candidate) > max_line_length):
            if line_count == 1 and len(candidate) > max_line_length:
                line_count = 2
                current_line = ""
                line_break = True
            else:
                finish_group()
        elif group and not current_line:
            line_break = True

        if line_count == 2 and len(f"{current_line} {token}".strip()) > max_line_length:
            finish_group()
            line_break = False

        group.append({**word, "word": token, "line_break": line_break})
        current_line = f"{current_line} {token}".strip()
        if token.endswith((".", "!", "?", "…")):
            finish_group()
    finish_group()
    return cues


def ass_timestamp(seconds):
    centiseconds = max(0, round(seconds * 100))
    hours, centiseconds = divmod(centiseconds, 360_000)
    minutes, centiseconds = divmod(centiseconds, 6_000)
    whole_seconds, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{whole_seconds:02}.{centiseconds:02}"


def write_ass_subtitles(path, cues):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,56,&H0083BDD8,&H00EAF2F6,&H663A1F0B,&H663A1F0B,-1,0,0,0,100,100,0,0,3,10,0,2,88,88,620,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(header)
        for cue in cues:
            if cue.get("words"):
                karaoke = []
                for index, word in enumerate(cue["words"]):
                    next_start = (
                        cue["words"][index + 1]["start"]
                        if index + 1 < len(cue["words"])
                        else word["end"]
                    )
                    duration = max(1, round((next_start - word["start"]) * 100))
                    token = (
                        word["word"]
                        .replace("\\", "\\\\")
                        .replace("{", "\\{")
                        .replace("}", "\\}")
                    )
                    separator = (
                        r"\N"
                        if word.get("line_break")
                        else (" " if index else "")
                    )
                    karaoke.append(f"{{\\kf{duration}}}{separator}{token}")
                text = "".join(karaoke)
            else:
                lines = [
                    line.replace("\\", "\\\\")
                    .replace("{", "\\{")
                    .replace("}", "\\}")
                    for line in cue["text"].splitlines()
                ]
                text = r"\N".join(lines)
            file.write(
                f"Dialogue: 0,{ass_timestamp(cue['start'])},"
                f"{ass_timestamp(cue['end'])},Default,,0,0,0,,{text}\n"
            )


def fit_subtitles_to_safe_area(cues, max_line_length=34):
    fitted = []
    for cue in cues:
        words = cue["text"].split()
        if not words:
            continue

        chunks = []
        current_lines = []
        current_line = ""
        for word in words:
            candidate = f"{current_line} {word}".strip()
            if len(candidate) <= max_line_length:
                current_line = candidate
            elif not current_line:
                current_line = word
            elif len(current_lines) == 0:
                current_lines.append(current_line)
                current_line = word
            else:
                chunks.append("\n".join([*current_lines, current_line]))
                current_lines = []
                current_line = word
        if current_line:
            chunks.append("\n".join([*current_lines, current_line]))

        total_weight = sum(len(chunk.replace("\n", " ")) for chunk in chunks)
        elapsed = cue["end"] - cue["start"]
        consumed_weight = 0
        for chunk in chunks:
            weight = len(chunk.replace("\n", " "))
            start = cue["start"] + elapsed * consumed_weight / total_weight
            consumed_weight += weight
            end = cue["start"] + elapsed * consumed_weight / total_weight
            fitted.append(
                {
                    **cue,
                    "start": start,
                    "end": end,
                    "text": chunk,
                }
            )
    return fitted


def camera_motion_filter():
    # Movimiento continuo y suave: respiración de zoom 1.000 -> 1.025 -> 1.000
    # (máximo 2,5 %) con curva coseno, sin saltos ni pausas entre ciclos.
    # El zoompan trabaja sobre una imagen ampliada 4x (ver video_filter) para
    # que el redondeo a píxeles enteros no genere temblor.
    cycle_frames = 360  # 12 s a 30 fps por ciclo completo
    zoom = f"1+0.0125*(1-cos(2*PI*on/{cycle_frames}))"
    return (
        f"zoompan=z='{zoom}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
        f"d=1:s=1080x1920:fps=30"
    )


SOUND_VOLUME = 0.55


def has_audio(ffprobe, video_path):
    result = subprocess.run(
        [
            ffprobe, "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return bool(result.stdout.strip())


def get_duration(ffprobe, video_path):
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    duration = float(result.stdout.strip())
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError(f"Duración de video no válida: {video_path}")
    return duration


def main():
    parser = argparse.ArgumentParser(
        description="Exporta un video vertical 9:16 con subtítulos incrustados."
    )
    parser.add_argument("video", help="Ruta al video limpio")
    parser.add_argument("srt", help="Ruta al archivo de subtítulos .srt")
    parser.add_argument(
        "--output",
        help="Ruta opcional para guardar el Reel sin sobrescribir otro borrador",
    )
    parser.add_argument(
        "--sonido",
        help="Ruta a TU propio sonido de inicio (.wav/.mp3). Opcional: sin esta opción no se añade ningún sonido.",
    )
    args = parser.parse_args()

    try:
        video_path = Path(args.video).expanduser().resolve(strict=True)
        subtitle_path = Path(args.srt).expanduser().resolve(strict=True)
        if not video_path.is_file():
            raise ValueError(f"No es un archivo de video: {video_path}")
        if not subtitle_path.is_file():
            raise ValueError(f"No es un archivo de subtítulos: {subtitle_path}")
        if subtitle_path.suffix.lower() != ".srt":
            raise ValueError("El archivo de subtítulos debe tener extensión .srt")

        ffmpeg = require_command("ffmpeg")
        ffprobe = require_command("ffprobe")
        cues = load_subtitles(subtitle_path)
        manifest_path = video_path.with_name(f"{video_path.stem}.timeline.json")
        words_path = subtitle_path.with_name(f"{subtitle_path.stem}.words.json")
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            segments = manifest["segments"]
            if words_path.exists():
                words = json.loads(words_path.read_text(encoding="utf-8"))
                cues = group_word_cues(remap_words(words, segments))
            else:
                cues = remap_cues(cues, segments)
            if not cues:
                raise ValueError(
                    "Ningún subtítulo coincide con los segmentos conservados del video."
                )
        if not any(cue.get("words") for cue in cues):
            cues = fit_subtitles_to_safe_area(cues, max_line_length=25)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = (
            Path(args.output).expanduser().resolve()
            if args.output
            else OUTPUT_DIR / f"{video_path.stem}.mp4"
        )
        if output_path.suffix.lower() != ".mp4":
            raise ValueError("El archivo de salida debe tener extensión .mp4")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_name(
            f"{output_path.stem}.partial{output_path.suffix}"
        )
        video_duration = get_duration(ffprobe, video_path)
        fade_duration = min(0.45, video_duration / 4)
        fade_start = max(0, video_duration - fade_duration)
        video_filter = (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,scale=4320:7680:flags=bicubic,{camera_motion_filter()},"
            "subtitles=captions.ass,"
            f"fade=t=out:st={fade_start:.3f}:d={fade_duration:.3f}"
        )
        try:
            with tempfile.TemporaryDirectory(
                prefix="reel_subtitulos_"
            ) as temporary_dir:
                work_dir = Path(temporary_dir)
                write_ass_subtitles(work_dir / "captions.ass", cues)
                voice_chain = (
                    "loudnorm=I=-14:LRA=11:TP=-1.0,"
                    f"afade=t=out:st={fade_start:.3f}:d={fade_duration:.3f}"
                )
                sound_path = None
                if args.sonido and has_audio(ffprobe, video_path):
                    sound_path = Path(args.sonido).expanduser().resolve(strict=True)
                command = [
                    ffmpeg,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(video_path),
                ]
                if sound_path:
                    # Sonido de inicio propio mezclado bajo la voz.
                    command += [
                        "-i",
                        str(sound_path),
                        "-filter_complex",
                        f"[0:a]{voice_chain}[v];"
                        f"[1:a]volume={SOUND_VOLUME}[s];"
                        "[v][s]amix=inputs=2:duration=first:normalize=0,"
                        "alimiter=limit=0.95[a]",
                        "-vf",
                        video_filter,
                        "-map",
                        "0:v:0",
                        "-map",
                        "[a]",
                    ]
                else:
                    command += [
                        "-vf",
                        video_filter,
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a?",
                        "-af",
                        voice_chain,
                    ]
                command += [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-profile:a",
                    "aac_low",
                    "-b:a",
                    "192k",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-movflags",
                    "+faststart",
                    str(temporary_path),
                ]
                result = subprocess.run(
                    command,
                    check=False,
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        result.stderr.strip() or "FFmpeg terminó con error."
                    )

            temporary_path.replace(output_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        print(f"Reel exportado en: {output_path}")
    except (
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        parser.exit(1, f"Error al exportar el Reel: {error}\n")


if __name__ == "__main__":
    main()
