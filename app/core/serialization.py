"""
Serialization helpers.

Convert the existing domain objects into plain dictionaries that contain
only JSON-serializable values (numbers, strings, bools, None, lists,
dicts). No external libraries, no JSON files - just Python structures the
Strands tool layer can pass around safely.

Round-trip helpers (``*_from_dict``) are provided for the objects a tool
might legitimately receive as input (``GameState``).
"""

from app.core.decisions import FootballDecision
from app.core.game_state import GameState, Player, Position


# ----------------------------------------------------------------------
# Position
# ----------------------------------------------------------------------

def serialize_position(position):
    if position is None:
        return None
    return {"x": position.x, "y": position.y}


def position_from_dict(data):
    if data is None:
        return None
    return Position(x=data["x"], y=data["y"])


# ----------------------------------------------------------------------
# Player
# ----------------------------------------------------------------------

def serialize_player(player: Player) -> dict:
    return {
        "player_id": player.player_id,
        "role": player.role,
        "position": serialize_position(player.position),
    }


def player_from_dict(data: dict) -> Player:
    return Player(
        player_id=data["player_id"],
        role=data["role"],
        position=position_from_dict(data["position"]),
    )


# ----------------------------------------------------------------------
# GameState
# ----------------------------------------------------------------------

def serialize_game_state(game_state: GameState) -> dict:
    return {
        "ball_position": serialize_position(game_state.ball_position),
        "possession": game_state.possession,
        "our_team": {
            player.player_id: serialize_player(player)
            for player in game_state.our_team
        },
        "opponent_team": {
            player.player_id: serialize_player(player)
            for player in game_state.opponent_team
        },
    }


def game_state_from_dict(data: dict) -> GameState:
    return GameState(
        ball_position=position_from_dict(data.get("ball_position")),
        our_team=[
            player_from_dict(p) for p in data["our_team"].values()
        ],
        opponent_team=[
            player_from_dict(p) for p in data["opponent_team"].values()
        ],
        possession=data["possession"],
    )


# ----------------------------------------------------------------------
# Decisions
# ----------------------------------------------------------------------

def serialize_decision(decision: FootballDecision) -> dict:
    return {
        "action": decision.action.value,
        "target_player_id": decision.target_player_id,
        "target_position": serialize_position(decision.target_position),
        "confidence": decision.confidence,
        "reason": decision.reason,
    }


def serialize_team_decision(team_decision) -> dict:
    return {
        "tactical_mode": team_decision.tactical_mode,
        "primary_agent": team_decision.primary_agent,
        "primary_action": team_decision.primary_action.value,
        "reason": team_decision.reason,
        "conflicts": list(team_decision.conflicts),
        "agent_decisions": {
            agent_id: serialize_decision(decision)
            for agent_id, decision in team_decision.agent_decisions.items()
        },
    }


# ----------------------------------------------------------------------
# Simulation / evaluation results
# ----------------------------------------------------------------------

def serialize_step_result(step) -> dict:
    return {
        "tick": step.tick,
        "team_decision": serialize_team_decision(step.team_decision),
        "state_before": serialize_game_state(step.state_before),
        "state_after": serialize_game_state(step.state_after),
    }


def serialize_evaluation(result) -> dict:
    return {
        "total_ticks": result.total_ticks,
        "mode_counts": dict(result.mode_counts),
        "action_counts": dict(result.action_counts),
        "primary_agent_counts": dict(result.primary_agent_counts),
        "total_ball_distance": result.total_ball_distance,
        "player_movement": dict(result.player_movement),
        "changed_ticks": result.changed_ticks,
        "static_ticks": result.static_ticks,
    }
