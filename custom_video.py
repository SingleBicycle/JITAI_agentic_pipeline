import argparse
import os
from collections import Counter

from jitai.pipeline import (
    ASDJITAIPipeline,
    DEFAULT_CHILD_PROFILE,
    DEFAULT_INTERVENTION_LIBRARY,
    DEFAULT_SCENE_CONTEXT,
)
from jitai.utils import dump_json, load_json


def resolve_model(name: str, vision_default: str):
    if name != "auto":
        return name
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini25pro"
    if os.getenv("OPENAI_API_KEY"):
        return "gpt4o"
    return vision_default


def _safe_load_json(path: str):
    if not os.path.exists(path):
        return None
    return load_json(path, None)


def _describe_transcript_status(work_dir: str):
    transcript_path = os.path.join(work_dir, "audio", "transcript.json")
    warning_path = os.path.join(work_dir, "audio", "transcript_warning.json")

    if os.path.exists(transcript_path):
        transcript = _safe_load_json(transcript_path) or {}
        segments = transcript.get("segments", []) or []
        text = (transcript.get("text") or "").strip()
        return {
            "status": "available",
            "path": transcript_path,
            "segment_count": len(segments),
            "has_text": bool(text),
        }

    if os.path.exists(warning_path):
        warning = _safe_load_json(warning_path) or {}
        return {
            "status": "warning",
            "path": warning_path,
            "message": warning.get("warning", ""),
            "segment_count": 0,
            "has_text": False,
        }

    return {
        "status": "not_requested",
        "path": None,
        "segment_count": 0,
        "has_text": False,
    }


def _top_nonempty(items, limit=3):
    counter = Counter(item for item in items if item)
    return [item for item, _ in counter.most_common(limit)]


def _summarize_child_behavior(timeline: list) -> dict:
    affects = _top_nonempty(
        [item["assessment"]["child_state"].get("affect") for item in timeline], limit=2
    )
    attention_targets = _top_nonempty(
        [item["assessment"]["child_state"].get("attention_target") for item in timeline], limit=2
    )
    cues = _top_nonempty(
        [
            cue
            for item in timeline
            for cue in item["assessment"]["child_state"].get("observable_cues", [])
        ],
        limit=4,
    )
    state_summaries = _top_nonempty(
        [item["assessment"]["child_state"].get("state_summary") for item in timeline], limit=2
    )
    return {
        "dominant_affect": affects,
        "main_attention_targets": attention_targets,
        "frequent_observable_cues": cues,
        "state_summaries": state_summaries,
    }


def _summarize_caregiver_behavior(timeline: list) -> dict:
    proximities = _top_nonempty(
        [item["assessment"]["caregiver_state"].get("proximity") for item in timeline], limit=2
    )
    attention_levels = _top_nonempty(
        [item["assessment"]["caregiver_state"].get("attention_to_child") for item in timeline],
        limit=2,
    )
    support_actions = _top_nonempty(
        [
            action
            for item in timeline
            for action in item["assessment"]["caregiver_state"].get("support_actions", [])
        ],
        limit=4,
    )
    return {
        "dominant_proximity": proximities,
        "attention_to_child": attention_levels,
        "frequent_support_actions": support_actions,
    }


def _build_review_recommendation(timeline: list, alerts: list, transcript_status: dict) -> dict:
    reasons = []
    risks = [
        float(item["assessment"]["child_state"].get("dysregulation_risk", 0.0))
        for item in timeline
    ]
    confidences = [
        float(item["assessment"].get("confidence", 0.0))
        for item in timeline
    ]

    max_risk = max(risks) if risks else 0.0
    unique_risks = len(set(round(value, 4) for value in risks)) if risks else 0
    unique_affects = len(
        set(item["assessment"]["child_state"].get("affect", "") for item in timeline)
    )

    if alerts:
        reasons.append("policy layer triggered one or more alerts")
    if max_risk >= 0.6:
        reasons.append("at least one window reached moderate or higher dysregulation risk")
    if transcript_status["status"] == "warning":
        reasons.append("audio transcription failed, so multimodal evidence is incomplete")
    if transcript_status["status"] == "not_requested":
        reasons.append("audio transcription was not requested")
    if timeline and unique_risks <= 1 and unique_affects <= 2:
        reasons.append("window-level risk and affect changed very little, which may indicate over-smoothed outputs")
    if confidences and sum(confidences) / len(confidences) < 0.55:
        reasons.append("model confidence stayed relatively low across the clip")

    if alerts or max_risk >= 0.6:
        level = "recommended"
    elif reasons:
        level = "recommended"
    else:
        level = "optional"

    return {
        "level": level,
        "reasons": reasons or ["no major risk flags detected in this clip"],
    }


