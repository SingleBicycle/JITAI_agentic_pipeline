import json
import re


def repair_json(payload: str) -> str:
    if not isinstance(payload, str):
        return payload

    stripped = payload.strip()
    if not stripped:
        return stripped

    try:
        json.loads(stripped)
        return stripped
    except Exception:
        pass

    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        candidate = match.group(0)
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            return candidate

    return stripped
