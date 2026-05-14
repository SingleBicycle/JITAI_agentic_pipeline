from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CONFIDENCE_LEVELS = {"low", "medium", "high"}
VERIFICATION_STATUS = {
    "pending",
    "accepted",
    "accepted_with_low_confidence",
    "rejected_missing_evidence",
}
PARTICIPANT_ROLES = {
    "target_participant",
    "social_partner",
    "speaker",
    "listener",
    "peer",
    "unknown",
}
OUTCOME_VALUES = {
    "engagement",
    "no response",
    "partial engagement",
    "repair",
    "transition",
    "uncertain engagement",
    "unknown",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_time_span(start: float, end: float, label: str) -> None:
    _require(start >= 0.0, f"{label} start_time must be >= 0")
    _require(end >= start, f"{label} end_time must be >= start_time")


def _validate_intervals(intervals: List[List[float]], label: str) -> None:
    _require(isinstance(intervals, list), f"{label} must be a list")
    for interval in intervals:
        _require(len(interval) == 2, f"{label} intervals must have [start, end]")
        _validate_time_span(float(interval[0]), float(interval[1]), label)


@dataclass
class SegmentProposal:
    segment_id: str
    start_time: float
    end_time: float
    proposal_reason: str
    motion_score: float

    def __post_init__(self) -> None:
        _validate_time_span(float(self.start_time), float(self.end_time), self.segment_id)
        _require(self.proposal_reason in {"motion_change", "fixed_window", "audio_motion_change"}, "invalid proposal_reason")
        _require(0.0 <= float(self.motion_score) <= 1.0, "motion_score must be between 0 and 1")


@dataclass
class EvidenceCard:
    card_id: str
    segment_id: str
    time_span: List[float]
    motion: Dict[str, Any]
    people: Dict[str, Any]
    audio: Dict[str, Any]
    context: Dict[str, Any]
    privacy: Dict[str, Any]
    representative_timestamps: List[float]
    modalities_available: List[str]
    missing_modalities: List[str]
    thumbnail_paths: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require(len(self.time_span) == 2, "EvidenceCard.time_span must have [start, end]")
        _validate_time_span(float(self.time_span[0]), float(self.time_span[1]), self.card_id)
        _require("mean_motion" in self.motion, "motion.mean_motion is required")
        _require("estimated_count" in self.people, "people.estimated_count is required")
        _require("available" in self.audio, "audio.available is required")
        _require("derived_features_only" in self.privacy, "privacy.derived_features_only is required")


@dataclass
class ParticipantRole:
    person_id: str
    role: str

    def __post_init__(self) -> None:
        _require(self.role in PARTICIPANT_ROLES, f"invalid participant role: {self.role}")


@dataclass
class BehaviorEpisode:
    episode_id: str
    source_segment_id: str
    start_time: float
    end_time: float
    participant_roles: List[ParticipantRole]
    interaction_context: str
    antecedent: str
    observable_behavior: str
    partner_response: str
    target_response: str
    outcome: str
    evidence_timestamp: List[List[float]]
    modalities_used: List[str]
    confidence: str
    uncertainty_reason: str
    verification_status: str = "pending"
    coding_mode: str = "rule_based"
    evidence_card_id: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_time_span(float(self.start_time), float(self.end_time), self.episode_id)
        _validate_intervals(self.evidence_timestamp, f"{self.episode_id}.evidence_timestamp")
        _require(self.confidence in CONFIDENCE_LEVELS, f"invalid confidence: {self.confidence}")
        _require(self.verification_status in VERIFICATION_STATUS, f"invalid verification_status: {self.verification_status}")
        _require(self.outcome in OUTCOME_VALUES, f"invalid outcome: {self.outcome}")
        roles = [r if isinstance(r, ParticipantRole) else ParticipantRole(**r) for r in self.participant_roles]
        self.participant_roles = roles


@dataclass
class BehaviorChain:
    chain_id: str
    episode_ids: List[str]
    time_span: List[float]
    summary: str
    evidence_timestamps: List[List[float]]
    confidence: str
    main_uncertainties: List[str]

    def __post_init__(self) -> None:
        _require(len(self.time_span) == 2, "BehaviorChain.time_span must have [start, end]")
        _validate_time_span(float(self.time_span[0]), float(self.time_span[1]), self.chain_id)
        _validate_intervals(self.evidence_timestamps, f"{self.chain_id}.evidence_timestamps")
        _require(self.confidence in CONFIDENCE_LEVELS, f"invalid confidence: {self.confidence}")


@dataclass
class BehaviorReport:
    demo_name: str
    generated_at: str
    video_metadata: Dict[str, Any]
    segment_count: int
    evidence_card_count: int
    accepted_evidence_card_count: int
    episodes: List[BehaviorEpisode]
    behavior_chains: List[BehaviorChain]
    privacy_note: str
    limitations: List[str]
    final_summary: str

    def __post_init__(self) -> None:
        _require(self.segment_count >= 0, "segment_count must be non-negative")
        _require(self.evidence_card_count >= 0, "evidence_card_count must be non-negative")
        _require(self.accepted_evidence_card_count >= 0, "accepted_evidence_card_count must be non-negative")
