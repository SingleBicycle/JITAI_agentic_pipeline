import argparse
import json
import os
import subprocess
import sys


def load_manifest(manifest_path: str):
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def should_run_clip(clip: dict, args):
    clip_id = clip["clip_id"]
    if args.clip_ids:
        allowed = {int(item.strip()) for item in args.clip_ids.split(",") if item.strip()}
        return clip_id in allowed
    if args.max_clips is not None:
        return clip_id < args.max_clips
    return True


def safe_load_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_clip_summary(clip: dict, args):
    clip_id = clip["clip_id"]
    clip_work_dir = os.path.join(args.work_root, f"clip_{clip_id:03d}")
    run_summary_path = os.path.join(clip_work_dir, "jitai", "run_summary.json")
    run_summary = safe_load_json(run_summary_path)
    if run_summary is not None:
        run_summary["clip_id"] = clip_id
        run_summary["work_dir"] = clip_work_dir
        run_summary["video_path"] = clip["video_path"]
        return run_summary

    timeline = safe_load_json(os.path.join(clip_work_dir, "jitai", "jitai_timeline.json")) or []
    alerts = safe_load_json(os.path.join(clip_work_dir, "jitai", "jitai_alerts.json")) or []
    summary = safe_load_json(os.path.join(clip_work_dir, "jitai", "jitai_summary.json")) or {}
    transcript = safe_load_json(os.path.join(clip_work_dir, "audio", "transcript.json"))
    transcript_warning = safe_load_json(
        os.path.join(clip_work_dir, "audio", "transcript_warning.json")
    )

    if transcript is not None:
        transcript_status = {
            "status": "available",
            "path": os.path.join(clip_work_dir, "audio", "transcript.json"),
            "segment_count": len(transcript.get("segments", []) or []),
            "has_text": bool((transcript.get("text") or "").strip()),
        }
    elif transcript_warning is not None:
        transcript_status = {
            "status": "warning",
            "path": os.path.join(clip_work_dir, "audio", "transcript_warning.json"),
            "message": transcript_warning.get("warning", ""),
            "segment_count": 0,
            "has_text": False,
        }
    else:
        transcript_status = {
            "status": "not_requested",
            "path": None,
            "segment_count": 0,
            "has_text": False,
        }

    risks = [
        float(item["assessment"]["child_state"].get("dysregulation_risk", 0.0))
        for item in timeline
    ] if timeline else []

    return {
        "video_path": clip["video_path"],
        "work_dir": clip_work_dir,
        "clip_id": clip_id,
        "window_count": len(timeline),
        "alert_count": len(alerts),
        "max_risk": round(max(risks), 4) if risks else 0.0,
        "avg_risk": round(sum(risks) / len(risks), 4) if risks else 0.0,
        "session_summary": summary.get("session_summary", ""),
        "high_risk_windows": summary.get("high_risk_windows", []),
        "transcript": transcript_status,
    }


def print_batch_summary(batch_summary: dict):
    print("\n=== Batch Run Complete ===")
    print(f"work_root: {batch_summary['work_root']}")
    print(
        "clips={clips} windows={windows} alerts={alerts} max_risk={max_risk:.2f}".format(
            clips=batch_summary["completed_clip_count"],
            windows=batch_summary["total_windows"],
            alerts=batch_summary["total_alerts"],
            max_risk=batch_summary["max_risk"],
        )
    )
    print(
        "transcripts: available={available} warning={warning} not_requested={not_requested}".format(
            available=batch_summary["transcript_status_counts"]["available"],
            warning=batch_summary["transcript_status_counts"]["warning"],
            not_requested=batch_summary["transcript_status_counts"]["not_requested"],
        )
    )
    print(
        "review_levels: recommended={recommended} optional={optional} unknown={unknown}".format(
            recommended=batch_summary["review_level_counts"]["recommended"],
            optional=batch_summary["review_level_counts"]["optional"],
            unknown=batch_summary["review_level_counts"]["unknown"],
        )
    )
    print("clips:")
    for clip in batch_summary["clips"]:
        transcript_status = clip["transcript"]["status"]
        review = clip.get("human_review_recommendation", {}).get("level", "unknown")
        print(
            f"  clip_{clip['clip_id']:03d} | windows={clip['window_count']} | alerts={clip['alert_count']} | "
            f"max_risk={clip['max_risk']:.2f} | transcript={transcript_status} | review={review}"
        )
    print(f"batch_summary: {batch_summary['batch_summary_path']}")


