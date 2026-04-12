import os
import logging
from dataclasses import dataclass
from typing import Optional

from AVA.prompt import PROMPTS
from audio_utils import AudioSignal, OpenAIAudioTranscriber, extract_audio_track
from jitai.policy import PolicyEngine
from jitai.utils import compact_json, dump_json, ensure_dir, extract_json_response, intervals_overlap
from llms.BaseModel import BaseVideoModel

logger = logging.getLogger("jitai")


DEFAULT_CHILD_PROFILE = {
    "child_id": "child_1",
    "age_years": None,
    "communication_level": "unspecified",
    "known_triggers": [],
    "preferred_supports": [],
    "notes": [],
}

DEFAULT_SCENE_CONTEXT = {
    "location": "unspecified",
    "participants": ["child_1", "caregiver_1"],
    "activity": "unspecified",
    "goal": "caregiver-facing observational support",
}

DEFAULT_INTERVENTION_LIBRARY = {
    "global": {
        "minimum_confidence": 0.45,
        "risk_thresholds": {"low": 0.35, "medium": 0.6, "high": 0.8},
        "max_actions_per_window": 1,
    },
    "interventions": [
        {
            "id": "co_regulation",
            "label": "Offer co-regulation support",
            "tags": ["co_regulation", "distress", "escalation"],
            "min_urgency": "medium",
            "cooldown_seconds": 45,
            "instructions": "Move closer, reduce verbal load, and offer a calm co-regulation cue.",
        },
        {
            "id": "reduce_demands",
            "label": "Reduce immediate task demands",
            "tags": ["reduce_demands", "task_overload", "avoidance"],
            "min_urgency": "medium",
            "cooldown_seconds": 60,
            "instructions": "Briefly reduce task complexity or pause the demand before re-engaging.",
        },
        {
            "id": "repair_joint_attention",
            "label": "Repair shared attention",
            "tags": ["repair_joint_attention", "shared_attention_absent"],
            "min_urgency": "low",
            "cooldown_seconds": 30,
            "instructions": "Re-enter the child’s focus with a simple shared-attention cue using an already salient object.",
        },
    ],
}


