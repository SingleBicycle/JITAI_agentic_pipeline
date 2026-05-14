from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

import cv2
import numpy as np

from .utils import clamp, ensure_dir, unique_sorted


@dataclass
class VideoSample:
    timestamp: float
    frame_bgr: np.ndarray


def load_video_metadata(video_path: str | Path) -> Dict[str, Any]:
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Input video does not exist: {path}")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV could not open video: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    capture.release()

    if fps <= 0.0:
        fps = 30.0
    duration = total_frames / fps if total_frames > 0 else 0.0
    return {
        "path": str(path),
        "fps": round(fps, 3),
        "duration": round(duration, 3),
        "width": width,
        "height": height,
        "total_frames": total_frames,
    }


def sample_video_frames(
    video_path: str | Path,
    sample_fps: float = 1.0,
    processing_width: int = 320,
    max_sampled_frames: int = 3600,
) -> List[VideoSample]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV could not open video for sampling: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    sample_fps = max(0.1, float(sample_fps))
    frame_interval = max(1, int(round(fps / sample_fps)))

    samples: List[VideoSample] = []
    frame_idx = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_idx % frame_interval == 0:
            timestamp = frame_idx / fps
            samples.append(VideoSample(timestamp=round(timestamp, 3), frame_bgr=_resize_width(frame, processing_width)))
            if len(samples) >= max_sampled_frames:
                break
        frame_idx += 1
    capture.release()
    return samples


def compute_motion_series(samples: List[VideoSample]) -> List[Dict[str, float]]:
    series: List[Dict[str, float]] = []
    previous_gray = None
    for sample in samples:
        gray = cv2.cvtColor(sample.frame_bgr, cv2.COLOR_BGR2GRAY)
        if previous_gray is None:
            score = 0.0
        else:
            diff = cv2.absdiff(gray, previous_gray)
            score = float(np.mean(diff) / 255.0)
        previous_gray = gray
        series.append({"time": round(sample.timestamp, 3), "motion": round(clamp(score, 0.0, 1.0), 5)})
    return series


def save_privacy_safe_thumbnails(
    video_path: str | Path,
    timestamps: Iterable[float],
    output_dir: str | Path,
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    thumb_cfg = config.get("thumbnails", {})
    if not thumb_cfg.get("enabled", True):
        return []
    output_dir = ensure_dir(output_dir)
    width = int(thumb_cfg.get("width", 192))
    blur_faces = bool(thumb_cfg.get("blur_faces", True))
    cascade = _load_face_cascade() if blur_faces else None
    face_detection_available = cascade is not None

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV could not open video for thumbnails: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    duration_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    manifest: List[Dict[str, Any]] = []
    for index, timestamp in enumerate(unique_sorted(timestamps)):
        frame_idx = int(round(float(timestamp) * fps))
        if duration_frames:
            frame_idx = int(clamp(frame_idx, 0, max(0, duration_frames - 1)))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = capture.read()
        if not ok:
            continue
        frame = _resize_width(frame, width)
        face_count = 0
        if cascade is not None:
            frame, face_count = _blur_faces(frame, cascade)
        filename = f"thumb_{index:03d}_{float(timestamp):07.2f}s.jpg".replace(".", "_", 1)
        path = output_dir / filename
        cv2.imwrite(str(path), frame)
        if face_detection_available:
            note = "Face blur attempted with OpenCV Haar cascade; saved frame is low resolution."
            mode = "face_blur_attempted_lowres"
        else:
            note = "Face detection was unavailable; saved as low-resolution internal demo artifact."
            mode = "lowres_internal_demo_artifact"
        manifest.append(
            {
                "timestamp": round(float(timestamp), 2),
                "path": f"thumbnails/{filename}",
                "privacy_mode": mode,
                "face_detection_available": face_detection_available,
                "faces_blurred": int(face_count),
                "note": note,
            }
        )
    capture.release()

    notice = (
        "These thumbnails are internal demo artifacts. The pipeline prioritizes derived features. "
        "Frames are saved at low resolution; face blur is attempted when OpenCV face detection is available.\n"
    )
    (output_dir / "README.txt").write_text(notice, encoding="utf-8")
    return manifest


def _resize_width(frame: np.ndarray, target_width: int) -> np.ndarray:
    if target_width <= 0 or frame.shape[1] <= target_width:
        return frame
    ratio = target_width / float(frame.shape[1])
    target_height = max(1, int(round(frame.shape[0] * ratio)))
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)


def _load_face_cascade():
    try:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    except AttributeError:
        return None
    if not cascade_path.exists():
        return None
    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        return None
    return cascade


def _blur_faces(frame: np.ndarray, cascade) -> tuple[np.ndarray, int]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24))
    output = frame.copy()
    for x, y, w, h in faces:
        roi = output[y : y + h, x : x + w]
        kernel = max(15, int(min(w, h) // 2) * 2 + 1)
        output[y : y + h, x : x + w] = cv2.GaussianBlur(roi, (kernel, kernel), 0)
    return output, len(faces)
