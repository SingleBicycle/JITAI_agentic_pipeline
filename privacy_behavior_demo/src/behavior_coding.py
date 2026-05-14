from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
from PIL import Image

from .behavior_schema import BehaviorEpisode, EvidenceCard, ParticipantRole
from .utils import clamp


def code_behavior_episodes(
    evidence_cards: List[EvidenceCard],
    config: Dict[str, Any],
    video_path: str | Path | None = None,
) -> List[BehaviorEpisode]:
    coding_cfg = config.get("behavior_coding", {})
    requested_mode = str(coding_cfg.get("mode", "rule_based"))
    episodes: List[BehaviorEpisode] = []
    for idx, card in enumerate(evidence_cards, start=1):
        episode = None
        if requested_mode == "vlm":
            episode = _try_vlm_episode(card, idx, config, video_path)
            if episode is None:
                print(
                    f"[demo] vlm_fallback_rule_based | segment={card.segment_id}",
                    flush=True,
                )
        if episode is None and (requested_mode == "llm" or bool(coding_cfg.get("llm", {}).get("enabled", False))):
            episode = _try_llm_episode(card, idx, config)
        if episode is None:
            episode = _rule_based_episode(card, idx, config)
        episodes.append(episode)
    return episodes


def build_llm_prompt(card: EvidenceCard, episode_id: str) -> str:
    evidence_summary = {
        "episode_id": episode_id,
        "source_segment_id": card.segment_id,
        "time_span": card.time_span,
        "motion": card.motion,
        "people": card.people,
        "audio": card.audio,
        "context": card.context,
        "privacy": card.privacy,
        "modalities_available": card.modalities_available,
        "missing_modalities": card.missing_modalities,
    }
    return (
        "You are coding a privacy-preserving behavior episode from derived evidence only. "
        "Do not infer diagnoses, clinical recommendations, or identity. "
        "Return one JSON object matching the BehaviorEpisode fields: episode_id, source_segment_id, "
        "start_time, end_time, participant_roles, interaction_context, antecedent, observable_behavior, "
        "partner_response, target_response, outcome, evidence_timestamp, modalities_used, confidence, "
        "uncertainty_reason. Use generalized roles only.\n\n"
        f"Derived evidence:\n{json.dumps(evidence_summary, indent=2)}"
    )


def build_vlm_prompt(card: EvidenceCard, episode_id: str) -> str:
    evidence_summary = {
        "episode_id": episode_id,
        "source_segment_id": card.segment_id,
        "time_span": card.time_span,
        "motion": card.motion,
        "people": card.people,
        "audio": card.audio,
        "context": card.context,
        "privacy": card.privacy,
        "modalities_available": card.modalities_available,
        "missing_modalities": card.missing_modalities,
        "representative_timestamps": card.representative_timestamps,
    }
    schema_hint = {
        "episode_id": episode_id,
        "source_segment_id": card.segment_id,
        "start_time": card.time_span[0],
        "end_time": card.time_span[1],
        "participant_roles": [
            {"person_id": "p1", "role": "target_participant"},
            {"person_id": "p2", "role": "social_partner"},
        ],
        "interaction_context": "short generalized context label",
        "antecedent": "observable prior event or unknown",
        "observable_behavior": "visible behavior grounded in frames/evidence",
        "partner_response": "observable partner response or unknown",
        "target_response": "observable target response or unknown",
        "outcome": "engagement | no response | partial engagement | repair | transition | uncertain engagement | unknown",
        "evidence_timestamp": [card.time_span],
        "modalities_used": ["video", "motion", "context"],
        "confidence": "low | medium | high",
        "uncertainty_reason": "short uncertainty explanation",
    }
    return (
        "You are coding one privacy-preserving behavior episode from sampled video frames and derived evidence. "
        "This is behavior reasoning, not generic captioning. Do not identify actors by name. "
        "Do not infer diagnosis, mental state, treatment, or clinical labels. Use generalized roles only: "
        "target_participant, social_partner, speaker, listener, peer, unknown. "
        "Ground every behavior claim in the provided time window and evidence. "
        "Return valid JSON only matching this schema shape.\n\n"
        f"Required schema shape:\n{json.dumps(schema_hint, indent=2)}\n\n"
        f"Derived evidence:\n{json.dumps(evidence_summary, indent=2)}"
    )


