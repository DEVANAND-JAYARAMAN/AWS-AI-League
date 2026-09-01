"""
Team-level coordination layer.

The :class:`AgentCoordinator` collects one :class:`FootballDecision` per
specialized agent. This module takes those raw decisions plus the current
:class:`GameState` and produces a single deterministic :class:`TeamDecision`
that describes what the team as a whole should do right now.

No randomness, no LLM calls - everything here is pure deterministic logic.
"""

from dataclasses import dataclass, field
from typing import Dict

from simulation.decision import FootballAction, FootballDecision
from simulation.game_state import GameState
from tools.decision_tools import get_distance


# Fixed agent order used as the final deterministic tie-breaker so the
# result never depends on dict iteration order.
AGENT_ORDER = ["goalkeeper", "defender", "midfielder", "striker"]


# Action priority per tactical mode (index 0 = most important).
# The primary team action is the highest-priority action any agent chose.
_PRIORITY_BY_MODE: Dict[str, list] = {
    "ATTACK": [
        FootballAction.SHOOT,
        FootballAction.PASS,
        FootballAction.PRESS,
        FootballAction.HOLD_POSITION,
        FootballAction.MOVE,
    ],
    "DEFENSE": [
        FootballAction.PRESS,
        FootballAction.HOLD_POSITION,
        FootballAction.PASS,
        FootballAction.SHOOT,
        FootballAction.MOVE,
    ],
    # Transition: keep possession first, then react.
    "TRANSITION": [
        FootballAction.PASS,
        FootballAction.PRESS,
        FootballAction.SHOOT,
        FootballAction.HOLD_POSITION,
        FootballAction.MOVE,
    ],
}


@dataclass
class TeamDecision:
    """
    Deterministic team-level plan built from the individual agent decisions.

    ``agent_decisions`` is preserved untouched so we can always inspect what
    each specialized agent wanted to do.
    """

    tactical_mode: str
    agent_decisions: Dict[str, FootballDecision]
    primary_action: FootballAction
    primary_agent: str
    reason: str
    conflicts: list = field(default_factory=list)


def _determine_tactical_mode(game_state: GameState) -> str:
    """
    Tactical mode is driven by possession.

    OUR_TEAM      -> ATTACK
    OPPONENT_TEAM -> DEFENSE
    anything else -> TRANSITION (possession contested / unknown)
    """

    if game_state.possession == "OUR_TEAM":
        return "ATTACK"

    if game_state.possession == "OPPONENT_TEAM":
        return "DEFENSE"

    return "TRANSITION"


def _priority_index(action: FootballAction, mode: str) -> int:
    """Lower number = higher priority for the given tactical mode."""

    priority = _PRIORITY_BY_MODE.get(mode, _PRIORITY_BY_MODE["ATTACK"])
    return priority.index(action)


def _agent_distance_to_ball(
    agent_id: str,
    game_state: GameState,
) -> float:
    """Distance from the agent's player to the ball (inf if not found)."""

    for player in game_state.our_team:
        if player.player_id == agent_id:
            return get_distance(
                source=player.position,
                target=game_state.ball_position,
            )

    return float("inf")


def _detect_conflicts(
    agent_decisions: Dict[str, FootballDecision],
) -> list:
    """
    Simple deterministic conflict detection.

    Currently: more than one agent trying to PRESS at the same time.
    """

    pressing = [
        agent_id
        for agent_id, decision in agent_decisions.items()
        if decision.action == FootballAction.PRESS
    ]

    conflicts = []

    if len(pressing) > 1:
        conflicts.append(
            "Multiple agents want to PRESS: "
            + ", ".join(sorted(pressing))
        )

    return conflicts


def coordinate_team_decision(
    game_state: GameState,
    agent_decisions: Dict[str, FootballDecision],
) -> TeamDecision:
    """
    Build a :class:`TeamDecision` from raw agent decisions + game state.

    Resolution factors, applied in order:
      1. Tactical mode (selects the action priority table).
      2. Action priority (highest-priority action wins).
      3. For PRESS ties: agent closest to the ball wins.
      4. Otherwise: higher confidence wins.
      5. Fixed agent order (defender, midfielder, striker) as last resort.
    """

    mode = _determine_tactical_mode(game_state)
    conflicts = _detect_conflicts(agent_decisions)

    def sort_key(item):
        agent_id, decision = item

        agent_rank = (
            AGENT_ORDER.index(agent_id)
            if agent_id in AGENT_ORDER
            else len(AGENT_ORDER)
        )

        return (
            _priority_index(decision.action, mode),   # 1. action priority
            _agent_distance_to_ball(agent_id, game_state)
            if decision.action == FootballAction.PRESS
            else 0.0,                                  # 2. PRESS -> closest
            -decision.confidence,                      # 3. confidence
            agent_rank,                                # 4. stable order
        )

    primary_agent, primary_decision = min(
        agent_decisions.items(),
        key=sort_key,
    )

    reason = (
        f"Team is in {mode} mode. "
        f"The {primary_agent} has the most important action "
        f"({primary_decision.action.value}): {primary_decision.reason}"
    )

    return TeamDecision(
        tactical_mode=mode,
        agent_decisions=agent_decisions,
        primary_action=primary_decision.action,
        primary_agent=primary_agent,
        reason=reason,
        conflicts=conflicts,
    )
