# Privacy Behavior Demo

This is a minimal research demo for privacy-preserving dyadic or group behavior reasoning from one long-form interaction video.

The demo is not a generic captioning system. It proposes behavior episodes, extracts derived evidence, verifies that behavior claims are grounded in timestamped evidence, and exports a structured behavior report.

This demo does not diagnose ASD and does not provide clinical recommendations. It is designed so the same schema can later connect to ASD caregiver-child intervention research with human review.

## Install

From this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OpenCV is required for video loading, frame sampling, motion features, and thumbnail creation. `ffmpeg` is optional for audio-energy evidence.

## Run

Place a local video at `data/input/demo.mp4`, then run:

```bash
python -m src.main \
  --video data/input/demo.mp4 \
  --output outputs/demo \
  --config configs/demo_config.yaml
```

If the input video does not exist, the CLI exits cleanly with a clear message.

## VLM Evaluation Mode

For a VLM-backed run with sampled representative frames and derived evidence, use:

```bash
set -a
. ../.env
set +a

python -m src.main \
  --video /path/to/video.mp4 \
  --output outputs/vlm_demo \
  --config configs/vlm_eval_config.yaml
```

The VLM mode sends only a small number of sampled frames plus derived evidence summaries to the model. It still writes the same structured `BehaviorEpisode` and `BehaviorReport` schema. If the VLM call is unavailable, the runtime logs an explicit `vlm_error` or `vlm_fallback_rule_based` message.

## Expected Outputs

After one successful run:

```text
outputs/demo/
  segments.json
  evidence_cards.json
  behavior_report.json
  report.md
  timeline.html
  thumbnails/
```

`timeline.html` is a static file. No web server is required.

## Schema Summary

`SegmentProposal` stores candidate behavior episode windows:

```json
{
  "segment_id": "seg_001",
  "start_time": 0.0,
  "end_time": 12.0,
  "proposal_reason": "motion_change",
  "motion_score": 0.42
}
```

`EvidenceCard` stores privacy-preserving derived evidence:

```json
{
  "segment_id": "seg_001",
  "time_span": [0.0, 12.0],
  "motion": {"mean_motion": 0.32, "peak_motion": 0.76, "peak_time": 8.4, "activity_level": "medium"},
  "people": {"estimated_count": 2, "track_summary": "two visible people for most of the segment"},
  "audio": {"available": true, "turn_taking_summary": "speech-like activity near 4.2s and 9.1s"},
  "privacy": {"raw_video_released": false, "derived_features_only": true}
}
```

`BehaviorEpisode` stores structured behavior coding:

```json
{
  "episode_id": "demo_ep_001",
  "source_segment_id": "seg_001",
  "participant_roles": [
    {"person_id": "p1", "role": "target_participant"},
    {"person_id": "p2", "role": "social_partner"}
  ],
  "antecedent": "social partner appears to initiate an interaction",
  "observable_behavior": "visible movement and possible response occur within the segment",
  "partner_response": "unknown or weakly observed",
  "target_response": "possible movement response",
  "outcome": "uncertain engagement",
  "evidence_timestamp": [[0.0, 12.0]],
  "modalities_used": ["motion", "person_count"],
  "confidence": "medium",
  "verification_status": "accepted_with_low_confidence"
}
```

`BehaviorChain` groups adjacent related episodes into higher-level interaction sequences.

## Privacy Note

The pipeline prioritizes derived features: motion magnitude, optional person-count estimates, optional audio-energy summaries, and context labels. It does not release raw video. Thumbnails are low-resolution internal demo artifacts, and OpenCV face blur is attempted when available.

This repository tracks code, configuration, README, and empty `.gitkeep` placeholders only. Local videos under `data/input/` and generated artifacts under `outputs/` are ignored by Git.

## Limitations

- This is a research demo, not a benchmark.
- The default behavior coding mode is rule-based and intentionally conservative.
- Audio evidence is energy-based unless a future transcript module is connected.
- Pose, person tracking, VLM reasoning, and retrieval memory are extension points.
- Outputs should be reviewed by humans before being used in research coding.

## Later Connection To ASD Caregiver-Child Intervention

The demo uses generalized fields such as `target_participant`, `social_partner`, `partner_response`, `target_response`, `antecedent`, and `outcome`. In a later ASD caregiver-child workflow, those roles can map to child, caregiver, therapist, or peer while keeping the same timestamped evidence contract.

Potential replacements:

- Rule-based behavior coding can be replaced with VLM or LLM agent coding.
- Heuristic segmentation can be replaced with ActionFormer, TriDet, or another temporal action proposal model.
- Coarse motion features can be replaced with skeleton, pose, or optical-flow features.
- Local behavior memory can be backed by FAISS or another retrieval store.
