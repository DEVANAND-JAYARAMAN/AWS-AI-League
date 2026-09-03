"""
Step 38 - structured match event logging.

Turns the tick-by-tick output of
:class:`~app.ai.match_simulator.HybridMatchSimulator` into a list of
structured, JSON-serializable :class:`MatchEvent` records:

    Tick
     |-- State Before
     |-- Deterministic Decision
     |-- Nova Recommendation
     |-- Final Decision
     |-- Agreement
     |-- Decision Source
     |-- Ball Movement
     +-- State After

Read-only: nothing here runs the simulation or mutates a GameState. It
only re-shapes data the simulator already produced.
"""

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Iterable, List, Optional

from app.core.serialization import serialize_game_state


def _distance(a, b) -> float:
    """Euclidean distance between two ``(x, y)`` pairs (0.0 if either is missing)."""

    if not a or not b or a[0] is None or b[0] is None:
        return 0.0
    return round(math.hypot(a[0] - b[0], a[1] - b[1]), 2)


def _ball_xy(state, fallback):
    """Prefer an explicit ``(x, y)`` tuple, else read it off a GameState."""

    if fallback is not None:
        return tuple(fallback)
    if state is not None and state.ball_position is not None:
        return (state.ball_position.x, state.ball_position.y)
    return (None, None)


@dataclass
class MatchEvent:
    """One fully-described simulation tick."""

    tick: int
    tactical_mode: str

    possession_before: Optional[str]
    possession_after: Optional[str]

    state_before: Optional[dict]

    deterministic_decision: Optional[dict]
    nova_recommendation: Optional[dict]
    final_decision: dict

    agreement: Optional[str]
    decision_source: str

    nova_called: bool
    nova_skip_reason: Optional[str]

    ball_movement: dict          # {"before": (x, y), "after": (x, y), "distance": float}

    state_after: Optional[dict]

    reason: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class MatchEventLog:
    """An ordered log of :class:`MatchEvent` records for one match."""

    simulation_mode: str
    events: List[MatchEvent] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)

    def as_dicts(self) -> List[dict]:
        return [event.as_dict() for event in self.events]

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            {
                "simulation_mode": self.simulation_mode,
                "total_ticks": len(self.events),
                "events": self.as_dicts(),
            },
            indent=indent,
        )


def _event_from_tick(tick) -> MatchEvent:
    state_before = tick.game_state_before
    state_after = tick.game_state_after

    ball_before = _ball_xy(state_before, getattr(tick, "ball_before", None))
    ball_after = _ball_xy(state_after, getattr(tick, "ball_after", None))

    return MatchEvent(
        tick=tick.tick_number,
        tactical_mode=tick.final_decision.get("tactical_mode", ""),
        possession_before=getattr(tick, "possession_before", None),
        possession_after=getattr(tick, "possession_after", None),
        state_before=serialize_game_state(state_before) if state_before else None,
        deterministic_decision=tick.deterministic_decision,
        nova_recommendation=tick.nova_recommendation,
        final_decision=tick.final_decision,
        agreement=tick.agreement_type,
        decision_source=tick.decision_source,
        nova_called=tick.nova_called,
        nova_skip_reason=tick.nova_skip_reason,
        ball_movement={
            "before": ball_before,
            "after": ball_after,
            "distance": _distance(ball_before, ball_after),
        },
        state_after=serialize_game_state(state_after) if state_after else None,
        reason=tick.reason,
    )


def build_events(match_result_or_ticks) -> List[MatchEvent]:
    """
    Build :class:`MatchEvent` records from a
    :class:`~app.ai.match_simulator.HybridMatchResult` or any iterable of
    ``HybridTickResult`` objects.
    """

    ticks = getattr(match_result_or_ticks, "tick_results", None)
    if ticks is None:
        ticks = list(match_result_or_ticks)

    return [_event_from_tick(tick) for tick in ticks]


def build_event_log(match_result) -> MatchEventLog:
    """Convenience wrapper: :class:`HybridMatchResult` -> :class:`MatchEventLog`."""

    return MatchEventLog(
        simulation_mode=getattr(match_result, "simulation_mode", "UNKNOWN"),
        events=build_events(match_result),
    )
