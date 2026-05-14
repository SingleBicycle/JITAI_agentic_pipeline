from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from .behavior_schema import EvidenceCard, SegmentProposal
from .utils import clamp, mean, unique_sorted
from .video_io import VideoSample


def extract_evidence_cards(
    video_path: str | Path,
    segments: List[SegmentProposal],
    samples: List[VideoSample],
    motion_series: List[Dict[str, float]],
    config: Dict[str, Any],
    output_dir: str | Path,
) -> List[EvidenceCard]:
    audio_profile = _extract_audio_profile(video_path, config, output_dir)
    cards: List[EvidenceCard] = []
    for idx, segment in enumerate(segments, start=1):
        segment_samples = [sample for sample in samples if segment.start_time <= sample.timestamp <= segment.end_time]
        segment_motion = [item for item in motion_series if segment.start_time <= item["time"] <= segment.end_time]
        motion = _summarize_motion(segment, segment_motion)
        people = _summarize_people(segment_samples, config)
        audio = _summarize_audio(segment, audio_profile)
        context_cfg = config.get("evidence", {}).get("context", {})
        context = {
            "scene_summary": context_cfg.get("scene_summary", "indoor interaction setting"),
            "objects": list(context_cfg.get("objects", [])),
        }
        representative_timestamps = _representative_timestamps(segment, motion)

        modalities_available = ["motion", "context"]
        missing_modalities = ["pose"]
        if people.get("source") == "detector":
            modalities_available.append("person_track")
        else:
            missing_modalities.append("person_track")
        if people.get("estimated_count") is not None:
            modalities_available.append("person_count")
        if audio.get("available"):
            modalities_available.append("audio_turn_taking")
        else:
            missing_modalities.append("audio_turn_taking")

        cards.append(
            EvidenceCard(
                card_id=f"evidence_{idx:03d}",
                segment_id=segment.segment_id,
                time_span=[round(segment.start_time, 2), round(segment.end_time, 2)],
                motion=motion,
                people=people,
                audio=audio,
                context=context,
                privacy={
                    "raw_video_released": False,
                    "derived_features_only": True,
                    "thumbnail_policy": "low-resolution privacy-safe internal artifacts only",
                },
                representative_timestamps=representative_timestamps,
                modalities_available=modalities_available,
                missing_modalities=missing_modalities,
                thumbnail_paths=[],
            )
        )
    return cards


def attach_thumbnail_paths(cards: List[EvidenceCard], thumbnail_manifest: List[Dict[str, Any]]) -> None:
    by_time = {round(float(item["timestamp"]), 2): item["path"] for item in thumbnail_manifest}
    for card in cards:
        card.thumbnail_paths = [
            by_time[round(float(timestamp), 2)]
            for timestamp in card.representative_timestamps
            if round(float(timestamp), 2) in by_time
        ]


def _summarize_motion(segment: SegmentProposal, segment_motion: List[Dict[str, float]]) -> Dict[str, Any]:
    if not segment_motion:
        return {
            "mean_motion": 0.0,
            "peak_motion": 0.0,
            "peak_time": round((segment.start_time + segment.end_time) / 2.0, 2),
            "activity_level": "low",
        }
    values = [float(item["motion"]) for item in segment_motion]
    peak_item = max(segment_motion, key=lambda item: float(item["motion"]))
    mean_motion = mean(values)
    peak_motion = float(peak_item["motion"])
    if peak_motion >= 0.12 or mean_motion >= 0.07:
        activity = "high"
    elif peak_motion >= 0.035 or mean_motion >= 0.018:
        activity = "medium"
    else:
        activity = "low"
    return {
        "mean_motion": round(mean_motion, 4),
        "peak_motion": round(peak_motion, 4),
        "peak_time": round(float(peak_item["time"]), 2),
        "activity_level": activity,
    }


def _summarize_people(samples: List[VideoSample], config: Dict[str, Any]) -> Dict[str, Any]:
    people_cfg = config.get("evidence", {}).get("people", {})
    enable_detector = bool(people_cfg.get("enable_detector", False))
    if enable_detector:
        counts = _detect_people_counts(samples[: min(5, len(samples))])
        if counts:
            estimated = int(round(float(np.median(counts))))
            return {
                "estimated_count": estimated,
                "track_summary": f"OpenCV HOG person detector estimated about {estimated} visible person(s).",
                "source": "detector",
            }

    if bool(people_cfg.get("assume_dyadic_if_no_detector", True)):
        default_count = int(people_cfg.get("default_count_if_detector_unavailable", 2))
        return {
            "estimated_count": default_count,
            "track_summary": "Person detector not used; demo config assumes a dyadic or small-group interaction for role coding.",
            "source": "config_assumption",
        }
    return {
        "estimated_count": None,
        "track_summary": "Person detector unavailable or disabled; participant count is unknown.",
        "source": "unavailable",
    }