def _try_vlm_episode(
    card: EvidenceCard,
    idx: int,
    config: Dict[str, Any],
    video_path: str | Path | None,
) -> Optional[BehaviorEpisode]:
    if video_path is None:
        return None
    vlm_cfg = config.get("behavior_coding", {}).get("vlm", {})
    env_key = str(vlm_cfg.get("env_key", "OPENAI_API_KEY"))
    api_key = os.environ.get(env_key)
    if not api_key:
        print(f"[demo] vlm_unavailable | missing_env={env_key}", flush=True)
        return None
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        print("[demo] vlm_unavailable | openai package import failed", flush=True)
        return None

    episode_id = f"demo_ep_{idx:03d}"
    frames = _sample_vlm_frames(
        video_path,
        card.representative_timestamps,
        max_frames=int(vlm_cfg.get("max_frames_per_episode", 4)),
        image_width=int(vlm_cfg.get("image_width", 384)),
    )
    if not frames:
        print(f"[demo] vlm_unavailable | no_frames segment={card.segment_id}", flush=True)
        return None

    content: List[Dict[str, Any]] = [{"type": "text", "text": build_vlm_prompt(card, episode_id)}]
    for item in frames:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{item['jpeg_base64']}",
                    "detail": str(vlm_cfg.get("detail", "low")),
                },
            }
        )

    try:
        client_kwargs = {"api_key": api_key}
        base_url = os.environ.get(str(vlm_cfg.get("base_url_env", "OPENAI_BASE_URL")))
        if base_url:
            client_kwargs["base_url"] = base_url
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=str(vlm_cfg.get("model", "gpt-4o")),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only JSON. Make conservative behavior claims grounded in video frames and timestamps."
                    ),
                },
                {"role": "user", "content": content},
            ],
            response_format={"type": "json_object"},
            temperature=float(vlm_cfg.get("temperature", 0.0)),
            max_tokens=int(vlm_cfg.get("max_tokens", 900)),
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        payload.setdefault("episode_id", episode_id)
        payload.setdefault("source_segment_id", card.segment_id)
        payload.setdefault("start_time", card.time_span[0])
        payload.setdefault("end_time", card.time_span[1])
        payload.setdefault("evidence_timestamp", [card.time_span])
        payload.setdefault("modalities_used", ["video", "motion", "context"])
        payload.setdefault("confidence", "medium")
        payload.setdefault("uncertainty_reason", "VLM output should be reviewed by a human coder.")
        payload.setdefault("evidence_card_id", card.card_id)
        payload.setdefault("coding_mode", "vlm")
        if "video" not in payload["modalities_used"]:
            payload["modalities_used"] = ["video"] + list(payload["modalities_used"])
        return BehaviorEpisode(**payload)
    except Exception as exc:
        print(f"[demo] vlm_error | segment={card.segment_id} | {exc}", flush=True)
        return None


