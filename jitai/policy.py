from dataclasses import dataclass, field


URGENCY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def derive_urgency(risk: float, thresholds: dict):
    low = thresholds.get("low", 0.35)
    medium = thresholds.get("medium", 0.6)
    high = thresholds.get("high", 0.8)
    if risk >= high:
        return "high"
    if risk >= medium:
        return "medium"
    if risk >= low:
        return "low"
    return "none"


@dataclass
class PolicyEngine:
    library: dict
    last_triggered: dict = field(default_factory=dict)

    def _urgency_allowed(self, candidate: str, minimum: str):
        return URGENCY_ORDER[candidate] >= URGENCY_ORDER[minimum]

    def evaluate(self, assessment: dict, window_start: float, window_end: float):
        policy_cfg = self.library.get("global", {})
        thresholds = policy_cfg.get(
            "risk_thresholds", {"low": 0.35, "medium": 0.6, "high": 0.8}
        )
        minimum_confidence = policy_cfg.get("minimum_confidence", 0.45)

        risk = assessment.get("child_state", {}).get("dysregulation_risk", 0.0)
        confidence = assessment.get("confidence", 0.0)
        urgency = derive_urgency(risk, thresholds)
        candidate_tags = set(assessment.get("recommended_intervention_tags", []))
        candidate_tags.update(assessment.get("risk_flags", []))

        selected = []
        blocked = []
        should_alert = confidence >= minimum_confidence and urgency != "none"

        for intervention in self.library.get("interventions", []):
            cooldown = intervention.get("cooldown_seconds", 0)
            last_time = self.last_triggered.get(intervention["id"])
            if last_time is not None and window_start - last_time < cooldown:
                blocked.append(intervention["id"])
                continue

            required_tags = set(intervention.get("tags", []))
            if required_tags and candidate_tags.isdisjoint(required_tags):
                continue

            min_urgency = intervention.get("min_urgency", "low")
            if not self._urgency_allowed(urgency, min_urgency):
                continue

            selected.append(intervention)
            self.last_triggered[intervention["id"]] = window_start
            if len(selected) == self.library.get("global", {}).get("max_actions_per_window", 1):
                break

        if not selected:
            should_alert = False

        return {
            "should_alert": should_alert,
            "urgency": urgency,
            "matched_interventions": selected,
            "cooldown_blocked": blocked,
            "recommended_action": selected[0]["instructions"] if selected else None,
            "recommended_action_label": selected[0]["label"] if selected else None,
            "window_start": window_start,
            "window_end": window_end,
        }