def build_batch_summary(clip_summaries: list, args):
    transcript_status_counts = {"available": 0, "warning": 0, "not_requested": 0}
    review_level_counts = {"recommended": 0, "optional": 0, "unknown": 0}
    for summary in clip_summaries:
        status = summary.get("transcript", {}).get("status", "not_requested")
        transcript_status_counts[status] = transcript_status_counts.get(status, 0) + 1
        review_level = summary.get("human_review_recommendation", {}).get("level", "unknown")
        review_level_counts[review_level] = review_level_counts.get(review_level, 0) + 1

    max_risk = max((summary.get("max_risk", 0.0) for summary in clip_summaries), default=0.0)
    total_windows = sum(summary.get("window_count", 0) for summary in clip_summaries)
    total_alerts = sum(summary.get("alert_count", 0) for summary in clip_summaries)
    batch_summary_path = os.path.join(args.work_root, "batch_run_summary.json")

    return {
        "work_root": args.work_root,
        "manifest": args.manifest,
        "mode": args.mode,
        "completed_clip_count": len(clip_summaries),
        "total_windows": total_windows,
        "total_alerts": total_alerts,
        "max_risk": round(max_risk, 4),
        "transcript_status_counts": transcript_status_counts,
        "review_level_counts": review_level_counts,
        "clips": clip_summaries,
        "batch_summary_path": batch_summary_path,
    }


def run_clip(clip: dict, args):
    clip_id = clip["clip_id"]
    clip_video_path = clip["video_path"]
    clip_work_dir = os.path.join(args.work_root, f"clip_{clip_id:03d}")

    command = [
        sys.executable,
        "custom_video.py",
        "--video_path",
        clip_video_path,
        "--work_dir",
        clip_work_dir,
        "--mode",
        args.mode,
        "--extract_model",
        args.extract_model,
        "--reasoner_model",
        args.reasoner_model,
        "--window_seconds",
        str(args.window_seconds),
        "--stride_seconds",
        str(args.stride_seconds),
        "--max_frames_per_window",
        str(args.max_frames_per_window),
        "--gpus",
        str(args.gpus),
    ]

    if args.profile_json:
        command.extend(["--profile_json", args.profile_json])
    if args.scene_context_json:
        command.extend(["--scene_context_json", args.scene_context_json])
    if args.intervention_json:
        command.extend(["--intervention_json", args.intervention_json])
    if args.transcription_model:
        command.extend(["--transcription_model", args.transcription_model])
    if args.max_windows is not None:
        command.extend(["--max_windows", str(args.max_windows)])
    if args.rebuild_index:
        command.append("--rebuild_index")
    if args.query:
        command.extend(["--query", args.query, "--query_id", str(args.query_id)])

    if args.dry_run:
        print(" ".join(command))
        return None

    subprocess.run(command, check=True, cwd=args.project_root)
    return collect_clip_summary(clip, args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--project_root", default="/DATA/zihao/projects/Project-Ava")
    parser.add_argument("--work_root", required=True)
    parser.add_argument("--mode", choices=["jitai", "query", "both"], default="jitai")
    parser.add_argument("--extract_model", default="auto")
    parser.add_argument("--reasoner_model", default="auto")
    parser.add_argument("--profile_json")
    parser.add_argument("--scene_context_json")
    parser.add_argument("--intervention_json")
    parser.add_argument("--query")
    parser.add_argument("--query_id", type=int, default=0)
    parser.add_argument("--window_seconds", type=int, default=15)
    parser.add_argument("--stride_seconds", type=int, default=5)
    parser.add_argument("--max_frames_per_window", type=int, default=12)
    parser.add_argument("--gpus", type=int, default=1)
    parser.add_argument("--rebuild_index", action="store_true")
    parser.add_argument("--max_windows", type=int)
    parser.add_argument("--transcription_model", default=None)
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--clip_ids", default=None, help="Comma-separated clip ids to run, e.g. 0,2")
    parser.add_argument("--max_clips", type=int, default=None, help="Run only the first N clips")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    os.makedirs(args.work_root, exist_ok=True)

    completed = []
    for clip in manifest["clips"]:
        if not should_run_clip(clip, args):
            continue
        clip_summary = run_clip(clip, args)
        if clip_summary is not None:
            completed.append(clip_summary)

    if not args.dry_run:
        batch_summary = build_batch_summary(completed, args)
        with open(batch_summary["batch_summary_path"], "w", encoding="utf-8") as f:
            json.dump(batch_summary, f, indent=2, ensure_ascii=False)
        print_batch_summary(batch_summary)
