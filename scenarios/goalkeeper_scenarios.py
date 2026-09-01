"""
Goalkeeper scenarios.

The keeper is rarely the team's *primary* decision (tactical
prioritization usually favours an outfield action), so these scenarios
are judged in INDIVIDUAL mode - we check the GoalkeeperAgent's own
decision directly.
"""

from scenarios.scenario_models import EvaluationMode, Scenario, ScenarioCategory
from simulation.sample_scenario import (
    create_attacking_scenario,
    create_goalkeeper_danger_scenario,
    create_goalkeeper_emergency_scenario,
)

GOALKEEPER = ScenarioCategory.GOALKEEPER


def build_goalkeeper_scenarios():
    return [
        Scenario(
            scenario_name="Safe Ball Far From Goal",
            category=GOALKEEPER,
            description=(
                "Ball is up the far end with our team attacking - the "
                "keeper simply holds the goal line."
            ),
            initial_game_state=create_attacking_scenario(),
            evaluation_mode=EvaluationMode.INDIVIDUAL,
            expected_individual_agent="goalkeeper",
            expected_individual_action="HOLD_POSITION",
        ),
        Scenario(
            scenario_name="Opponent Attack Near Goal",
            category=GOALKEEPER,
            description=(
                "Opponent is attacking close to our goal - the keeper "
                "moves onto the ball-to-goal line to cut the angle."
            ),
            initial_game_state=create_goalkeeper_danger_scenario(),
            evaluation_mode=EvaluationMode.INDIVIDUAL,
            expected_individual_agent="goalkeeper",
            expected_individual_action="MOVE",
        ),
        Scenario(
            scenario_name="Emergency Near Goal",
            category=GOALKEEPER,
            description=(
                "Ball is right on our goal with the opponent in "
                "possession - the keeper comes out to press."
            ),
            initial_game_state=create_goalkeeper_emergency_scenario(),
            evaluation_mode=EvaluationMode.INDIVIDUAL,
            expected_individual_agent="goalkeeper",
            expected_individual_action="PRESS",
        ),
    ]
