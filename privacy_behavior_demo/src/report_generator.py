from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .behavior_schema import BehaviorChain, BehaviorEpisode, BehaviorReport, EvidenceCard, SegmentProposal
from .utils import confidence_min, now_iso, seconds_to_clock, write_json


def merge_behavior_chains(episodes: List[BehaviorEpisode], config: Dict[str, Any]) -> List[BehaviorChain]:
    report_cfg = config.get("report", {})
    merge_gap = float(report_cfg.get("chain_merge_gap_seconds", 5.0))
    sorted_episodes = sorted(episodes, key=lambda episode: episode.start_time)
    groups: List[List[BehaviorEpisode]] = []
    current: List[BehaviorEpisode] = []
    for episode in sorted_episodes:
        if not current:
            current = [episode]
            continue
        previous = current[-1]
        close = episode.start_time - previous.end_time <= merge_gap
        similar_context = _similar_context(previous.interaction_context, episode.interaction_context)
        if close and similar_context:
            current.append(episode)
        else:
            groups.append(current)
            current = [episode]
    if current:
        groups.append(current)

    chains: List[BehaviorChain] = []
    for idx, group in enumerate(groups, start=1):
        if len(group) == 1:
            summary = _single_episode_chain_summary(group[0])
        else:
            summary = "A possible initiation-response sequence or related interaction pattern occurs across adjacent episodes."
        evidence_timestamps: List[List[float]] = []
        for episode in group:
            evidence_timestamps.extend(episode.evidence_timestamp)
        uncertainties = _dedupe([episode.uncertainty_reason for episode in group if episode.uncertainty_reason])
        chains.append(
            BehaviorChain(
                chain_id=f"chain_{idx:03d}",
                episode_ids=[episode.episode_id for episode in group],
                time_span=[round(group[0].start_time, 2), round(group[-1].end_time, 2)],
                summary=summary,
                evidence_timestamps=evidence_timestamps,
                confidence=confidence_min(episode.confidence for episode in group),
                main_uncertainties=uncertainties[:5],
            )
        )
    return chains


def build_behavior_report(
    video_metadata: Dict[str, Any],
    segments: List[SegmentProposal],
    evidence_cards: List[EvidenceCard],
    episodes: List[BehaviorEpisode],
    chains: List[BehaviorChain],
    config: Dict[str, Any],
) -> BehaviorReport:
    accepted_statuses = {"accepted", "accepted_with_low_confidence"}
    accepted_cards = {
        episode.evidence_card_id
        for episode in episodes
        if episode.verification_status in accepted_statuses and episode.evidence_card_id
    }
    limitations = [
        "This demo uses coarse derived features and is not a full benchmark.",
        "Participant roles are generalized and may be inferred from configuration when detectors are unavailable.",
        "Audio evidence, when present, is energy-based and is not a transcript.",
        "The output is an evidence-grounded behavior report, not a clinical diagnosis or treatment recommendation.",
    ]
    privacy_note = (
        "Raw video is not released by the pipeline. The report prioritizes derived motion, person-count, "
        "audio-energy, and context features; thumbnails are low-resolution internal demo artifacts."
    )
    final_summary = (
        "This demo illustrates privacy-preserving behavior episode reasoning from a single interaction video. "
        "Each episode is represented with structured fields, timestamped evidence, confidence, and uncertainty."
    )
    return BehaviorReport(
        demo_name=str(config.get("demo", {}).get("name", "privacy_behavior_single_video_demo")),
        generated_at=now_iso(),
        video_metadata=video_metadata,
        segment_count=len(segments),
        evidence_card_count=len(evidence_cards),
        accepted_evidence_card_count=len(accepted_cards),
        episodes=episodes,
        behavior_chains=chains,
        privacy_note=privacy_note,
        limitations=limitations,
        final_summary=final_summary,
    )


def write_behavior_report_json(path: str | Path, report: BehaviorReport) -> None:
    write_json(path, report)


