"""
Match analytics (Steps 38-40).

    HybridMatchResult
        -> build_event_log()      structured MatchEvent per tick   (Step 38)
        -> format_timeline()      replayable play-by-play          (Step 39)
        -> format_analytics()     one aggregated match report      (Step 40)

Everything here is read-only and deterministic: it re-shapes data the
simulator already produced and never runs a simulation or mutates a
GameState.
"""

from app.analytics.event_logger import (
    MatchEvent,
    MatchEventLog,
    build_event_log,
    build_events,
)
from app.analytics.match_analytics import (
    MatchAnalytics,
    analyze,
    format_analytics,
)
from app.analytics.match_timeline import format_timeline

__all__ = [
    "MatchEvent",
    "MatchEventLog",
    "build_events",
    "build_event_log",
    "format_timeline",
    "MatchAnalytics",
    "analyze",
    "format_analytics",
    "build_match_report",
]


def build_match_report(match_result) -> str:
    """Timeline + analytics for one match, as a single printable string."""

    events = build_events(match_result)
    return (
        format_timeline(events)
        + "\n\n"
        + "=" * 55
        + "\n\n"
        + format_analytics(events)
    )
