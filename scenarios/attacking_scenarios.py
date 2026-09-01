"""
Attacking scenarios (our team has possession).

Expected outcomes below were read off the existing deterministic agents
and the TeamCoordinator scoring model - nothing here asks the agents to
behave differently.
"""

from scenarios.scenario_models import EvaluationMode, Scenario, ScenarioCategory
from simulation.sample_scenario import (
    create_attacking_scenario,
    create_defender_support_scenario,
    create_midfielder_pass_scenario,
    create_open_pass_scenario,
    create_shooting_scenario,
)

ATTACK = ScenarioCategory.ATTACK


def build_attacking_scenarios():
    return [
        Scenario(
            scenario_name="Clear Shooting Opportunity",
            category=ATTACK,
            description=(
                "Striker is close to the opponent goal, on the ball, and "
                "free of pressure."
            ),
            initial_game_state=create_shooting_scenario(),
            expected_primary_agent="striker",
            expected_primary_action="SHOOT",
            expected_tactical_mode="ATTACK",
        ),
        Scenario(
            scenario_name="Open Forward Pass",
            category=ATTACK,
            description=(
                "Midfielder has the ball with the striker open ahead for a "
                "forward pass."
            ),
            initial_game_state=create_midfielder_pass_scenario(),
            expected_primary_agent="midfielder",
            expected_primary_action="PASS",
            expected_tactical_mode="ATTACK",
        ),
        Scenario(
            scenario_name="Attacking Under Pressure",
            category=ATTACK,
            description=(
                "Striker is near the ball but tightly marked - the striker "
                "should keep control rather than force a shot."
            ),
            initial_game_state=create_attacking_scenario(),
            evaluation_mode=EvaluationMode.INDIVIDUAL,
            expected_individual_agent="striker",
            expected_individual_action="HOLD_POSITION",
            expected_tactical_mode="ATTACK",
        ),
        Scenario(
            scenario_name="Striker Movement Opportunity",
            category=ATTACK,
            description=(
                "Our team has the ball but the striker is far from it and "
                "unmarked - the striker should move into space."
            ),
            initial_game_state=create_open_pass_scenario(),
            expected_primary_agent="striker",
            expected_primary_action="MOVE",
            expected_tactical_mode="ATTACK",
        ),
        Scenario(
            scenario_name="Build-Up Play",
            category=ATTACK,
            description=(
                "Our team builds from midfield with the striker available "
                "further forward."
            ),
            initial_game_state=create_defender_support_scenario(),
            evaluation_mode=EvaluationMode.INDIVIDUAL,
            expected_individual_agent="defender",
            expected_individual_action="MOVE",
            expected_tactical_mode="ATTACK",
        ),
    ]
