from agents.base_agent import BaseFootballAgent

from simulation.decision import (
    FootballAction,
    FootballDecision,
)
from simulation.field import OPPONENT_GOAL
from simulation.game_state import GameState, Position
from tools.decision_tools import find_closest_player, get_distance


class StrikerAgent(BaseFootballAgent):
    """
    Specialized football agent responsible for attacking decisions.
    """

    def decide(
        self,
        game_state: GameState,
    ) -> FootballDecision:

        # Find this striker in our team
        striker = next(
            player
            for player in game_state.our_team
            if player.player_id == self.player_id
        )

        # Calculate striker distance to opponent goal
        distance_to_goal = get_distance(
            source=striker.position,
            target=OPPONENT_GOAL,
        )

        # Find nearest opponent to striker
        nearest_opponent, opponent_distance = find_closest_player(
            players=game_state.opponent_team,
            target_position=striker.position,
        )

        # Check if striker is near the ball
        distance_to_ball = get_distance(
            source=striker.position,
            target=game_state.ball_position,
        )

        # If opponent has possession, striker should reposition
        if game_state.possession != "OUR_TEAM":
            return FootballDecision(
                action=FootballAction.MOVE,
                target_player_id=None,
                target_position=Position(x=55, y=50),
                confidence=0.70,
                reason=(
                    "The opponent has possession, so reposition "
                    "to support the team's defensive shape."
                ),
            )

        # Excellent shooting opportunity
        if (
            distance_to_goal <= 25
            and distance_to_ball <= 8
            and opponent_distance >= 6
        ):
            return FootballDecision(
                action=FootballAction.SHOOT,
                target_player_id=None,
                confidence=0.90,
                reason=(
                    "Close to goal, near the ball, and not under "
                    "immediate defensive pressure."
                ),
            )

        # Near the ball but under pressure
        if (
            distance_to_ball <= 8
            and opponent_distance < 6
        ):
            return FootballDecision(
                action=FootballAction.HOLD_POSITION,
                target_player_id=None,
                confidence=0.70,
                reason=(
                    "Near the ball but under immediate defensive "
                    "pressure. Maintain control and wait for support."
                ),
            )

        # Otherwise move into an attacking position
        return FootballDecision(
            action=FootballAction.MOVE,
            target_player_id=None,
            target_position=Position(x=85, y=50),
            confidence=0.65,
            reason=(
                "Move into a better attacking position to create "
                "space and receive the ball."
            ),
        )