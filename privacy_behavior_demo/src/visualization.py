from __future__ import annotations

import html
from pathlib import Path
from typing import List

from .behavior_schema import BehaviorChain, BehaviorEpisode, EvidenceCard, SegmentProposal
from .utils import seconds_to_clock


def write_timeline_html(
    path: str | Path,
    duration: float,
    segments: List[SegmentProposal],
    evidence_cards: List[EvidenceCard],
    episodes: List[BehaviorEpisode],
    chains: List[BehaviorChain],
) -> None:
    duration = max(float(duration), 1.0)
    card_by_segment = {card.segment_id: card for card in evidence_cards}
    rows: List[str] = []
    rows.append(_section("Segments", [_segment_bar(segment, duration) for segment in segments]))
    rows.append(_section("Evidence Cards", [_evidence_row(card, duration) for card in evidence_cards]))
    rows.append(_section("Behavior Episodes", [_episode_row(episode, duration) for episode in episodes]))
    rows.append(_section("Merged Chains", [_chain_row(chain, duration) for chain in chains]))
    thumb_rows = []
    for episode in episodes:
        card = card_by_segment.get(episode.source_segment_id)
        if not card or not card.thumbnail_paths:
            continue
        images = " ".join(
            f'<img src="{html.escape(path)}" alt="privacy-safe thumbnail for {html.escape(episode.episode_id)}">'
            for path in card.thumbnail_paths
        )
        thumb_rows.append(f"<div class=\"thumb-row\"><strong>{html.escape(episode.episode_id)}</strong>{images}</div>")
    if thumb_rows:
        rows.append(_section("Privacy-Safe Thumbnails", thumb_rows))

    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Privacy Behavior Timeline</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #202124; background: #fafafa; }}
    h1 {{ font-size: 24px; margin-bottom: 4px; }}
    h2 {{ font-size: 18px; margin-top: 28px; }}
    .note {{ color: #5f6368; margin-bottom: 20px; }}
    .track {{ position: relative; height: 36px; border: 1px solid #d8dee4; background: #fff; margin: 8px 0 14px; border-radius: 6px; overflow: hidden; }}
    .bar {{ position: absolute; top: 5px; height: 24px; border-radius: 4px; color: #111; font-size: 12px; line-height: 24px; padding-left: 6px; box-sizing: border-box; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .segment {{ background: #a7d8ff; }}
    .evidence {{ background: #c6e7c8; }}
    .episode.low {{ background: #f8d7da; }}
    .episode.medium {{ background: #ffe6a3; }}
    .episode.high {{ background: #b7e4c7; }}
    .chain {{ background: #d7c9ff; }}
    .meta {{ font-size: 13px; color: #3c4043; margin-top: -6px; margin-bottom: 14px; }}
    .ticks {{ display: flex; justify-content: space-between; color: #6a737d; font-size: 12px; }}
    .thumb-row {{ margin: 10px 0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
    .thumb-row img {{ width: 128px; border: 1px solid #d8dee4; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Privacy-Preserving Behavior Episode Timeline</h1>
  <div class="note">Duration: {html.escape(seconds_to_clock(duration))}. Static demo visualization generated from derived evidence and verified behavior episodes.</div>
  <div class="ticks"><span>0</span><span>{html.escape(seconds_to_clock(duration / 2.0))}</span><span>{html.escape(seconds_to_clock(duration))}</span></div>
  {''.join(rows)}
</body>
</html>
"""
    Path(path).write_text(content, encoding="utf-8")


def _section(title: str, rows: List[str]) -> str:
    body = "".join(rows) if rows else "<p class=\"meta\">No entries.</p>"
    return f"<h2>{html.escape(title)}</h2>{body}"


def _segment_bar(segment: SegmentProposal, duration: float) -> str:
    label = f"{segment.segment_id} {segment.proposal_reason} motion={segment.motion_score:.2f}"
    return _bar(segment.start_time, segment.end_time, duration, label, "segment")


def _evidence_row(card: EvidenceCard, duration: float) -> str:
    start, end = float(card.time_span[0]), float(card.time_span[1])
    label = f"{card.card_id} motion={card.motion.get('activity_level')} evidence={card.representative_timestamps}"
    meta = (
        f"<div class=\"meta\">{html.escape(card.segment_id)} modalities={html.escape(', '.join(card.modalities_available))} "
        f"missing={html.escape(', '.join(card.missing_modalities))}</div>"
    )
    return _bar(start, end, duration, label, "evidence") + meta


def _episode_row(episode: BehaviorEpisode, duration: float) -> str:
    label = f"{episode.episode_id} {episode.confidence} {episode.outcome}"
    meta = (
        f"<div class=\"meta\">{html.escape(episode.verification_status)} evidence="
        f"{html.escape(str(episode.evidence_timestamp))} uncertainty={html.escape(episode.uncertainty_reason)}</div>"
    )
    return _bar(episode.start_time, episode.end_time, duration, label, f"episode {episode.confidence}") + meta


def _chain_row(chain: BehaviorChain, duration: float) -> str:
    label = f"{chain.chain_id} {chain.confidence} {chain.episode_ids}"
    meta = f"<div class=\"meta\">{html.escape(chain.summary)} evidence={html.escape(str(chain.evidence_timestamps))}</div>"
    return _bar(chain.time_span[0], chain.time_span[1], duration, label, "chain") + meta


def _bar(start: float, end: float, duration: float, label: str, css_class: str) -> str:
    left = max(0.0, min(100.0, (float(start) / duration) * 100.0))
    width = max(0.5, min(100.0 - left, ((float(end) - float(start)) / duration) * 100.0))
    return (
        "<div class=\"track\">"
        f"<div class=\"bar {html.escape(css_class)}\" style=\"left:{left:.3f}%;width:{width:.3f}%\">"
        f"{html.escape(label)}</div></div>"
    )
