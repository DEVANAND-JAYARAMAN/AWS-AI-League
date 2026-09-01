"""
Deterministic simulation dynamics.

After the primary team action has been executed for a tick, this layer
lets the rest of the world evolve a little so multi-tick simulations do
not freeze (e.g. repeated HOLD_POSITION).

Rules (all deterministic, no randomness, no physics):

* Every non-primary agent that has a ``target_position`` in its own
  FootballDecision takes ONE small step toward that target.
* Movement is capped at ``PLAYER_MAX_STEP`` units per tick so nobody
  teleports across the pitch.
* Possession and the ball are left exactly as the action executor set
  them.
"""

import math

from simulation.game_state import GameState, Position


# Maximum distance a player may move in a single tick.
PLAYER_MAX_STEP = 8.0


def move_towards(
    current_position: Position,
    target_position: Position,
    max_distance: float,
) -> Position:
    """
    Return a new Position that is at most ``max_distance`` from
    ``current_position`` in the direction of ``target_position``.

    * If the target is already within reach (or identical), returns the
      target position exactly (no overshoot).
    * Otherwise returns a point ``max_distance`` along the straight line.
    """

    dx = target_position.x - current_position.x
    dy = target_position.y - current_position.y

    distance = math.hypot(dx, dy)

    if distance <= max_distance or distance == 0:
        return Position(x=target_position.x, y=target_position.y)

    ratio = max_distance / distance

    return Position(
        x=round(current_position.x + dx * ratio, 2),
        y=round(current_position.y + dy * ratio, 2),
    )


def apply_dynamics(
    state: GameState,
    team_decision,
    max_step: float = PLAYER_MAX_STEP,
) -> None:
    """
    Evolve the world for one tick, in place, on ``state``.

    The primary agent has already been moved by the action executor, so
    here we only nudge the *supporting* agents toward the target position
    each of them chose. This is what keeps HOLD_POSITION ticks from being
    completely static.
    """

    primary_agent = team_decision.primary_agent

    for agent_id, decision in team_decision.agent_decisions.items():

        if agent_id == primary_agent:
            continue

        if decision.target_position is None:
            continue

        player = _find_our_player(state, agent_id)

        if player is None:
            continue

        player.position = move_towards(
            current_position=player.position,
            target_position=decision.target_position,
            max_distance=max_step,
        )


def _find_our_player(state: GameState, player_id: str):

    for player in state.our_team:
        if player.player_id == player_id:
            return player

    return None
