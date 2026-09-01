"""
Scenario library for the Agentic Football evaluation benchmark.

Each scenario pairs a deterministic :class:`~simulation.game_state.GameState`
with the behaviour we expect the existing football intelligence to produce.
The scenarios never change agent logic - they describe what the current
deterministic rules already do, so the benchmark can measure it.
"""

from scenarios.scenario_models import (
    EvaluationMode,
    Scenario,
    ScenarioCategory,
)
from scenarios.attacking_scenarios import build_attacking_scenarios
from scenarios.defensive_scenarios import build_defensive_scenarios
from scenarios.goalkeeper_scenarios import build_goalkeeper_scenarios
from scenarios.transition_scenarios import build_transition_scenarios


def load_all_scenarios():
    """Return every benchmark scenario, grouped category after category."""

    scenarios = []
    scenarios.extend(build_attacking_scenarios())
    scenarios.extend(build_defensive_scenarios())
    scenarios.extend(build_goalkeeper_scenarios())
    scenarios.extend(build_transition_scenarios())
    return scenarios


__all__ = [
    "EvaluationMode",
    "Scenario",
    "ScenarioCategory",
    "load_all_scenarios",
    "build_attacking_scenarios",
    "build_defensive_scenarios",
    "build_goalkeeper_scenarios",
    "build_transition_scenarios",
]
