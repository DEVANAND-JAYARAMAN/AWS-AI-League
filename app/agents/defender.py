from app.agents.base import BaseFootballAgent

from app.core.decisions import (
    FootballAction,
    FootballDecision,
)
from app.core.field import OUR_GOAL
from app.core.game_state import GameState, Position
from app.core.decision_tools import find_closest_player, get_distance


# Maximum distance (in pitch units) at which the defender is considered
# close enough to the ball to step out and press the ball carrier.
PRESS_RANGE = 15.0


def _point_between(
    start: Position,
    end: Position,
    ratio: float,
) -> Position:
    """
    Return a point on the straight line from ``start`` to ``end``.

    ratio = 0.0 -> exactly at ``start``
    ratio = 1.0 -> exactly at ``end``
    """

    return Position(
        x=round(start.x + (end.x - start.x) * ratio, 2),
        y=round(start.y + (end.y - start.y) * ratio, 2),
    )


class DefenderAgent(BaseFootballAgent):
    """
    Specialized football agent responsible for defensive decisions.

    The defender keeps a position between our goal and the ball, presses
    the ball carrier when the opponent has possession and the defender is
    close enough, and otherwise holds defensive shape.
    """

    def decide(
        self,
        game_state: GameState,
    ) -> FootballDecision:

        # Find this defender in our team.
        defender = next(
            player
            for player in game_state.our_team
            if player.player_id == self.player_id
        )

        distance_to_ball = get_distance(
            source=defender.position,
            target=game_state.ball_position,
        )

        # A sensible defensive spot is on the line between our goal and
        # the ball. When defending we sit closer to the ball; when our
        # team has the ball we stay deeper to protect the goal.
        defensive_support = _point_between(
            start=OUR_GOAL,
            end=game_state.ball_position,
            ratio=0.60,
        )

        deep_support = _point_between(
            start=OUR_GOAL,
            end=game_state.ball_position,
            ratio=0.35,
        )

        # Opponent has possession -> defend.
        if game_state.possession != "OUR_TEAM":

            # Close to the ball: step out and press the ball carrier.
            if distance_to_ball <= PRESS_RANGE:

                ball_carrier, _ = find_closest_player(
                    players=game_state.opponent_team,
                    target_position=game_state.ball_position,
                )

                return FootballDecision(
                    action=FootballAction.PRESS,
                    target_player_id=ball_carrier.player_id,
                    target_position=game_state.ball_position,
                    confidence=0.80,
                    reason=(
                        "The opponent has possession and the defender is "
                        "close to the ball, so press the ball carrier."
                    ),
                )

            # Far from the ball: do not chase across the pitch. Move to a
            # covering position between the ball and our goal.
            return FootballDecision(
                action=FootballAction.MOVE,
                target_player_id=None,
                target_position=defensive_support,
                confidence=0.75,
                reason=(
                    "The opponent has possession but the defender is far "
                    "from the ball, so move into a covering position "
                    "between the ball and our goal."
                ),
            )

        # Our team has possession -> keep defensive structure and offer a
        # deeper support option rather than pushing up to press.
        return FootballDecision(
            action=FootballAction.MOVE,
            target_player_id=None,
            target_position=deep_support,
            confidence=0.70,
            reason=(
                "Our team has possession, so maintain defensive shape and "
                "provide a supporting option behind the ball."
            ),
        )
