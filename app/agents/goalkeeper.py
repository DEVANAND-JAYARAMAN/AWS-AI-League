from app.agents.base import BaseFootballAgent

from app.core.decisions import (
    FootballAction,
    FootballDecision,
)
from app.core.field import OUR_GOAL
from app.core.game_state import GameState, Position
from app.core.decision_tools import find_closest_player, get_distance


# How close (to our goal) the ball must be before the keeper reacts.
DANGER_RANGE = 30.0

# Inside this range it is an emergency - the keeper comes out to close down.
EMERGENCY_RANGE = 12.0


def _point_between(start: Position, end: Position, ratio: float) -> Position:
    """Point on the line start -> end (ratio 0 = start, 1 = end)."""

    return Position(
        x=round(start.x + (end.x - start.x) * ratio, 2),
        y=round(start.y + (end.y - start.y) * ratio, 2),
    )


class GoalkeeperAgent(BaseFootballAgent):
    """
    Specialized football agent responsible for protecting our goal.

    The keeper stays near the goal line and only reacts when the ball
    gets close to our goal while the opponent has possession.
    """

    def decide(
        self,
        game_state: GameState,
    ) -> FootballDecision:

        keeper = next(
            player
            for player in game_state.our_team
            if player.player_id == self.player_id
        )

        ball_to_goal = get_distance(
            source=game_state.ball_position,
            target=OUR_GOAL,
        )

        opponent_has_ball = game_state.possession != "OUR_TEAM"

        # Ball is a genuine threat: opponent has it and it is near our goal.
        if opponent_has_ball and ball_to_goal <= DANGER_RANGE:

            # Emergency: ball almost on our goal -> come out and press.
            if ball_to_goal <= EMERGENCY_RANGE:

                ball_carrier, _ = find_closest_player(
                    players=game_state.opponent_team,
                    target_position=game_state.ball_position,
                )

                return FootballDecision(
                    action=FootballAction.PRESS,
                    target_player_id=ball_carrier.player_id,
                    target_position=game_state.ball_position,
                    confidence=0.85,
                    reason=(
                        "The ball is right on our goal with the opponent "
                        "in possession - come out and close it down."
                    ),
                )

            # Danger but not critical: move onto the line between the
            # ball and our goal to cut down the angle.
            interception = _point_between(
                start=OUR_GOAL,
                end=game_state.ball_position,
                ratio=0.30,
            )

            return FootballDecision(
                action=FootballAction.MOVE,
                target_player_id=None,
                target_position=interception,
                confidence=0.80,
                reason=(
                    "Opponent is attacking near our goal - move to an "
                    "interception position between the ball and the goal."
                ),
            )

        # Nothing threatening: hold the goal line.
        return FootballDecision(
            action=FootballAction.HOLD_POSITION,
            target_player_id=None,
            target_position=None,
            confidence=0.75,
            reason=(
                "No immediate threat to our goal, so hold position on "
                "the goal line and stay ready."
            ),
        )
