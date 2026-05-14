from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

from .behavior_coding import code_behavior_episodes
from .evidence_extraction import attach_thumbnail_paths, extract_evidence_cards
from .evidence_verifier import verify_episodes
from .report_generator import (
    build_behavior_report,
    merge_behavior_chains,
    write_behavior_report_json,
    write_markdown_report,
)
from .segment_proposal import propose_segments
from .utils import ensure_dir, read_config, to_plain_dict, write_json
from .video_io import compute_motion_series, load_video_metadata, sample_video_frames, save_privacy_safe_thumbnails
from .visualization import write_timeline_html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single-video privacy-preserving behavior episode demo")
    parser.add_argument("--video", required=True, help="Path to local input video, for example data/input/demo.mp4")
    parser.add_argument("--output", required=True, help="Output directory, for example outputs/demo")
    parser.add_argument("--config", required=True, help="YAML config path")
    return parser.parse_args()


def run_pipeline(video_path: str | Path, output_dir: str | Path, config_path: str | Path) -> Dict[str, str]:
    video_path = Path(video_path)
    output_dir = ensure_dir(output_dir)
    config = read_config(config_path)
    if not video_path.exists():
        raise FileNotFoundError(
            f"Input video does not exist: {video_path}. Put a local demo video at this path or pass --video to another file."
        )

    print(f"[demo] load_video {video_path}", flush=True)
    video_metadata = load_video_metadata(video_path)

    video_cfg = config.get("video", {})
    print("[demo] sample_frames", flush=True)
    samples = sample_video_frames(
        video_path,
        sample_fps=float(video_cfg.get("sample_fps", 1.0)),
        processing_width=int(video_cfg.get("processing_width", 320)),
        max_sampled_frames=int(video_cfg.get("max_sampled_frames", 3600)),
    )
    motion_series = compute_motion_series(samples)

    print("[demo] propose_segments", flush=True)
    segments = propose_segments(video_metadata, motion_series, config)
    write_json(
        output_dir / "segments.json",
        {
            "video_metadata": video_metadata,
            "segments": segments,
            "motion_sample_count": len(motion_series),
        },
    )

    print("[demo] extract_evidence", flush=True)
    evidence_cards = extract_evidence_cards(video_path, segments, samples, motion_series, config, output_dir)
    thumbnail_timestamps: List[float] = []
    for card in evidence_cards:
        thumbnail_timestamps.extend(card.representative_timestamps[: int(config.get("thumbnails", {}).get("max_per_episode", 3))])
    thumbnail_manifest = save_privacy_safe_thumbnails(video_path, thumbnail_timestamps, output_dir / "thumbnails", config)
    attach_thumbnail_paths(evidence_cards, thumbnail_manifest)
    write_json(
        output_dir / "evidence_cards.json",
        {
            "video_metadata": video_metadata,
            "evidence_cards": evidence_cards,
            "thumbnail_manifest": thumbnail_manifest,
        },
    )

    print("[demo] code_behavior_episodes", flush=True)
    episodes = code_behavior_episodes(evidence_cards, config, video_path=video_path)
    episodes = verify_episodes(episodes, segments, evidence_cards, config)

    print("[demo] merge_and_report", flush=True)
    chains = merge_behavior_chains(episodes, config)
    report = build_behavior_report(video_metadata, segments, evidence_cards, episodes, chains, config)
    write_behavior_report_json(output_dir / "behavior_report.json", report)
    write_markdown_report(output_dir / "report.md", report, segments, evidence_cards)
    write_timeline_html(
        output_dir / "timeline.html",
        float(video_metadata.get("duration") or 0.0),
        segments,
        evidence_cards,
        episodes,
        chains,
    )

    outputs = {
        "segments": str(output_dir / "segments.json"),
        "evidence_cards": str(output_dir / "evidence_cards.json"),
        "behavior_report": str(output_dir / "behavior_report.json"),
        "markdown_report": str(output_dir / "report.md"),
        "timeline": str(output_dir / "timeline.html"),
        "thumbnails": str(output_dir / "thumbnails"),
    }
    write_json(output_dir / "run_manifest.json", {"outputs": outputs, "config_path": str(config_path)})
    return outputs


def main() -> int:
    args = parse_args()
    try:
        outputs = run_pipeline(args.video, args.output, args.config)
    except FileNotFoundError as exc:
        print(f"[demo:error] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[demo:error] {exc}", file=sys.stderr)
        return 1
    print("[demo] complete", flush=True)
    for name, path in outputs.items():
        print(f"[demo] {name}: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
