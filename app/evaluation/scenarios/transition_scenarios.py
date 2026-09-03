"""
Transition scenarios.

These focus on the *tactical mode* the TeamCoordinator derives from
possession, which is the core of transitional play.
"""

from app.evaluation.scenarios.scenario_models import Scenario, ScenarioCategory
from app.core.sample_scenario import (
    create_defensive_scenario,
    create_goalkeeper_emergency_scenario,
    create_midfielder_pass_scenario,
)

TRANSITION = ScenarioCategory.TRANSITION


def build_transition_scenarios():
    return [
        Scenario(
            scenario_name="Our Team Regains Possession",
            category=TRANSITION,
            description=(
                "Our team has just won the ball back - the team should "
                "switch into ATTACK mode."
            ),
            initial_game_state=create_midfielder_pass_scenario(),
            expected_tactical_mode="ATTACK",
            expected_primary_action="PASS",
            expected_primary_agent="midfielder",
        ),
        Scenario(
            scenario_name="Opponent Takes Possession",
            category=TRANSITION,
            description=(
                "The opponent has just taken the ball - the team should "
                "switch into DEFENSE mode."
            ),
            initial_game_state=create_defensive_scenario(),
            expected_tactical_mode="DEFENSE",
        ),
        Scenario(
            scenario_name="Opponent Threat Near Goal",
            category=TRANSITION,
            description=(
                "Opponent breaks through near our goal - the team stays in "
                "DEFENSE mode and reacts to the danger."
            ),
            initial_game_state=create_goalkeeper_emergency_scenario(),
            expected_tactical_mode="DEFENSE",
        ),
    ]
