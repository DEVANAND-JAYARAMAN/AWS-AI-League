"""
Team-level coordination layer.

The :class:`AgentCoordinator` collects one :class:`FootballDecision` per
specialized agent. This module takes those raw decisions plus the current
:class:`GameState` and produces a single deterministic :class:`TeamDecision`
that describes what the team as a whole should do right now.

No randomness, no LLM calls - everything here is pure deterministic logic.

------------------------------------------------------------------------
Tactical scoring model (Step 35)
------------------------------------------------------------------------
Each agent decision is scored, and the highest score becomes the primary
team decision:

    final_score = action_priority(mode)
                + role_relevance_bonus(mode)
                + decision.confidence * 10

* action_priority  - depends on the tactical MODE. This dominates, so a
  Striker SHOOT in ATTACK always beats a Goalkeeper HOLD_POSITION no
  matter how confident the keeper is.
* role_relevance_bonus - a small nudge (<= the gap between action tiers)
  when a role does the thing that role is meant to do (striker shooting,
  defender pressing, ...).
* confidence * 10 - a secondary factor: it separates decisions that are
  otherwise equal, but can never jump a whole action tier.

Ties (identical final score) are broken by a fixed per-mode role order.
"""

from dataclasses import dataclass, field
from typing import Dict

from app.core.decisions import FootballAction, FootballDecision
from app.core.game_state import GameState


A = FootballAction

# ----------------------------------------------------------------------
# 1. Action priority per tactical mode (higher = more important)
# ----------------------------------------------------------------------

ATTACK_PRIORITY = {
    A.SHOOT: 100,
    A.PASS: 80,
    A.MOVE: 60,
    A.PRESS: 40,
    A.HOLD_POSITION: 20,
}

DEFENSE_PRIORITY = {
    A.PRESS: 100,
    A.MOVE: 80,
    A.HOLD_POSITION: 60,
    A.PASS: 30,
    A.SHOOT: 20,
}

# Transition: keep possession first, then react.
TRANSITION_PRIORITY = {
    A.PASS: 100,
    A.PRESS: 80,
    A.SHOOT: 70,
    A.MOVE: 50,
    A.HOLD_POSITION: 30,
}

_PRIORITY_BY_MODE = {
    "ATTACK": ATTACK_PRIORITY,
    "DEFENSE": DEFENSE_PRIORITY,
    "TRANSITION": TRANSITION_PRIORITY,
}

# ----------------------------------------------------------------------
# 2. Role relevance bonus - deliberately small (max 15) so it can only
#    separate decisions inside the same action tier, never across tiers.
# ----------------------------------------------------------------------

_ROLE_BONUS_BY_MODE = {
    "ATTACK": {
        ("striker", A.SHOOT): 15,
        ("midfielder", A.PASS): 10,
        ("striker", A.MOVE): 8,
        ("midfielder", A.MOVE): 4,
    },
    "DEFENSE": {
        ("defender", A.PRESS): 15,
        ("goalkeeper", A.PRESS): 12,   # keeper coming out is an emergency
        ("defender", A.MOVE): 8,
        ("goalkeeper", A.MOVE): 4,
    },
    "TRANSITION": {
        ("midfielder", A.PASS): 10,
        ("striker", A.SHOOT): 8,
        ("defender", A.PRESS): 8,
    },
}

# ----------------------------------------------------------------------
# 3. Deterministic tie-break order (first listed wins a tie)
# ----------------------------------------------------------------------

_TIEBREAK_BY_MODE = {
    "ATTACK": ["striker", "midfielder", "defender", "goalkeeper"],
    "DEFENSE": ["defender", "goalkeeper", "midfielder", "striker"],
    "TRANSITION": ["striker", "midfielder", "defender", "goalkeeper"],
}

_MODE_ADJECTIVE = {
    "ATTACK": "attacking",
    "DEFENSE": "defensive",
    "TRANSITION": "transition",
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


def _action_priority(action: FootballAction, mode: str) -> int:
    table = _PRIORITY_BY_MODE.get(mode, ATTACK_PRIORITY)
    return table.get(action, 0)


def _role_bonus(agent_id: str, action: FootballAction, mode: str) -> int:
    table = _ROLE_BONUS_BY_MODE.get(mode, {})
    return table.get((agent_id, action), 0)


def _tiebreak_rank(agent_id: str, mode: str) -> int:
    order = _TIEBREAK_BY_MODE.get(mode, _TIEBREAK_BY_MODE["ATTACK"])
    return order.index(agent_id) if agent_id in order else len(order)


def score_decision(
    agent_id: str,
    decision: FootballDecision,
    mode: str,
) -> float:
    """
    Full tactical score for one agent decision (higher = better).

        action_priority + role_bonus + confidence * 10
    """

    return (
        _action_priority(decision.action, mode)
        + _role_bonus(agent_id, decision.action, mode)
        + decision.confidence * 10
    )


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
            "Multiple agents want to PRESS: " + ", ".join(sorted(pressing))
        )

    return conflicts


def coordinate_team_decision(
    game_state: GameState,
    agent_decisions: Dict[str, FootballDecision],
) -> TeamDecision:
    """
    Build a :class:`TeamDecision` from raw agent decisions + game state.

    Selection is mode-aware, action-priority-aware, role-context-aware,
    and uses confidence only as a secondary factor. See the module
    docstring for the scoring model.
    """

    mode = _determine_tactical_mode(game_state)
    conflicts = _detect_conflicts(agent_decisions)

    # Rank by score (desc), then by the mode's fixed role order (asc).
    def sort_key(item):
        agent_id, decision = item
        return (
            -score_decision(agent_id, decision, mode),
            _tiebreak_rank(agent_id, mode),
        )

    primary_agent, primary_decision = min(
        agent_decisions.items(),
        key=sort_key,
    )

    action_name = primary_decision.action.value
    mode_adjective = _MODE_ADJECTIVE.get(mode, mode.lower())

    reason = (
        f"Team is in {mode} mode. "
        f"The {primary_agent} {action_name} decision was selected because "
        f"{action_name} has the highest {mode_adjective} tactical priority, "
        f"with a confidence of {primary_decision.confidence:.2f}."
    )

    return TeamDecision(
        tactical_mode=mode,
        agent_decisions=agent_decisions,
        primary_action=primary_decision.action,
        primary_agent=primary_agent,
        reason=reason,
        conflicts=conflicts,
    )
