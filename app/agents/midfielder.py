from app.agents.base import BaseFootballAgent

from app.core.decisions import (
    FootballAction,
    FootballDecision,
)
from app.core.game_state import GameState, Position
from app.core.decision_tools import (
    find_closest_player,
    get_distance,
)


class MidfielderAgent(BaseFootballAgent):
    """
    Specialized football agent responsible for connecting
    attacking and defensive play.
    """

    def decide(
        self,
        game_state: GameState,
    ) -> FootballDecision:

        midfielder = next(
            player
            for player in game_state.our_team
            if player.player_id == self.player_id
        )

        distance_to_ball = get_distance(
            source=midfielder.position,
            target=game_state.ball_position,
        )

        nearest_opponent, opponent_distance = find_closest_player(
            players=game_state.opponent_team,
            target_position=midfielder.position,
        )

        # Opponent possession:
        # Midfielder should move toward a defensive position.
        if game_state.possession != "OUR_TEAM":

            return FootballDecision(
                action=FootballAction.MOVE,
                target_player_id=None,
                target_position=Position(x=40, y=50),
                confidence=0.75,
                reason=(
                    "The opponent has possession, so move into "
                    "a defensive supporting position."
                ),
            )

        # Midfielder is near the ball and under pressure.
        if (
            distance_to_ball <= 8
            and opponent_distance < 6
        ):

            return FootballDecision(
                action=FootballAction.HOLD_POSITION,
                target_player_id=None,
                confidence=0.70,
                reason=(
                    "Near the ball but under defensive pressure. "
                    "Maintain control and look for support."
                ),
            )

        # Find the striker as an attacking target.
        striker = next(
            (
                player
                for player in game_state.our_team
                if player.role == "STRIKER"
            ),
            None,
        )

        # If the midfielder is near the ball and the striker
        # is reasonably far from defenders, pass forward.
        if striker:

            _, striker_opponent_distance = find_closest_player(
                players=game_state.opponent_team,
                target_position=striker.position,
            )

            if (
                distance_to_ball <= 10
                and striker_opponent_distance >= 8
            ):

                return FootballDecision(
                    action=FootballAction.PASS,
                    target_player_id=striker.player_id,
                    confidence=0.85,
                    reason=(
                        "The striker is available with enough "
                        "space from nearby opponents."
                    ),
                )

        # Default midfield movement.
        return FootballDecision(
            action=FootballAction.MOVE,
            target_player_id=None,
            target_position=Position(x=55, y=50),
            confidence=0.65,
            reason=(
                "Move into a balanced position to support both "
                "attack and defense."
            ),
        )