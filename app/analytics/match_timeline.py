"""
Step 39 - replayable match timeline.

Renders a list of :class:`~app.analytics.event_logger.MatchEvent` records
as a compact, human-readable play-by-play:

    MATCH START

    Tick 1
    Midfielder -> PASS
    Ball: (60, 40) -> (82, 50)

    Tick 2
    Striker -> SHOOT
    Ball: (82, 50) -> (100, 50)

    MATCH END
"""

from typing import Iterable, List

from app.analytics.event_logger import MatchEvent, build_events


def _fmt_xy(xy) -> str:
    if not xy or xy[0] is None:
        return "(?, ?)"
    x, y = xy
    x = int(x) if float(x) == int(x) else round(x, 1)
    y = int(y) if float(y) == int(y) else round(y, 1)
    return f"({x}, {y})"


def _timeline_lines(events: List[MatchEvent]) -> List[str]:
    lines: List[str] = ["MATCH START", ""]

    for event in events:
        agent = str(event.final_decision.get("agent", "?")).capitalize()
        action = event.final_decision.get("action", "?")

        lines.append(f"Tick {event.tick}")
        lines.append(f"{agent} -> {action}")
        lines.append(
            f"Ball: {_fmt_xy(event.ball_movement['before'])} -> "
            f"{_fmt_xy(event.ball_movement['after'])}"
        )

        if event.possession_before != event.possession_after:
            lines.append(
                f"Possession: {event.possession_before} -> "
                f"{event.possession_after}"
            )

        lines.append("")

    lines.append("MATCH END")
    return lines


def format_timeline(events_or_match) -> str:
    """
    Accepts a list of :class:`MatchEvent`, a
    :class:`~app.analytics.event_logger.MatchEventLog`, or a
    :class:`~app.ai.match_simulator.HybridMatchResult`.
    """

    events = _coerce_events(events_or_match)
    return "\n".join(_timeline_lines(events))


def _coerce_events(source) -> List[MatchEvent]:
    if hasattr(source, "events"):            # MatchEventLog
        return list(source.events)
    if hasattr(source, "tick_results"):      # HybridMatchResult
        return build_events(source)
    items = list(source)
    if items and isinstance(items[0], MatchEvent):
        return items
    return build_events(items)               # iterable of HybridTickResult
