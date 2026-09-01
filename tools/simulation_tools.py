"""
Simulation tool wrappers over :class:`FootballSimulationEngine`.

    simulate_tick  -> one deterministic engine tick
    simulate_match -> N deterministic engine ticks

The engine (and its dynamics layer) remains the single source of truth;
these helpers only build the engine and serialize its output.
"""

from strands import tool

from simulation.engine import FootballSimulationEngine
from simulation.game_state import GameState
from utils.serialization import (
    game_state_from_dict,
    serialize_game_state,
    serialize_step_result,
)


def _coerce_game_state(game_state) -> GameState:
    if isinstance(game_state, GameState):
        return game_state
    return game_state_from_dict(game_state)


@tool
def simulate_tick(game_state) -> dict:
    """
    Advance the simulation by exactly one tick.

    Args:
        game_state: A GameState object or its serialized dictionary.

    Returns:
        A serialized step result (tick number, team decision, state
        before and state after).
    """

    engine = FootballSimulationEngine(
        initial_game_state=_coerce_game_state(game_state)
    )

    step = engine.step()

    return serialize_step_result(step)


@tool
def simulate_match(game_state, ticks: int = 10) -> dict:
    """
    Run the deterministic simulation for a number of ticks.

    Args:
        game_state: A GameState object or its serialized dictionary.
        ticks: How many ticks to run (default 10).

    Returns:
        A structured summary: number of ticks run, the final ball
        position, the final serialized game state, and the full serialized
        history.
    """

    engine = FootballSimulationEngine(
        initial_game_state=_coerce_game_state(game_state)
    )

    history = engine.run(ticks=ticks)

    return {
        "ticks": len(history),
        "final_ball_position": serialize_game_state(
            engine.game_state
        )["ball_position"],
        "final_state": serialize_game_state(engine.game_state),
        "history": [serialize_step_result(step) for step in history],
    }
