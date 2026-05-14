from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_config(path: str | Path) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config root must be a mapping: {path}")
        return loaded
    except ImportError:
        return _simple_yaml_load(text)


def _simple_yaml_load(text: str) -> Dict[str, Any]:
    """Small fallback parser for this demo config if PyYAML is unavailable."""
    root: Dict[str, Any] = {}
    stack: List[tuple[int, MutableMapping[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value_text = raw_value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value_text == "":
            value: Dict[str, Any] = {}
            parent[key] = value
            stack.append((indent, value))
        else:
            parent[key] = _parse_scalar(value_text)
    return root


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    result = deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def to_plain_dict(value: Any) -> Any:
    if is_dataclass(value):
        return to_plain_dict(asdict(value))
    if isinstance(value, dict):
        return {str(k): to_plain_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain_dict(v) for v in value]
    return value


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(to_plain_dict(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def unique_sorted(values: Iterable[float], ndigits: int = 2) -> List[float]:
    seen = set()
    output: List[float] = []
    for value in sorted(values):
        rounded = round(float(value), ndigits)
        if rounded in seen:
            continue
        seen.add(rounded)
        output.append(rounded)
    return output


def seconds_to_clock(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours:d}:{minutes:02d}:{secs:04.1f}"
    return f"{minutes:02d}:{secs:04.1f}"


def mean(values: Iterable[float], default: float = 0.0) -> float:
    vals = [float(v) for v in values if not math.isnan(float(v))]
    if not vals:
        return default
    return sum(vals) / len(vals)


def confidence_min(values: Iterable[str]) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    vals = [v for v in values if v in order]
    if not vals:
        return "low"
    return min(vals, key=lambda v: order[v])


def confidence_downgrade(confidence: str) -> str:
    if confidence == "high":
        return "medium"
    return "low"
