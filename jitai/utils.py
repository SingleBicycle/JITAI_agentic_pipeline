import json
import os
import re
from typing import Any

from json_repair import repair_json


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
    return path


def load_json(path: str, default: Any):
    if not path:
        return default
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: str, payload: Any):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def extract_json_response(response: str, default: dict):
    try:
        return json.loads(repair_json(response))
    except Exception:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            try:
                return json.loads(repair_json(match.group(0)))
            except Exception:
                return default
    return default


def intervals_overlap(start_a: float, end_a: float, start_b: float, end_b: float):
    return max(start_a, start_b) < min(end_a, end_b)


def compact_json(payload: Any):
    return json.dumps(payload, indent=2, ensure_ascii=False)
