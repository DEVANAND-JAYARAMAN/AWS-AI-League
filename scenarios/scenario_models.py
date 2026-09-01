"""
Simple, readable scenario model for the evaluation benchmark.

A scenario reuses the existing domain models (``GameState``, ``Player``,
``Position``) - it never redefines them. It only adds the *expected*
behaviour so the benchmark can compare expected vs actual.
"""

from dataclasses import dataclass
from typing import Optional

from simulation.game_state import GameState


class ScenarioCategory:
    """The four benchmark categories."""

    ATTACK = "ATTACK"
    DEFENSE = "DEFENSE"
    GOALKEEPER = "GOALKEEPER"
    TRANSITION = "TRANSITION"

    ALL = (ATTACK, DEFENSE, GOALKEEPER, TRANSITION)


class EvaluationMode:
    """
    How a scenario should be judged.

    PRIMARY
        Compare the *team's* primary decision (primary agent / primary
        action) chosen by the TeamCoordinator.

    INDIVIDUAL
        Compare one specific agent's own decision. This is needed for
        goalkeeper scenarios: the keeper can make the correct individual
        call even when tactical prioritization picks a different action
        as the team's primary decision.
    """

    PRIMARY = "PRIMARY"
    INDIVIDUAL = "INDIVIDUAL"


@dataclass
class Scenario:
    """One benchmark scenario."""

    scenario_name: str
    category: str
    description: str
    initial_game_state: GameState

    # --- Primary-decision expectation (EvaluationMode.PRIMARY) ---
    expected_primary_agent: Optional[str] = None
    expected_primary_action: Optional[str] = None

    # --- Individual-agent expectation (EvaluationMode.INDIVIDUAL) ---
    evaluation_mode: str = EvaluationMode.PRIMARY
    expected_individual_agent: Optional[str] = None
    expected_individual_action: Optional[str] = None

    # --- Optional extra checks ---
    expected_tactical_mode: Optional[str] = None
    notes: str = ""
