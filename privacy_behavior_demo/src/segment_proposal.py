from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .behavior_schema import SegmentProposal
from .utils import clamp


def propose_segments(
    video_metadata: Dict[str, Any],
    motion_series: List[Dict[str, float]],
    config: Dict[str, Any],
    audio_peak_times: Optional[List[float]] = None,
) -> List[SegmentProposal]:
    segment_cfg = config.get("segment", {})
    mode = str(segment_cfg.get("mode", "motion"))
    duration = float(video_metadata.get("duration") or 0.0)
    if duration <= 0.0:
        return []
    if mode == "fixed_window" or len(motion_series) < 3:
        return _fixed_windows(duration, segment_cfg)

    motions = np.array([float(item["motion"]) for item in motion_series], dtype=float)
    times = np.array([float(item["time"]) for item in motion_series], dtype=float)
    mean_motion = float(np.mean(motions))
    std_motion = float(np.std(motions))
    threshold = max(
        float(segment_cfg.get("min_motion_peak_score", 0.015)),
        mean_motion + std_motion * float(segment_cfg.get("motion_peak_std_factor", 0.6)),
    )
    min_window = float(segment_cfg.get("min_window_seconds", 5.0))
    max_window = float(segment_cfg.get("max_window_seconds", 20.0))
    target_window = float(segment_cfg.get("target_window_seconds", 12.0))
    max_segments = int(segment_cfg.get("max_segments", 30))

    peak_indices = _local_motion_peaks(motions, threshold, min_distance_seconds=min_window / 2.0, times=times)
    candidates: List[SegmentProposal] = []
    for peak_idx in peak_indices[:max_segments]:
        peak_time = float(times[peak_idx])
        half_window = clamp(target_window / 2.0, min_window / 2.0, max_window / 2.0)
        start = clamp(peak_time - half_window, 0.0, max(0.0, duration - min_window))
        end = clamp(peak_time + half_window, min(duration, start + min_window), duration)
        if end - start > max_window:
            end = start + max_window
        reason = "motion_change"
        if _has_nearby_audio_peak(peak_time, audio_peak_times):
            reason = "audio_motion_change"
        candidates.append(
            SegmentProposal(
                segment_id="pending",
                start_time=round(start, 2),
                end_time=round(end, 2),
                proposal_reason=reason,
                motion_score=round(float(motions[peak_idx]), 4),
            )
        )

    if not candidates:
        return _fixed_windows(duration, segment_cfg)
    merged = _merge_close_candidates(candidates, segment_cfg)
    if not merged:
        merged = _fixed_windows(duration, segment_cfg)
    return _renumber(merged[:max_segments])


def _local_motion_peaks(
    motions: np.ndarray,
    threshold: float,
    min_distance_seconds: float,
    times: np.ndarray,
) -> List[int]:
    raw_indices: List[int] = []
    for idx in range(1, len(motions) - 1):
        if motions[idx] >= threshold and motions[idx] >= motions[idx - 1] and motions[idx] >= motions[idx + 1]:
            raw_indices.append(idx)
    if not raw_indices:
        raw_indices = [int(idx) for idx in np.argsort(motions)[::-1][:3] if motions[idx] >= threshold]

    selected: List[int] = []
    for idx in sorted(raw_indices, key=lambda i: motions[i], reverse=True):
        if all(abs(float(times[idx]) - float(times[prev])) >= min_distance_seconds for prev in selected):
            selected.append(idx)
    return sorted(selected, key=lambda i: float(times[i]))


def _has_nearby_audio_peak(peak_time: float, audio_peak_times: Optional[List[float]], window: float = 2.0) -> bool:
    if not audio_peak_times:
        return False
    return any(abs(float(t) - peak_time) <= window for t in audio_peak_times)


def _merge_close_candidates(candidates: List[SegmentProposal], segment_cfg: Dict[str, Any]) -> List[SegmentProposal]:
    if not candidates:
        return []
    gap = float(segment_cfg.get("merge_gap_seconds", 3.0))
    max_window = float(segment_cfg.get("max_window_seconds", 20.0))
    merged: List[SegmentProposal] = []
    current = candidates[0]
    for item in candidates[1:]:
        close = item.start_time - current.end_time <= gap
        combined_duration = item.end_time - current.start_time
        if close and combined_duration <= max_window:
            reason = (
                "audio_motion_change"
                if "audio_motion_change" in {current.proposal_reason, item.proposal_reason}
                else current.proposal_reason
            )
            current = SegmentProposal(
                segment_id="pending",
                start_time=current.start_time,
                end_time=item.end_time,
                proposal_reason=reason,
                motion_score=max(current.motion_score, item.motion_score),
            )
        else:
            merged.append(current)
            current = item
    merged.append(current)
    return merged


def _fixed_windows(duration: float, segment_cfg: Dict[str, Any]) -> List[SegmentProposal]:
    window = float(segment_cfg.get("fixed_window_seconds", segment_cfg.get("target_window_seconds", 12.0)))
    min_window = float(segment_cfg.get("min_window_seconds", 5.0))
    max_window = float(segment_cfg.get("max_window_seconds", 20.0))
    window = clamp(window, min_window, max_window)
    output: List[SegmentProposal] = []
    start = 0.0
    while start < duration:
        end = min(duration, start + window)
        if end - start < min_window and output:
            previous = output[-1]
            output[-1] = SegmentProposal(
                segment_id=previous.segment_id,
                start_time=previous.start_time,
                end_time=round(duration, 2),
                proposal_reason=previous.proposal_reason,
                motion_score=previous.motion_score,
            )
            break
        output.append(
            SegmentProposal(
                segment_id="pending",
                start_time=round(start, 2),
                end_time=round(end, 2),
                proposal_reason="fixed_window",
                motion_score=0.0,
            )
        )
        start = end
    return _renumber(output)


def _renumber(segments: List[SegmentProposal]) -> List[SegmentProposal]:
    return [
        SegmentProposal(
            segment_id=f"seg_{idx:03d}",
            start_time=segment.start_time,
            end_time=segment.end_time,
            proposal_reason=segment.proposal_reason,
            motion_score=segment.motion_score,
        )
        for idx, segment in enumerate(segments, start=1)
    ]