def _detect_people_counts(samples: List[VideoSample]) -> List[int]:
    try:
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    except Exception:
        return []
    counts: List[int] = []
    for sample in samples:
        frame = sample.frame_bgr
        rects, _ = hog.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)
        counts.append(int(len(rects)))
    return counts


def _extract_audio_profile(video_path: str | Path, config: Dict[str, Any], output_dir: str | Path) -> Dict[str, Any]:
    audio_cfg = config.get("evidence", {}).get("audio", {})
    if not bool(audio_cfg.get("enabled", True)):
        return {"available": False, "reason": "audio disabled in config", "windows": [], "peak_times": []}
    if shutil.which("ffmpeg") is None:
        return {"available": False, "reason": "ffmpeg not found", "windows": [], "peak_times": []}

    sample_rate = int(audio_cfg.get("ffmpeg_sample_rate", 16000))
    window_seconds = float(audio_cfg.get("window_seconds", 1.0))
    with tempfile.TemporaryDirectory(dir=str(Path(output_dir))) as tmp:
        wav_path = Path(tmp) / "audio.wav"
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "wav",
            str(wav_path),
        ]
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not wav_path.exists():
            reason = proc.stderr.strip() or "ffmpeg could not extract an audio track"
            if "does not contain any stream" in reason or "Stream map" in reason:
                reason = "no audio stream detected"
            return {"available": False, "reason": reason, "windows": [], "peak_times": []}
        try:
            windows = _read_wav_energy_windows(wav_path, sample_rate, window_seconds)
        except Exception as exc:
            return {"available": False, "reason": f"audio read failed: {exc}", "windows": [], "peak_times": []}

    if not windows:
        return {"available": False, "reason": "audio track contained no readable samples", "windows": [], "peak_times": []}
    energies = np.array([item["rms"] for item in windows], dtype=float)
    threshold = max(0.01, float(np.mean(energies) + np.std(energies) * 0.5))
    peak_times = [item["time"] for item in windows if item["rms"] >= threshold]
    return {"available": True, "reason": "", "windows": windows, "peak_times": peak_times, "threshold": round(threshold, 5)}


def _read_wav_energy_windows(wav_path: Path, sample_rate: int, window_seconds: float) -> List[Dict[str, float]]:
    with wave.open(str(wav_path), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
        sample_width = wav.getsampwidth()
        channels = wav.getnchannels()
        actual_rate = wav.getframerate() or sample_rate
    if sample_width == 2:
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        samples = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        samples = (samples - 128.0) / 128.0
    if channels > 1:
        samples = samples.reshape((-1, channels)).mean(axis=1)
    samples_per_window = max(1, int(actual_rate * window_seconds))
    windows: List[Dict[str, float]] = []
    for start_idx in range(0, len(samples), samples_per_window):
        chunk = samples[start_idx : start_idx + samples_per_window]
        if len(chunk) == 0:
            continue
        rms = float(np.sqrt(np.mean(np.square(chunk))))
        windows.append({"time": round(start_idx / actual_rate, 2), "rms": round(clamp(rms, 0.0, 1.0), 5)})
    return windows


def _summarize_audio(segment: SegmentProposal, profile: Dict[str, Any]) -> Dict[str, Any]:
    if not profile.get("available"):
        return {
            "available": False,
            "activity": "unavailable",
            "turn_taking_summary": f"audio unavailable: {profile.get('reason', 'unknown reason')}",
            "peak_times": [],
        }
    windows = [item for item in profile.get("windows", []) if segment.start_time <= item["time"] <= segment.end_time]
    if not windows:
        return {
            "available": True,
            "activity": "silence",
            "turn_taking_summary": "no readable audio energy window in this segment",
            "peak_times": [],
        }
    threshold = float(profile.get("threshold", 0.01))
    peak_times = [round(float(item["time"]), 2) for item in windows if float(item["rms"]) >= threshold]
    max_rms = max(float(item["rms"]) for item in windows)
    if max_rms < 0.01:
        activity = "silence"
        summary = "low audio energy across the segment"
    elif len(peak_times) <= 2:
        activity = "speech-like"
        summary = "speech-like activity near " + ", ".join(f"{t:.1f}s" for t in peak_times[:4])
    else:
        activity = "noisy"
        summary = "multiple high-energy audio windows; could be speech, noise, or overlapping activity"
    return {
        "available": True,
        "activity": activity,
        "turn_taking_summary": summary,
        "peak_times": peak_times,
    }


def _representative_timestamps(segment: SegmentProposal, motion: Dict[str, Any]) -> List[float]:
    mid = (segment.start_time + segment.end_time) / 2.0
    peak = float(motion.get("peak_time", mid))
    return unique_sorted(
        [
            clamp(segment.start_time + 0.5, segment.start_time, segment.end_time),
            clamp(peak, segment.start_time, segment.end_time),
            clamp(mid, segment.start_time, segment.end_time),
        ]
    )
