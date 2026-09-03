"""
Tactical tool wrappers.

These are thin, structured entry points over the existing deterministic
tactical system:

    analyze_tactical_state -> app.core.tactical_engine + TeamCoordinator
    get_team_decision      -> AgentCoordinator + TeamCoordinator

No tactical logic lives here - it is all delegated.
"""

from strands import tool

from app.agents.coordinator import AgentCoordinator
from app.core.game_state import GameState
from app.core.tactical_engine import analyze_game_state
from app.core.serialization import (
    game_state_from_dict,
    serialize_team_decision,
)


def _coerce_game_state(game_state) -> GameState:
    """Accept either a GameState or its serialized dict form."""
    if isinstance(game_state, GameState):
        return game_state
    return game_state_from_dict(game_state)


@tool
def analyze_tactical_state(game_state) -> dict:
    """
    Analyze the current football game state.

    Args:
        game_state: A GameState object or its serialized dictionary.

    Returns:
        A structured dictionary with possession, tactical mode, the player
        closest to the ball, open attacking players and open defensive
        players (from the deterministic tactical analyzer), plus the
        team-level tactical mode chosen by the coordinator.
    """

    state = _coerce_game_state(game_state)

    analysis = analyze_game_state(state)

    team_decision = AgentCoordinator().get_coordinated_team_decision(state)

    analysis["team_tactical_mode"] = team_decision.tactical_mode
    analysis["recommended_primary_action"] = (
        team_decision.primary_action.value
    )
    analysis["recommended_primary_agent"] = team_decision.primary_agent

    return analysis


@tool
def get_team_decision(game_state) -> dict:
    """
    Run the full deterministic decision stack for one game state.

    Args:
        game_state: A GameState object or its serialized dictionary.

    Returns:
        A serialized TeamDecision: tactical mode, primary agent/action,
        the team-level reason, any conflicts, and every individual agent
        decision.
    """

    state = _coerce_game_state(game_state)

    team_decision = AgentCoordinator().get_coordinated_team_decision(state)

    return serialize_team_decision(team_decision)