@dataclass
class ASDJITAIPipeline:
    video_path: str
    work_dir: str
    extract_model_name: str
    reasoner_model_name: str
    num_gpus: int = 1
    child_profile: Optional[dict] = None
    scene_context: Optional[dict] = None
    intervention_library: Optional[dict] = None
    window_seconds: int = 15
    stride_seconds: int = 5
    max_frames_per_window: int = 12
    rebuild_index: bool = False
    transcription_model: Optional[str] = None

    def __post_init__(self):
        from video_utils import VideoRepresentation

        self.child_profile = self.child_profile or DEFAULT_CHILD_PROFILE
        self.scene_context = self.scene_context or DEFAULT_SCENE_CONTEXT
        self.intervention_library = self.intervention_library or DEFAULT_INTERVENTION_LIBRARY
        self.video = VideoRepresentation(self.video_path, self.work_dir)
        self.output_dir = ensure_dir(os.path.join(self.work_dir, "jitai"))
        self.audio_dir = ensure_dir(os.path.join(self.work_dir, "audio"))
        self.extract_model = None
        self.reasoner_model = None
        self.ava = None
        self.audio_signal = None
        self.transcript = {"text": "", "segments": []}

    def _init_models(self):
        from llms.init_model import init_model

        if self.extract_model is None:
            self.extract_model = init_model(self.extract_model_name, self.num_gpus)
        if self.reasoner_model is None:
            if self.reasoner_model_name == self.extract_model_name:
                self.reasoner_model = self.extract_model
            else:
                self.reasoner_model = init_model(self.reasoner_model_name, self.num_gpus)

    def build_index(self):
        from AVA.ava import AVA

        self._init_models()
        self.ava = AVA(
            video=self.video,
            llm_model=self.extract_model,
            description_prompt_name="generate_description_dyadic",
            entity_prompt_name="entity_relation_extraction_role_aware",
        )
        graph_file = os.path.join(self.work_dir, "kg", "graph_event_knowledge_graph.graphml")
        if self.rebuild_index or not os.path.exists(graph_file):
            self.ava.construct()
        return self.ava

    def _load_cached_graph_views(self):
        if self.ava is None:
            self.build_index()
        return {
            "events": self.ava.events_vdb.get_datas(),
            "entities": self.ava.entities_vdb.get_datas(),
            "relations": self.ava.relations_vdb.get_datas(),
        }

    def _prepare_audio(self):
        audio_path = extract_audio_track(
            self.video_path,
            os.path.join(self.audio_dir, "audio.wav"),
        )
        self.audio_signal = AudioSignal(audio_path)

        transcription_path = os.path.join(self.audio_dir, "transcript.json")
        if self.transcription_model:
            try:
                transcriber = OpenAIAudioTranscriber(model=self.transcription_model)
                self.transcript = transcriber.transcribe(audio_path, transcription_path)
            except Exception as exc:
                logger.warning(f"Audio transcription unavailable: {exc}")
                self.transcript = {"text": "", "segments": [], "warning": str(exc)}
                dump_json(os.path.join(self.audio_dir, "transcript_warning.json"), self.transcript)

    def _iter_windows(self):
        duration = self.video.config["duration"]
        start = 0.0
        windows = []
        while start < duration:
            end = min(duration, start + self.window_seconds)
            windows.append((round(start, 3), round(end, 3)))
            if end >= duration:
                break
            start += self.stride_seconds
        return windows

    def _events_for_window(self, events, start_sec, end_sec):
        return [
            event
            for event in events
            if intervals_overlap(event["duration"][0], event["duration"][1], start_sec, end_sec)
        ]

    def _entities_for_window(self, entities, start_sec, end_sec):
        window_entities = []
        for entity in entities:
            durations = entity.get("durations", [])
            for duration in durations:
                if intervals_overlap(duration[0], duration[1], start_sec, end_sec):
                    window_entities.append(entity)
                    break
        return window_entities

    def _transcript_for_window(self, start_sec, end_sec):
        segments = []
        for segment in self.transcript.get("segments", []):
            if intervals_overlap(segment.get("start", 0), segment.get("end", 0), start_sec, end_sec):
                segments.append(segment)
        return segments

    def _graph_evidence_text(self, events, entities):
        lines = []
        for event in events[:8]:
            lines.append(
                f'event {event["duration"][0]}s-{event["duration"][1]}s: {event["description"]}'
            )
        for entity in entities[:8]:
            names = ", ".join(entity.get("names", [])) or entity.get("id", "")
            lines.append(
                f'entity {names} role={entity.get("role", "unknown")}: {"; ".join(entity.get("descriptions", [])[:2])}'
            )
        return "\n".join(lines) if lines else "no graph evidence retrieved for this window"

    def _audio_evidence(self, start_sec, end_sec):
        features = self.audio_signal.compute_features(start_sec, end_sec) if self.audio_signal else {}
        transcript_segments = self._transcript_for_window(start_sec, end_sec)
        transcript_text = ""
        if transcript_segments:
            transcript_text = " ".join(
                segment.get("text", "").strip() for segment in transcript_segments if segment.get("text")
            ).strip()
        elif self.transcript.get("text"):
            transcript_text = str(self.transcript.get("text", "")).strip()
        return {
            "features": features,
            "transcript_segments": transcript_segments,
            "transcript_text": transcript_text,
        }

    def _sample_frames(self, start_sec, end_sec):
        if not isinstance(self.reasoner_model, BaseVideoModel):
            return []
        frames, _, _ = self.video.get_frames_by_num(
            num_frames=self.max_frames_per_window,
            duration=(start_sec, end_sec),
        )
        return frames

    def _assess_window(self, graph_views, start_sec, end_sec):
        window_events = self._events_for_window(graph_views["events"], start_sec, end_sec)
        window_entities = self._entities_for_window(graph_views["entities"], start_sec, end_sec)
        audio_evidence = self._audio_evidence(start_sec, end_sec)
        graph_evidence_text = self._graph_evidence_text(window_events, window_entities)

        prompt = PROMPTS["jitai_window_assessment"].format(
            child_profile=compact_json(self.child_profile),
            scene_context=compact_json(self.scene_context),
            audio_evidence=compact_json(audio_evidence),
            graph_evidence=graph_evidence_text,
        )

        model_inputs = {"text": prompt}
        frames = self._sample_frames(start_sec, end_sec)
        if frames:
            model_inputs["video"] = frames

        raw_response = self.reasoner_model.generate_response(model_inputs)
        default_assessment = {
            "child_state": {
                "engagement": 0.0,
                "dysregulation_risk": 0.0,
                "affect": "unclear",
                "attention_target": "unclear",
                "state_summary": "",
                "observable_cues": [],
            },
            "caregiver_state": {
                "proximity": "unclear",
                "attention_to_child": "unclear",
                "response_latency_estimate_sec": None,
                "support_actions": [],
            },
            "interaction_state": {
                "shared_attention": "unclear",
                "turn_taking": "unclear",
                "escalation_trend": "unclear",
            },
            "risk_flags": [],
            "possible_triggers": [],
            "recommended_intervention_tags": [],
            "evidence": [],
            "confidence": 0.0,
            "uncertainty_notes": ["failed to parse model output"],
        }
        assessment = extract_json_response(raw_response, default_assessment)
        assessment["time_window"] = [start_sec, end_sec]
        assessment["audio_features"] = audio_evidence["features"]
        assessment["transcript_segments"] = audio_evidence["transcript_segments"]
        assessment["transcript_text"] = audio_evidence["transcript_text"]
        assessment["graph_event_count"] = len(window_events)
        assessment["graph_entity_count"] = len(window_entities)
        return assessment

    def _session_summary(self, timeline):
        prompt = PROMPTS["jitai_final_summary"].format(
            child_profile=compact_json(self.child_profile),
            scene_context=compact_json(self.scene_context),
            timeline_assessments=compact_json(
                [
                    {
                        "time_window": item["assessment"]["time_window"],
                        "risk": item["assessment"]["child_state"]["dysregulation_risk"],
                        "summary": item["assessment"]["child_state"]["state_summary"],
                        "flags": item["assessment"]["risk_flags"],
                        "action": item["policy"]["recommended_action_label"],
                    }
                    for item in timeline
                ]
            ),
        )
        raw_response = self.reasoner_model.generate_response({"text": prompt})
        default_summary = {
            "session_summary": "",
            "high_risk_windows": [],
            "common_triggers": [],
            "caregiver_strengths": [],
            "follow_up_focus": [],
        }
        return extract_json_response(raw_response, default_summary)

    def run(self, max_windows: Optional[int] = None):
        self.build_index()
        self._prepare_audio()
        graph_views = self._load_cached_graph_views()
        policy_engine = PolicyEngine(self.intervention_library)

        dump_json(
            os.path.join(self.output_dir, "config_snapshot.json"),
            {
                "video_path": self.video_path,
                "work_dir": self.work_dir,
                "extract_model": self.extract_model_name,
                "reasoner_model": self.reasoner_model_name,
                "window_seconds": self.window_seconds,
                "stride_seconds": self.stride_seconds,
                "max_frames_per_window": self.max_frames_per_window,
                "transcription_model": self.transcription_model,
                "child_profile": self.child_profile,
                "scene_context": self.scene_context,
                "intervention_library": self.intervention_library,
            },
        )

        timeline = []
        alerts = []
        windows = self._iter_windows()
        if max_windows is not None:
            windows = windows[:max_windows]

        windows_dir = ensure_dir(os.path.join(self.output_dir, "windows"))
        for index, (start_sec, end_sec) in enumerate(windows):
            assessment = self._assess_window(graph_views, start_sec, end_sec)
            policy = policy_engine.evaluate(assessment, start_sec, end_sec)
            window_result = {"assessment": assessment, "policy": policy}
            timeline.append(window_result)
            if policy["should_alert"]:
                alerts.append(window_result)
            dump_json(os.path.join(windows_dir, f"window_{index:04d}.json"), window_result)

        summary = self._session_summary(timeline)

        dump_json(os.path.join(self.output_dir, "jitai_timeline.json"), timeline)
        dump_json(os.path.join(self.output_dir, "jitai_alerts.json"), alerts)
        dump_json(os.path.join(self.output_dir, "jitai_summary.json"), summary)
        return {
            "timeline": timeline,
            "alerts": alerts,
            "summary": summary,
        }

    def answer_query(self, query: str, question_id: int = 0, with_frames: bool = True):
        if self.ava is None:
            self.build_index()
        self._init_models()
        self.ava.llm_model = self.reasoner_model
        self.ava.query_tree_search(query, question_id, re_process=True)
        return self.ava.generate_open_answer(
            query=query,
            question_id=question_id,
            with_frames=with_frames,
            re_process=True,
        )