def build_jitai_run_summary(result: dict, args) -> dict:
    timeline = result.get("timeline", [])
    alerts = result.get("alerts", [])
    summary = result.get("summary", {})
    transcript_status = _describe_transcript_status(args.work_dir)
    child_behavior = _summarize_child_behavior(timeline)
    caregiver_behavior = _summarize_caregiver_behavior(timeline)
    review_recommendation = _build_review_recommendation(timeline, alerts, transcript_status)

    max_risk = 0.0
    avg_risk = 0.0
    top_windows = []
    if timeline:
        risks = [
            float(item["assessment"]["child_state"].get("dysregulation_risk", 0.0))
            for item in timeline
        ]
        max_risk = max(risks)
        avg_risk = sum(risks) / len(risks)

        scored = sorted(
            timeline,
            key=lambda item: (
                float(item["assessment"]["child_state"].get("dysregulation_risk", 0.0)),
                float(item["assessment"].get("confidence", 0.0)),
            ),
            reverse=True,
        )
        for item in scored[:3]:
            assessment = item["assessment"]
            policy = item["policy"]
            top_windows.append(
                {
                    "time_window": assessment.get("time_window"),
                    "risk": assessment["child_state"].get("dysregulation_risk", 0.0),
                    "engagement": assessment["child_state"].get("engagement", 0.0),
                    "flags": assessment.get("risk_flags", []),
                    "recommended_tags": assessment.get("recommended_intervention_tags", []),
                    "should_alert": policy.get("should_alert", False),
                    "recommended_action_label": policy.get("recommended_action_label"),
                }
            )

    output_paths = {
        "timeline": os.path.join(args.work_dir, "jitai", "jitai_timeline.json"),
        "alerts": os.path.join(args.work_dir, "jitai", "jitai_alerts.json"),
        "summary": os.path.join(args.work_dir, "jitai", "jitai_summary.json"),
        "run_summary": os.path.join(args.work_dir, "jitai", "run_summary.json"),
    }

    return {
        "video_path": args.video_path,
        "work_dir": args.work_dir,
        "clip_id": os.path.basename(args.work_dir),
        "mode": args.mode,
        "extract_model": resolve_model(args.extract_model, "qwenvl"),
        "reasoner_model": resolve_model(args.reasoner_model, "qwenvl"),
        "window_seconds": args.window_seconds,
        "stride_seconds": args.stride_seconds,
        "window_count": len(timeline),
        "alert_count": len(alerts),
        "max_risk": round(max_risk, 4),
        "avg_risk": round(avg_risk, 4),
        "session_summary": summary.get("session_summary", ""),
        "high_risk_windows": summary.get("high_risk_windows", []),
        "common_triggers": summary.get("common_triggers", []),
        "caregiver_strengths": summary.get("caregiver_strengths", []),
        "follow_up_focus": summary.get("follow_up_focus", []),
        "transcript": transcript_status,
        "child_behavior_summary": child_behavior,
        "caregiver_behavior_summary": caregiver_behavior,
        "human_review_recommendation": review_recommendation,
        "top_windows": top_windows,
        "output_paths": output_paths,
    }


