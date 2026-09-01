"""
Defensive scenarios (opponent has possession).

Expected outcomes mirror the existing DefenderAgent / MidfielderAgent
rules and the DEFENSE-mode scoring in the TeamCoordinator.
"""

from scenarios.scenario_models import EvaluationMode, Scenario, ScenarioCategory
from simulation.game_state import GameState, Player, Position
from simulation.sample_scenario import (
    create_defender_press_scenario,
    create_defender_reposition_scenario,
    create_defensive_scenario,
)

DEFENSE = ScenarioCategory.DEFENSE


def _wide_covering_scenario() -> GameState:
    """
    Opponent has possession out wide and high; our defender is deep and
    far from the ball, so the defender should shift across to cover
    rather than sprint at the ball.
    """

    return GameState(
        ball_position=Position(x=72, y=25),
        our_team=[
            Player(player_id="goalkeeper", role="GOALKEEPER",
                   position=Position(x=5, y=50)),
            Player(player_id="defender", role="DEFENDER",
                   position=Position(x=22, y=52)),
            Player(player_id="midfielder", role="MIDFIELDER",
                   position=Position(x=52, y=45)),
            Player(player_id="striker", role="STRIKER",
                   position=Position(x=78, y=50)),
        ],
        opponent_team=[
            Player(player_id="opponent_1", role="ATTACKER",
                   position=Position(x=71, y=25)),
            Player(player_id="opponent_2", role="MIDFIELDER",
                   position=Position(x=64, y=35)),
            Player(player_id="opponent_3", role="ATTACKER",
                   position=Position(x=80, y=32)),
        ],
        possession="OPPONENT_TEAM",
    )


def build_defensive_scenarios():
    return [
        Scenario(
            scenario_name="Close Opponent Possession",
            category=DEFENSE,
            description=(
                "Opponent has the ball deep in our half with our defender "
                "close enough to step out and press."
            ),
            initial_game_state=create_defender_press_scenario(),
            expected_primary_agent="defender",
            expected_primary_action="PRESS",
            expected_tactical_mode="DEFENSE",
        ),
        Scenario(
            scenario_name="Opponent Possession Far Away",
            category=DEFENSE,
            description=(
                "Opponent has the ball on the far side of the pitch - the "
                "defender should reposition, not chase."
            ),
            initial_game_state=create_defender_reposition_scenario(),
            expected_primary_agent="defender",
            expected_primary_action="MOVE",
            expected_tactical_mode="DEFENSE",
        ),
        Scenario(
            scenario_name="Defensive Covering",
            category=DEFENSE,
            description=(
                "Opponent attacks out wide; the deep defender slides across "
                "to a covering position."
            ),
            initial_game_state=_wide_covering_scenario(),
            expected_primary_agent="defender",
            expected_primary_action="MOVE",
            expected_tactical_mode="DEFENSE",
        ),
        Scenario(
            scenario_name="Midfield Defensive Support",
            category=DEFENSE,
            description=(
                "Opponent has possession - the midfielder drops into a "
                "defensive supporting position."
            ),
            initial_game_state=create_defensive_scenario(),
            evaluation_mode=EvaluationMode.INDIVIDUAL,
            expected_individual_agent="midfielder",
            expected_individual_action="MOVE",
            expected_tactical_mode="DEFENSE",
        ),
        Scenario(
            scenario_name="High Defensive Pressure",
            category=DEFENSE,
            description=(
                "Opponent carries the ball into our half with the defender "
                "in range to press aggressively."
            ),
            initial_game_state=create_defensive_scenario(),
            expected_primary_agent="defender",
            expected_primary_action="PRESS",
            expected_tactical_mode="DEFENSE",
        ),
    ]
