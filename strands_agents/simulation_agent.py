"""
Simulation Agent adapter.

    Receive GameState + tick count
          -> call the simulation tool
          -> return a simulation summary

Keeps the raw engine history around (``last_history``) so the Evaluation
Agent can consume it without re-running anything.
"""

from simulation.engine import FootballSimulationEngine
from simulation.game_state import GameState
from tools.simulation_tools import simulate_match, simulate_tick
from utils.serialization import game_state_from_dict

# Future integration point:
# from strands import Agent
# _agent = Agent(model=<bedrock model provider>,
#                tools=[simulate_tick, simulate_match])


class SimulationAgentAdapter:
    """Deterministic adapter over the simulation tools."""

    tools = [simulate_tick, simulate_match]

    def __init__(self):
        self.last_history = []

    def _coerce(self, game_state) -> GameState:
        if isinstance(game_state, GameState):
            return game_state
        return game_state_from_dict(game_state)

    def run(self, game_state, ticks: int = 10) -> dict:
        """
        Run ``ticks`` deterministic ticks and return the tool summary.

        The raw SimulationStepResult list is stored on ``last_history``
        for the Evaluation Agent.
        """

        engine = FootballSimulationEngine(
            initial_game_state=self._coerce(game_state)
        )
        self.last_history = engine.run(ticks=ticks)

        # Tool call produces the serialized summary (single source of
        # truth for the output shape).
        return simulate_match(game_state, ticks=ticks)