def _try_llm_episode(card: EvidenceCard, idx: int, config: Dict[str, Any]) -> Optional[BehaviorEpisode]:
    llm_cfg = config.get("behavior_coding", {}).get("llm", {})
    env_key = str(llm_cfg.get("env_key", "OPENAI_API_KEY"))
    api_key = os.environ.get(env_key)
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None

    episode_id = f"demo_ep_{idx:03d}"
    prompt = build_llm_prompt(card, episode_id)
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=str(llm_cfg.get("model", "gpt-4o-mini")),
            messages=[
                {"role": "system", "content": "Return valid JSON only. Do not use raw frames."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        payload.setdefault("episode_id", episode_id)
        payload.setdefault("source_segment_id", card.segment_id)
        payload.setdefault("evidence_card_id", card.card_id)
        payload.setdefault("coding_mode", "llm")
        return BehaviorEpisode(**payload)
    except Exception:
        return None


def _rule_based_episode(card: EvidenceCard, idx: int, config: Dict[str, Any]) -> BehaviorEpisode:
    episode_id = f"demo_ep_{idx:03d}"
    start, end = float(card.time_span[0]), float(card.time_span[1])
    people_count = card.people.get("estimated_count")
    activity = str(card.motion.get("activity_level", "low"))
    audio_available = bool(card.audio.get("available"))
    audio_activity = str(card.audio.get("activity", "unavailable"))
    context_cfg = config.get("evidence", {}).get("context", {})
    interaction_context = str(context_cfg.get("interaction_context", "indoor dyadic interaction"))

    participant_roles = _participant_roles(people_count)
    modalities_used = ["motion", "context"]
    if people_count is not None:
        modalities_used.append("person_count")
    if audio_available:
        modalities_used.append("audio_turn_taking")

    if audio_available and audio_activity in {"speech-like", "noisy"} and activity in {"medium", "high"}:
        antecedent = "speech-like or partner activity is observed before or near a movement change"
        observable = "visible movement changes occur within the same behavior episode"
        partner_response = "possible initiation, wait, or repeated prompt inferred from audio-energy timing"
        target_response = "possible movement response after the inferred initiation"
        outcome = "partial engagement" if activity == "medium" else "engagement"
        confidence = "medium"
        uncertainty = "No transcript, identity label, or reliable role assignment is available."
    elif audio_available and audio_activity in {"speech-like", "noisy"} and activity == "low":
        antecedent = "speech-like activity is present with limited visible movement afterward"
        observable = "low motion follows the possible partner initiation"
        partner_response = "unknown or weakly observed"
        target_response = "possible delayed response or non-response"
        outcome = "no response"
        confidence = "low"
        uncertainty = "Audio is energy-based only and cannot confirm speech content or addressee."
    elif activity == "high" and (people_count or 0) >= 2:
        antecedent = "two-person interaction context is inferred from the configured demo setting"
        observable = "high motion suggests an interactive movement episode"
        partner_response = "unknown or weakly observed"
        target_response = "visible movement response occurs within the segment"
        outcome = "uncertain engagement"
        confidence = "medium"
        uncertainty = "Participant roles are inferred; no transcript or pose track is available."
    elif activity == "medium":
        antecedent = "a motion change suggests a possible interaction boundary"
        observable = "moderate visible movement occurs during the segment"
        partner_response = "unknown"
        target_response = "possible movement response"
        outcome = "uncertain engagement"
        confidence = "medium" if len(modalities_used) >= 3 else "low"
        uncertainty = "Evidence is based on coarse motion and context only."
    else:
        antecedent = "no clear antecedent is observable from derived features"
        observable = "low motion and limited derived evidence are observed"
        partner_response = "unknown"
        target_response = "unknown or not visible from derived features"
        outcome = "unknown"
        confidence = "low"
        uncertainty = "Derived features are sparse for this episode."

    return BehaviorEpisode(
        episode_id=episode_id,
        source_segment_id=card.segment_id,
        start_time=round(start, 2),
        end_time=round(end, 2),
        participant_roles=participant_roles,
        interaction_context=interaction_context,
        antecedent=antecedent,
        observable_behavior=observable,
        partner_response=partner_response,
        target_response=target_response,
        outcome=outcome,
        evidence_timestamp=[[round(start, 2), round(end, 2)]],
        modalities_used=modalities_used,
        confidence=confidence,
        uncertainty_reason=uncertainty,
        verification_status="pending",
        coding_mode="rule_based",
        evidence_card_id=card.card_id,
    )


def _participant_roles(people_count: Any) -> List[ParticipantRole]:
    try:
        count = int(people_count)
    except (TypeError, ValueError):
        count = 0
    if count >= 2:
        return [
            ParticipantRole(person_id="p1", role="target_participant"),
            ParticipantRole(person_id="p2", role="social_partner"),
        ]
    if count == 1:
        return [ParticipantRole(person_id="p1", role="target_participant")]
    return [ParticipantRole(person_id="p_unknown", role="unknown")]


def _sample_vlm_frames(
    video_path: str | Path,
    timestamps: List[float],
    max_frames: int,
    image_width: int,
) -> List[Dict[str, str]]:
    if max_frames <= 0:
        return []
    selected = timestamps[:max_frames]
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return []
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    output: List[Dict[str, str]] = []
    for timestamp in selected:
        frame_idx = int(round(float(timestamp) * fps))
        if total_frames:
            frame_idx = int(clamp(frame_idx, 0, max(0, total_frames - 1)))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = capture.read()
        if not ok:
            continue
        frame = _resize_width(frame, image_width)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=82)
        output.append(
            {
                "timestamp": f"{float(timestamp):.2f}",
                "jpeg_base64": base64.b64encode(buffer.getvalue()).decode("utf-8"),
            }
        )
    capture.release()
    return output


def _resize_width(frame, target_width: int):
    if target_width <= 0 or frame.shape[1] <= target_width:
        return frame
    ratio = target_width / float(frame.shape[1])
    target_height = max(1, int(round(frame.shape[0] * ratio)))
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