def print_jitai_run_summary(run_summary: dict):
    print("\n=== JITAI Run Complete ===")
    print(f"video: {run_summary['video_path']}")
    print(f"work_dir: {run_summary['work_dir']}")
    print(
        "windows={windows} alerts={alerts} max_risk={max_risk:.2f} avg_risk={avg_risk:.2f}".format(
            windows=run_summary["window_count"],
            alerts=run_summary["alert_count"],
            max_risk=run_summary["max_risk"],
            avg_risk=run_summary["avg_risk"],
        )
    )

    transcript = run_summary["transcript"]
    if transcript["status"] == "available":
        print(
            f"audio_transcript: available | segments={transcript['segment_count']} | path={transcript['path']}"
        )
    elif transcript["status"] == "warning":
        print(f"audio_transcript: warning | {transcript['message']}")
    else:
        print("audio_transcript: not requested")

    summary_text = run_summary.get("session_summary") or "no session summary generated"
    print(f"session_summary: {summary_text}")
    print(
        "human_review: {level} | reasons={reasons}".format(
            level=run_summary["human_review_recommendation"]["level"],
            reasons="; ".join(run_summary["human_review_recommendation"]["reasons"]),
        )
    )

    child_behavior = run_summary["child_behavior_summary"]
    caregiver_behavior = run_summary["caregiver_behavior_summary"]
    print(
        "child_behavior: affect={affect} | attention={attention} | cues={cues}".format(
            affect=", ".join(child_behavior["dominant_affect"]) or "unknown",
            attention=", ".join(child_behavior["main_attention_targets"]) or "unknown",
            cues=", ".join(child_behavior["frequent_observable_cues"]) or "none",
        )
    )
    print(
        "caregiver_behavior: proximity={proximity} | attention={attention} | actions={actions}".format(
            proximity=", ".join(caregiver_behavior["dominant_proximity"]) or "unknown",
            attention=", ".join(caregiver_behavior["attention_to_child"]) or "unknown",
            actions=", ".join(caregiver_behavior["frequent_support_actions"]) or "none",
        )
    )

    if run_summary["top_windows"]:
        print("top_windows:")
        for item in run_summary["top_windows"]:
            start, end = item["time_window"]
            flags = ", ".join(item["flags"]) if item["flags"] else "none"
            tags = ", ".join(item["recommended_tags"]) if item["recommended_tags"] else "none"
            action = item["recommended_action_label"] or "none"
            print(
                f"  {start:.1f}-{end:.1f}s | risk={item['risk']:.2f} | engagement={item['engagement']:.2f} | "
                f"flags={flags} | tags={tags} | alert={item['should_alert']} | action={action}"
            )

    print("outputs:")
    print(f"  timeline: {run_summary['output_paths']['timeline']}")
    print(f"  alerts: {run_summary['output_paths']['alerts']}")
    print(f"  summary: {run_summary['output_paths']['summary']}")
    print(f"  run_summary: {run_summary['output_paths']['run_summary']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_path", required=True)
    parser.add_argument("--work_dir", required=True)
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
    parser.add_argument(
        "--transcription_model",
        default=None,
        help="Optional OpenAI speech-to-text model such as gpt-4o-transcribe or gpt-4o-transcribe-diarize",
    )
    args = parser.parse_args()

    extract_model = resolve_model(args.extract_model, "qwenvl")
    reasoner_model = resolve_model(args.reasoner_model, "qwenvl")
    child_profile = load_json(args.profile_json, DEFAULT_CHILD_PROFILE)
    scene_context = load_json(args.scene_context_json, DEFAULT_SCENE_CONTEXT)
    intervention_library = load_json(args.intervention_json, DEFAULT_INTERVENTION_LIBRARY)

    pipeline = ASDJITAIPipeline(
        video_path=args.video_path,
        work_dir=args.work_dir,
        extract_model_name=extract_model,
        reasoner_model_name=reasoner_model,
        num_gpus=args.gpus,
        child_profile=child_profile,
        scene_context=scene_context,
        intervention_library=intervention_library,
        window_seconds=args.window_seconds,
        stride_seconds=args.stride_seconds,
        max_frames_per_window=args.max_frames_per_window,
        rebuild_index=args.rebuild_index,
        transcription_model=args.transcription_model,
    )

    if args.mode in {"jitai", "both"}:
        result = pipeline.run(max_windows=args.max_windows)
        run_summary = build_jitai_run_summary(result, args)
        dump_json(os.path.join(args.work_dir, "jitai", "run_summary.json"), run_summary)
        print_jitai_run_summary(run_summary)

    if args.mode in {"query", "both"}:
        if not args.query:
            raise ValueError("--query is required for query/both modes.")
        answer = pipeline.answer_query(args.query, question_id=args.query_id, with_frames=True)
        query_payload = {"query": args.query, "response": answer}
        query_path = os.path.join(args.work_dir, "jitai", f"query_{args.query_id}.json")
        dump_json(query_path, query_payload)
        print("\n=== Query Complete ===")
        print(f"query_id: {args.query_id}")
        print(f"query: {args.query}")
        print(f"output: {query_path}")
        if isinstance(answer, dict):
            answer_text = answer.get("answer") or answer.get("response") or str(answer)
        else:
            answer_text = str(answer)
        print(f"answer: {answer_text}")
