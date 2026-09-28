"""
Validation + statistics for fine-tuning datasets.

Every example must have:

    * a valid tactical_mode      (ALLOWED_MODES)
    * a valid recommended_agent  (one of the players in its own input)
    * a valid recommended_action (ALLOWED_ACTIONS)
    * confidence in [0, 1]
    * a non-empty reason
    * a valid GameState representation (ball position + at least one
      of our players, each with a role and an (x, y) position)

Malformed examples are rejected (collected as errors), never silently
fixed. A dataset statistics report is produced from the valid examples.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from app.fine_tuning.dataset_schema import (
    ALLOWED_ACTIONS,
    ALLOWED_MODES,
    TrainingExample,
)

_ALLOWED_POSSESSION = {"OUR_TEAM", "OPPONENT_TEAM", "CONTESTED", "NONE"}


# ----------------------------------------------------------------------
# Single-example validation
# ----------------------------------------------------------------------

def _validate_position(pos: Any, label: str, errors: List[str]) -> None:
    if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
        errors.append(f"{label} must be a dict with x and y")
        return
    for axis in ("x", "y"):
        try:
            float(pos[axis])
        except (TypeError, ValueError):
            errors.append(f"{label}.{axis} is not a number: {pos[axis]!r}")


def _validate_players(players: Any, label: str, errors: List[str]) -> List[str]:
    """Validate a team list; return the list of valid player_ids found."""

    ids: List[str] = []
    if not isinstance(players, list):
        errors.append(f"{label} must be a list")
        return ids
    for idx, player in enumerate(players):
        if not isinstance(player, dict):
            errors.append(f"{label}[{idx}] must be a dict")
            continue
        pid = player.get("player_id")
        if not pid:
            errors.append(f"{label}[{idx}] missing player_id")
        else:
            ids.append(str(pid))
        if not player.get("role"):
            errors.append(f"{label}[{idx}] ({pid}) missing role")
        _validate_position(player.get("position"), f"{label}[{idx}].position", errors)
    return ids


def validate_example(example: TrainingExample) -> List[str]:
    """
    Return a list of validation error strings for one example. An empty
    list means the example is valid.
    """

    errors: List[str] = []
    inp = example.input
    out = example.output

    # --- GameState representation (input) ---
    _validate_position(inp.ball_position, "input.ball_position", errors)

    if not inp.possession:
        errors.append("input.possession is empty")
    elif inp.possession not in _ALLOWED_POSSESSION:
        errors.append(
            f"input.possession '{inp.possession}' not in {sorted(_ALLOWED_POSSESSION)}"
        )

    our_ids = _validate_players(inp.our_team, "input.our_team", errors)
    _validate_players(inp.opponent_team, "input.opponent_team", errors)
    if not our_ids:
        errors.append("input.our_team must contain at least one valid player")

    # --- Label (output) ---
    if out.tactical_mode not in ALLOWED_MODES:
        errors.append(
            f"output.tactical_mode '{out.tactical_mode}' not in {ALLOWED_MODES}"
        )

    if out.recommended_action not in ALLOWED_ACTIONS:
        errors.append(
            f"output.recommended_action '{out.recommended_action}' "
            f"not in {ALLOWED_ACTIONS}"
        )

    if not out.recommended_agent:
        errors.append("output.recommended_agent is empty")
    elif our_ids and out.recommended_agent not in our_ids:
        errors.append(
            f"output.recommended_agent '{out.recommended_agent}' is not one "
            f"of the input's our_team players {our_ids}"
        )

    try:
        confidence = float(out.confidence)
        if not 0.0 <= confidence <= 1.0:
            errors.append(
                f"output.confidence {confidence} is outside [0, 1]"
            )
    except (TypeError, ValueError):
        errors.append(f"output.confidence is not a number: {out.confidence!r}")

    if not str(out.reason).strip():
        errors.append("output.reason must be a non-empty string")

    return errors


def is_valid(example: TrainingExample) -> bool:
    return not validate_example(example)


# ----------------------------------------------------------------------
# Dataset-level validation
# ----------------------------------------------------------------------

@dataclass
class ValidationReport:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    # (index, [errors]) for each rejected example
    rejected: List[Tuple[int, List[str]]] = field(default_factory=list)

    @property
    def all_valid(self) -> bool:
        return self.invalid == 0


def validate_dataset(
    examples: List[TrainingExample],
) -> Tuple[List[TrainingExample], ValidationReport]:
    """
    Validate every example. Returns ``(valid_examples, report)``. Malformed
    examples are dropped from ``valid_examples`` and recorded in the report.
    """

    report = ValidationReport(total=len(examples))
    valid_examples: List[TrainingExample] = []

    for idx, example in enumerate(examples):
        errors = validate_example(example)
        if errors:
            report.invalid += 1
            report.rejected.append((idx, errors))
        else:
            report.valid += 1
            valid_examples.append(example)

    return valid_examples, report


# ----------------------------------------------------------------------
# Dataset statistics
# ----------------------------------------------------------------------

def compute_statistics(
    examples: List[TrainingExample],
    split_counts: Dict[str, int] | None = None,
) -> Dict[str, Any]:
    """
    Aggregate a statistics report over a list of (valid) examples.

    ``split_counts`` is optional ``{"train": n, "validation": n, "test": n}``.
    """

    category_counts: Counter = Counter()
    mode_counts: Counter = Counter()
    action_counts: Counter = Counter()
    agent_counts: Counter = Counter()
    augmented = 0

    for ex in examples:
        category = ex.metadata.get("category", "UNKNOWN")
        category_counts[category] += 1
        mode_counts[ex.output.tactical_mode] += 1
        action_counts[ex.output.recommended_action] += 1
        agent_counts[ex.output.recommended_agent] += 1
        if ex.metadata.get("augmented"):
            augmented += 1

    stats: Dict[str, Any] = {
        "total_examples": len(examples),
        "augmented_examples": augmented,
        "base_examples": len(examples) - augmented,
        "categories": dict(sorted(category_counts.items())),
        "tactical_modes": dict(sorted(mode_counts.items())),
        "actions": dict(sorted(action_counts.items())),
        "agents": dict(sorted(agent_counts.items())),
    }
    if split_counts is not None:
        stats["splits"] = dict(split_counts)
    return stats


def format_statistics(stats: Dict[str, Any]) -> str:
    """Render a human-readable dataset statistics report."""

    lines: List[str] = []
    lines.append("## Dataset Statistics")
    lines.append("")
    lines.append(f"Total examples: {stats.get('total_examples', 0)}")
    base = stats.get("base_examples")
    aug = stats.get("augmented_examples")
    if base is not None and aug is not None:
        lines.append(f"  Base (benchmark) examples: {base}")
        lines.append(f"  Augmented variations: {aug}")
    lines.append("")

    lines.append("Categories:")
    for name, count in stats.get("categories", {}).items():
        lines.append(f"  {name}: {count}")
    lines.append("")

    lines.append("Tactical modes:")
    for name, count in stats.get("tactical_modes", {}).items():
        lines.append(f"  {name}: {count}")
    lines.append("")

    lines.append("Actions:")
    for name, count in stats.get("actions", {}).items():
        lines.append(f"  {name}: {count}")
    lines.append("")

    lines.append("Recommended agents:")
    for name, count in stats.get("agents", {}).items():
        lines.append(f"  {name}: {count}")

    if "splits" in stats:
        lines.append("")
        lines.append("Splits:")
        for name, count in stats["splits"].items():
            lines.append(f"  {name.capitalize()}: {count}")

    lines.append("")
    return "\n".join(lines)