def write_markdown_report(
    path: str | Path,
    report: BehaviorReport,
    segments: List[SegmentProposal],
    evidence_cards: List[EvidenceCard],
) -> None:
    path = Path(path)
    card_by_segment = {card.segment_id: card for card in evidence_cards}
    lines: List[str] = []
    lines.append("# Privacy-Preserving Behavior Episode Demo Report")
    lines.append("")
    lines.append(report.final_summary)
    lines.append("")
    lines.append("## Video Metadata")
    lines.append("")
    lines.append(f"- Source: `{report.video_metadata.get('path', '')}`")
    lines.append(f"- Duration: {report.video_metadata.get('duration', 0)} seconds")
    lines.append(f"- FPS: {report.video_metadata.get('fps', 0)}")
    lines.append(f"- Resolution: {report.video_metadata.get('width', 0)} x {report.video_metadata.get('height', 0)}")
    lines.append(f"- Total frames: {report.video_metadata.get('total_frames', 0)}")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Proposed behavior episodes: {report.segment_count}")
    lines.append(f"- Evidence cards: {report.evidence_card_count}")
    lines.append(f"- Accepted evidence cards: {report.accepted_evidence_card_count}")
    lines.append(f"- Merged behavior chains: {len(report.behavior_chains)}")
    lines.append("")
    lines.append("## Proposed Segments")
    lines.append("")
    for segment in segments:
        lines.append(
            f"- `{segment.segment_id}` {seconds_to_clock(segment.start_time)} to {seconds_to_clock(segment.end_time)} "
            f"reason=`{segment.proposal_reason}` motion_score={segment.motion_score:.3f}"
        )
    lines.append("")
    lines.append("## Timeline Of Behavior Episodes")
    lines.append("")
    for episode in report.episodes:
        card = card_by_segment.get(episode.source_segment_id)
        modalities = ", ".join(episode.modalities_used)
        evidence = ", ".join(f"[{seconds_to_clock(a)}, {seconds_to_clock(b)}]" for a, b in episode.evidence_timestamp)
        lines.append(f"### {episode.episode_id}: {seconds_to_clock(episode.start_time)} to {seconds_to_clock(episode.end_time)}")
        lines.append("")
        lines.append(f"- Source segment: `{episode.source_segment_id}`")
        lines.append(f"- Context: {episode.interaction_context}")
        lines.append(f"- Antecedent: {episode.antecedent}")
        lines.append(f"- Observable behavior: {episode.observable_behavior}")
        lines.append(f"- Partner response: {episode.partner_response}")
        lines.append(f"- Target response: {episode.target_response}")
        lines.append(f"- Outcome: {episode.outcome}")
        lines.append(f"- Evidence timestamps: {evidence}")
        lines.append(f"- Modalities used: {modalities}")
        lines.append(f"- Confidence: {episode.confidence}")
        lines.append(f"- Verification: {episode.verification_status}")
        lines.append(f"- Uncertainty: {episode.uncertainty_reason}")
        if card:
            lines.append(f"- Derived motion: mean={card.motion.get('mean_motion')} peak={card.motion.get('peak_motion')} level={card.motion.get('activity_level')}")
            lines.append(f"- People evidence: {card.people.get('track_summary')}")
            lines.append(f"- Audio evidence: {card.audio.get('turn_taking_summary')}")
        lines.append("")
    lines.append("## Merged Behavior Chains")
    lines.append("")
    for chain in report.behavior_chains:
        evidence = ", ".join(f"[{seconds_to_clock(a)}, {seconds_to_clock(b)}]" for a, b in chain.evidence_timestamps)
        lines.append(f"- `{chain.chain_id}` episodes={chain.episode_ids} span={seconds_to_clock(chain.time_span[0])} to {seconds_to_clock(chain.time_span[1])}")
        lines.append(f"  Summary: {chain.summary}")
        lines.append(f"  Evidence: {evidence}")
        lines.append(f"  Confidence: {chain.confidence}")
        if chain.main_uncertainties:
            lines.append(f"  Main uncertainties: {'; '.join(chain.main_uncertainties)}")
    lines.append("")
    lines.append("## Privacy Note")
    lines.append("")
    lines.append(report.privacy_note)
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for item in report.limitations:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Final Demo Summary")
    lines.append("")
    lines.append("This report does not make clinical claims and does not provide treatment recommendations.")
    lines.append(report.final_summary)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _similar_context(left: str, right: str) -> bool:
    if left == right:
        return True
    left_tokens = set(left.lower().split())
    right_tokens = set(right.lower().split())
    return bool(left_tokens & right_tokens & {"interaction", "dyadic", "shared", "indoor", "activity"})


def _single_episode_chain_summary(episode: BehaviorEpisode) -> str:
    if episode.outcome in {"engagement", "partial engagement", "uncertain engagement"}:
        return "One evidence-grounded behavior episode suggests a possible interaction or response pattern."
    return "One evidence-grounded behavior episode is retained with uncertainty marked."


def _dedupe(values: List[str]) -> List[str]:
    output: List[str] = []
    seen = set()
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(key)
    return output
