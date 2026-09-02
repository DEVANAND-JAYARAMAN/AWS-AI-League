"""
Parse + validate the LLM's tactical recommendation.

Strict on purpose: if the model returns anything that is not a complete,
valid recommendation using the project's real enum values (and a real
player from the current GameState), this raises
:class:`TacticalValidationError`. It never guesses a fallback action and
never touches a GameState.
"""

import json
import re
from dataclasses import dataclass
from typing import Iterable

from llm.tactical_prompt import ALLOWED_ACTIONS, ALLOWED_MODES, KNOWN_AGENTS

_REQUIRED_FIELDS = (
    "tactical_mode",
    "recommended_agent",
    "recommended_action",
    "confidence",
    "reason",
)


class TacticalValidationError(ValueError):
    """Raised when an LLM response is not a valid tactical recommendation."""


@dataclass
class TacticalRecommendation:
    """
    Advisory tactical recommendation from the LLM.

    Deliberately separate from :class:`~simulation.decision.FootballDecision`
    (which the deterministic agents own): this is a *suggestion*, not an
    executed decision. ``recommended_action`` is always one of
    :data:`llm.tactical_prompt.ALLOWED_ACTIONS`.
    """

    tactical_mode: str
    recommended_agent: str
    recommended_action: str
    confidence: float
    reason: str

    def as_dict(self) -> dict:
        return {
            "tactical_mode": self.tactical_mode,
            "recommended_agent": self.recommended_agent,
            "recommended_action": self.recommended_action,
            "confidence": self.confidence,
            "reason": self.reason,
        }


def _extract_json_object(text: str) -> dict:
    """Find and load the first top-level JSON object in ``text``."""

    if not text or not text.strip():
        raise TacticalValidationError("LLM response was empty.")

    cleaned = text.strip()

    # Strip ```json ... ``` / ``` ... ``` fences if the model added them.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    # Fast path: the whole thing is JSON.
    try:
        return json.loads(cleaned)
    except ValueError:
        pass

    # Otherwise grab the outermost {...} span.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise TacticalValidationError(
            f"No JSON object found in LLM response: {text!r}"
        )

    try:
        return json.loads(cleaned[start : end + 1])
    except ValueError as exc:
        raise TacticalValidationError(
            f"LLM response was not valid JSON: {exc}"
        ) from exc


def parse_recommendation(
    text: str,
    valid_agents: Iterable[str] | None = None,
) -> TacticalRecommendation:
    """
    Parse + validate a raw LLM text response.

    ``valid_agents`` should be the ``player_id`` values from the current
    GameState's ``our_team``. If omitted, the generic
    :data:`llm.tactical_prompt.KNOWN_AGENTS` list is used.
    """

    allowed_agents = {a.lower() for a in (valid_agents or KNOWN_AGENTS)}

    data = _extract_json_object(text)

    if not isinstance(data, dict):
        raise TacticalValidationError("LLM JSON was not an object.")

    missing = [field for field in _REQUIRED_FIELDS if field not in data]
    if missing:
        raise TacticalValidationError(
            f"LLM recommendation missing field(s): {', '.join(missing)}"
        )

    tactical_mode = str(data["tactical_mode"]).strip().upper()
    if tactical_mode not in ALLOWED_MODES:
        raise TacticalValidationError(
            f"Invalid tactical_mode '{data['tactical_mode']}'. "
            f"Allowed: {ALLOWED_MODES}"
        )

    recommended_action = str(data["recommended_action"]).strip().upper()
    if recommended_action not in ALLOWED_ACTIONS:
        raise TacticalValidationError(
            f"Invalid recommended_action '{data['recommended_action']}'. "
            f"Allowed: {ALLOWED_ACTIONS}"
        )

    recommended_agent = str(data["recommended_agent"]).strip().lower()
    if recommended_agent not in allowed_agents:
        raise TacticalValidationError(
            f"Invalid recommended_agent '{data['recommended_agent']}'. "
            f"Must be one of the current GameState players: "
            f"{sorted(allowed_agents)}"
        )

    try:
        confidence = float(data["confidence"])
    except (TypeError, ValueError) as exc:
        raise TacticalValidationError(
            f"confidence is not a number: {data['confidence']!r}"
        ) from exc

    if not 0.0 <= confidence <= 1.0:
        raise TacticalValidationError(
            f"confidence {confidence} is outside the range [0, 1]."
        )

    reason = str(data["reason"]).strip()
    if not reason:
        raise TacticalValidationError("reason must be a non-empty string.")

    return TacticalRecommendation(
        tactical_mode=tactical_mode,
        recommended_agent=recommended_agent,
        recommended_action=recommended_action,
        confidence=confidence,
        reason=reason,
    )
