import argparse
import json
import os
import re
import subprocess
from pathlib import Path


def sanitize_stem(path: str) -> str:
    stem = Path(path).stem
    stem = re.sub(r"[^\w\s-]", "_", stem, flags=re.UNICODE)
    stem = re.sub(r"\s+", "_", stem.strip())
    stem = re.sub(r"_+", "_", stem)
    return stem.lower().strip("_")


def probe_duration(video_path: str) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def build_clip_ranges(duration: float, clip_seconds: int, overlap_seconds: int):
    ranges = []
    start_sec = 0.0
    step = clip_seconds - overlap_seconds
    if step <= 0:
        raise ValueError("clip_seconds must be larger than overlap_seconds.")

    while start_sec < duration:
        end_sec = min(duration, start_sec + clip_seconds)
        ranges.append((round(start_sec, 3), round(end_sec, 3)))
        if end_sec >= duration:
            break
        start_sec += step
    return ranges


def split_video(video_path: str, output_root: str, clip_seconds: int, overlap_seconds: int):
    duration = probe_duration(video_path)
    safe_name = sanitize_stem(video_path)
    clips_dir = os.path.join(output_root, safe_name)
    os.makedirs(clips_dir, exist_ok=True)

    clip_ranges = build_clip_ranges(duration, clip_seconds, overlap_seconds)
    manifest = {
        "source_video": os.path.abspath(video_path),
        "duration_seconds": duration,
        "clip_seconds": clip_seconds,
        "overlap_seconds": overlap_seconds,
        "clips_dir": os.path.abspath(clips_dir),
        "clips": [],
    }

    for index, (start_sec, end_sec) in enumerate(clip_ranges):
        output_path = os.path.join(clips_dir, f"clip_{index:03d}.mp4")
        if not os.path.exists(output_path):
            command = [
                "ffmpeg",
                "-y",
                "-ss",
                str(start_sec),
                "-i",
                video_path,
                "-t",
                str(round(end_sec - start_sec, 3)),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                output_path,
            ]
            subprocess.run(command, check=True, capture_output=True)

        manifest["clips"].append(
            {
                "clip_id": index,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(end_sec - start_sec, 3),
                "video_path": os.path.abspath(output_path),
            }
        )

    manifest_path = os.path.join(clips_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest_path


def extract_clip_audio(clip_path: str, wav_path: str, sample_rate: int = 16000):
    os.makedirs(os.path.dirname(wav_path), exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        clip_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        wav_path,
    ]
    subprocess.run(command, check=True, capture_output=True)


def maybe_extract_audio(manifest_path: str, sample_rate: int = 16000):
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    audio_dir = os.path.join(manifest["clips_dir"], "audio")
    for clip in manifest["clips"]:
        wav_path = os.path.join(audio_dir, f'clip_{clip["clip_id"]:03d}.wav')
        if not os.path.exists(wav_path):
            extract_clip_audio(clip["video_path"], wav_path, sample_rate=sample_rate)
        clip["audio_path"] = os.path.abspath(wav_path)

    manifest["audio_sample_rate"] = sample_rate
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_path", required=True)
    parser.add_argument("--output_root", required=True)
    parser.add_argument("--clip_seconds", type=int, default=180)
    parser.add_argument("--overlap_seconds", type=int, default=0)
    parser.add_argument("--extract_audio", action="store_true")
    parser.add_argument("--audio_sample_rate", type=int, default=16000)
    args = parser.parse_args()

    manifest_path = split_video(
        video_path=args.video_path,
        output_root=args.output_root,
        clip_seconds=args.clip_seconds,
        overlap_seconds=args.overlap_seconds,
    )
    if args.extract_audio:
        manifest_path = maybe_extract_audio(
            manifest_path=manifest_path,
            sample_rate=args.audio_sample_rate,
        )
    print(manifest_path)
