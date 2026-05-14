from __future__ import annotations

from typing import Dict, List

from .behavior_schema import BehaviorEpisode, EvidenceCard, SegmentProposal
from .utils import confidence_downgrade


def verify_episodes(
    episodes: List[BehaviorEpisode],
    segments: List[SegmentProposal],
    evidence_cards: List[EvidenceCard],
    config: Dict,
) -> List[BehaviorEpisode]:
    segment_by_id = {segment.segment_id: segment for segment in segments}
    card_by_segment = {card.segment_id: card for card in evidence_cards}
    verifier_cfg = config.get("verifier", {})
    missing_threshold = int(verifier_cfg.get("missing_modality_low_confidence_threshold", 3))
    min_modalities = int(verifier_cfg.get("min_modalities_for_medium_confidence", 2))

    for episode in episodes:
        segment = segment_by_id.get(episode.source_segment_id)
        card = card_by_segment.get(episode.source_segment_id)
        reasons: List[str] = []
        status = "accepted"

        if not episode.evidence_timestamp:
            status = "rejected_missing_evidence"
            reasons.append("missing timestamped evidence")
        elif segment is None:
            status = "rejected_missing_evidence"
            reasons.append("source segment is missing")
        else:
            for interval in episode.evidence_timestamp:
                start, end = float(interval[0]), float(interval[1])
                if start < segment.start_time or end > segment.end_time or start > end:
                    status = "rejected_missing_evidence"
                    reasons.append("evidence timestamp falls outside the source segment")
                    break

        behavior_fields = [
            episode.interaction_context,
            episode.antecedent,
            episode.observable_behavior,
            episode.partner_response,
            episode.target_response,
            episode.outcome,
        ]
        if any(str(value).strip() for value in behavior_fields) and not episode.modalities_used:
            status = "rejected_missing_evidence"
            reasons.append("non-empty behavior fields have no listed modalities")

        missing_count = len(card.missing_modalities) if card else missing_threshold
        if status != "rejected_missing_evidence":
            if missing_count >= missing_threshold or len(episode.modalities_used) < min_modalities:
                episode.confidence = confidence_downgrade(episode.confidence)
                status = "accepted_with_low_confidence"
                reasons.append("confidence downgraded because derived modalities are missing")
            elif episode.confidence == "low":
                status = "accepted_with_low_confidence"

        if reasons:
            suffix = " ".join(reasons)
            if suffix not in episode.uncertainty_reason:
                episode.uncertainty_reason = f"{episode.uncertainty_reason} {suffix}".strip()
        episode.verification_status = status
    return episodes
