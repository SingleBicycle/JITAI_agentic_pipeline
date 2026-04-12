import contextlib
import json
import math
import os
import subprocess
import wave
from array import array
from typing import Optional


def extract_audio_track(video_path: str, output_path: str, sample_rate: int = 16000) -> str:
    if os.path.exists(output_path):
        return output_path

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        output_path,
    ]
    subprocess.run(command, check=True, capture_output=True)
    return output_path


class AudioSignal:
    def __init__(self, wav_path: str):
        with contextlib.closing(wave.open(wav_path, "rb")) as wav_file:
            self.sample_rate = wav_file.getframerate()
            self.sample_width = wav_file.getsampwidth()
            self.frame_count = wav_file.getnframes()
            self.duration = self.frame_count / float(self.sample_rate)
            raw = wav_file.readframes(self.frame_count)

        if self.sample_width != 2:
            raise ValueError("Only 16-bit PCM wav files are supported.")

        self.samples = array("h")
        self.samples.frombytes(raw)

    def _slice(self, start_sec: float, end_sec: float):
        start_idx = max(0, int(start_sec * self.sample_rate))
        end_idx = min(len(self.samples), int(end_sec * self.sample_rate))
        if end_idx <= start_idx:
            return []
        return self.samples[start_idx:end_idx]

    def compute_features(self, start_sec: float, end_sec: float) -> dict:
        samples = self._slice(start_sec, end_sec)
        if not samples:
            return {
                "rms": 0.0,
                "peak": 0.0,
                "silence_ratio": 1.0,
            }

        float_samples = [sample / 32768.0 for sample in samples]
        rms = math.sqrt(sum(sample * sample for sample in float_samples) / len(float_samples))
        peak = max(abs(sample) for sample in float_samples)
        silence_threshold = 0.015
        silence_ratio = sum(abs(sample) < silence_threshold for sample in float_samples) / len(
            float_samples
        )
        return {
            "rms": round(rms, 4),
            "peak": round(peak, 4),
            "silence_ratio": round(silence_ratio, 4),
        }


class OpenAIAudioTranscriber:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-transcribe",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "The `openai` package is not installed. Run `pip install openai` "
                "or omit `--transcription_model` to continue without transcription."
            ) from exc

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = OpenAI(**client_kwargs)

    def _build_request_kwargs(self, audio_file, prompt: Optional[str] = None) -> dict:
        kwargs = {
            "model": self.model,
            "file": audio_file,
        }

        if self.model in {"gpt-4o-transcribe", "gpt-4o-mini-transcribe"}:
            kwargs["response_format"] = "json"
            if prompt:
                kwargs["prompt"] = prompt
        elif self.model == "gpt-4o-transcribe-diarize":
            kwargs["response_format"] = "diarized_json"
            kwargs["chunking_strategy"] = "auto"
        else:
            kwargs["response_format"] = "verbose_json"
            kwargs["timestamp_granularities"] = ["segment"]
            if prompt:
                kwargs["prompt"] = prompt

        return kwargs

    def transcribe(self, audio_path: str, output_path: str, prompt: Optional[str] = None) -> dict:
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8") as f:
                return json.load(f)

        with open(audio_path, "rb") as audio_file:
            kwargs = self._build_request_kwargs(audio_file, prompt=prompt)
            response = self.client.audio.transcriptions.create(**kwargs)

        if hasattr(response, "model_dump"):
            response_dict = response.model_dump()
        elif isinstance(response, str):
            response_dict = {"text": response}
        else:
            response_dict = dict(response)

        normalized = normalize_transcript(response_dict)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2)
        return normalized


def normalize_transcript(response_dict: dict) -> dict:
    if not isinstance(response_dict, dict):
        response_dict = {"text": str(response_dict)}

    segments = response_dict.get("segments") or []
    normalized_segments = []
    for segment in segments:
        normalized_segments.append(
            {
                "start": segment.get("start"),
                "end": segment.get("end"),
                "text": segment.get("text", "").strip(),
                "speaker": segment.get("speaker")
                or segment.get("speaker_label")
                or segment.get("speaker_id")
                or "unknown",
            }
        )

    return {
        "text": response_dict.get("text", ""),
        "language": response_dict.get("language"),
        "duration": response_dict.get("duration"),
        "segments": normalized_segments,
        "raw": response_dict,
    }
