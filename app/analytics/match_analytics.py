"""
Step 40 - final match analytics report.

Aggregates a list of :class:`~app.analytics.event_logger.MatchEvent`
records into one :class:`MatchAnalytics` summary and renders it:

    MATCH ANALYTICS

    Ticks: 10

    Actions:
    PASS: 3
    SHOOT: 2
    PRESS: 1
    MOVE: 4

    AI Usage:
    Nova Calls: 4
    Nova Skipped: 6

    Agreement:
    Full: 2
    Partial: 2
    Disagreement: 0

    Movement:
    Ball Distance: ...
    Team Distance: ...

Read-only and deterministic: same events in -> same report out.
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from app.analytics.event_logger import MatchEvent, build_events

_ACTION_ORDER = ["PASS", "SHOOT", "PRESS", "MOVE", "HOLD_POSITION"]
_MODE_ORDER = ["ATTACK", "DEFENSE", "TRANSITION"]
_SOURCE_ORDER = [
    "AGREEMENT",
    "HYBRID_RESOLUTION",
    "DETERMINISTIC_FALLBACK",
    "DETERMINISTIC_ONLY",
    "NOVA_ONLY",
]
_AGREEMENT_LABELS = {
    "FULL_AGREEMENT": "Full",
    "PARTIAL_AGREEMENT": "Partial",
    "DISAGREEMENT": "Disagreement",
}


@dataclass
class MatchAnalytics:
    """Aggregated, typed view of one match."""

    total_ticks: int
    action_counts: Dict[str, int]
    mode_counts: Dict[str, int]
    decision_source_counts: Dict[str, int]

    nova_calls: int
    nova_skipped: int

    agreement_counts: Dict[str, int]         # keys: Full / Partial / Disagreement / n/a

    ball_distance: float
    team_distance: float
    player_distance: Dict[str, float] = field(default_factory=dict)


def _player_movement(before: dict, after: dict) -> Dict[str, float]:
    """Per-player Euclidean movement between two serialized GameStates."""

    moves: Dict[str, float] = {}
    if not before or not after:
        return moves

    after_team = after.get("our_team", {})
    for pid, player in before.get("our_team", {}).items():
        other = after_team.get(pid)
        if other is None:
            continue
        p0, p1 = player["position"], other["position"]
        if p0 is None or p1 is None:
            continue
        moves[pid] = round(math.hypot(p1["x"] - p0["x"], p1["y"] - p0["y"]), 2)
    return moves


def analyze(events_or_match) -> MatchAnalytics:
    """Aggregate events (or a HybridMatchResult / MatchEventLog) into a report."""

    events = _coerce_events(events_or_match)

    action_counts = Counter()
    mode_counts = Counter()
    source_counts = Counter()
    agreement_counts = Counter()

    nova_calls = 0
    ball_distance = 0.0
    player_distance: Dict[str, float] = {}

    for event in events:
        action_counts[event.final_decision.get("action", "?")] += 1
        if event.tactical_mode:
            mode_counts[event.tactical_mode] += 1
        source_counts[event.decision_source] += 1

        label = _AGREEMENT_LABELS.get(event.agreement, "n/a")
        agreement_counts[label] += 1

        if event.nova_called:
            nova_calls += 1

        ball_distance += float(event.ball_movement.get("distance", 0.0))

        for pid, dist in _player_movement(
            event.state_before, event.state_after
        ).items():
            player_distance[pid] = round(player_distance.get(pid, 0.0) + dist, 2)

    total = len(events)

    return MatchAnalytics(
        total_ticks=total,
        action_counts=_ordered(action_counts, _ACTION_ORDER),
        mode_counts=_ordered(mode_counts, _MODE_ORDER),
        decision_source_counts=_ordered(source_counts, _SOURCE_ORDER),
        nova_calls=nova_calls,
        nova_skipped=total - nova_calls,
        agreement_counts={
            "Full": agreement_counts.get("Full", 0),
            "Partial": agreement_counts.get("Partial", 0),
            "Disagreement": agreement_counts.get("Disagreement", 0),
            "n/a": agreement_counts.get("n/a", 0),
        },
        ball_distance=round(ball_distance, 2),
        team_distance=round(sum(player_distance.values()), 2),
        player_distance=player_distance,
    )


def _ordered(counter: Counter, preferred: List[str]) -> Dict[str, int]:
    """Known keys first (in ``preferred`` order), then any extras alphabetically."""

    out = {key: counter[key] for key in preferred if key in counter}
    for key in sorted(counter):
        if key not in out:
            out[key] = counter[key]
    return out


def format_analytics(analytics_or_match) -> str:
    """Render a :class:`MatchAnalytics` (or anything :func:`analyze` accepts)."""

    a = (
        analytics_or_match
        if isinstance(analytics_or_match, MatchAnalytics)
        else analyze(analytics_or_match)
    )

    lines = ["MATCH ANALYTICS", "", f"Ticks: {a.total_ticks}", ""]

    lines.append("Actions:")
    for action, count in a.action_counts.items():
        lines.append(f"{action}: {count}")
    lines.append("")

    if a.mode_counts:
        lines.append("Tactical Modes:")
        for mode, count in a.mode_counts.items():
            lines.append(f"{mode}: {count}")
        lines.append("")

    lines.append("AI Usage:")
    lines.append(f"Nova Calls: {a.nova_calls}")
    lines.append(f"Nova Skipped: {a.nova_skipped}")
    lines.append("")

    lines.append("Agreement:")
    lines.append(f"Full: {a.agreement_counts['Full']}")
    lines.append(f"Partial: {a.agreement_counts['Partial']}")
    lines.append(f"Disagreement: {a.agreement_counts['Disagreement']}")
    if a.agreement_counts.get("n/a"):
        lines.append(f"N/A (no Nova this tick): {a.agreement_counts['n/a']}")
    lines.append("")

    if a.decision_source_counts:
        lines.append("Decision Sources:")
        for source, count in a.decision_source_counts.items():
            lines.append(f"{source}: {count}")
        lines.append("")

    lines.append("Movement:")
    lines.append(f"Ball Distance: {a.ball_distance:.2f}")
    lines.append(f"Team Distance: {a.team_distance:.2f}")
    for pid, dist in a.player_distance.items():
        lines.append(f"  {pid.capitalize()}: {dist:.2f}")

    return "\n".join(lines)


def _coerce_events(source) -> List[MatchEvent]:
    if hasattr(source, "events"):
        return list(source.events)
    if hasattr(source, "tick_results"):
        return build_events(source)
    items = list(source)
    if items and isinstance(items[0], MatchEvent):
        return items
    return build_events(items)
