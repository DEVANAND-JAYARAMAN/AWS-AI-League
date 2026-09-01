"""
Focused test: FootballDecision can carry an optional target_position.
"""

from simulation.decision import FootballAction, FootballDecision
from simulation.game_state import Position


def test_decision_without_target_position():

    decision = FootballDecision(
        action=FootballAction.SHOOT,
        target_player_id=None,
        confidence=0.9,
        reason="No target position provided.",
    )

    assert decision.target_position is None


def test_decision_with_target_position():

    decision = FootballDecision(
        action=FootballAction.MOVE,
        target_player_id=None,
        target_position=Position(x=40, y=50),
        confidence=0.8,
        reason="Move back to cover the defensive area.",
    )

    assert decision.target_position is not None
    assert decision.target_position.x == 40
    assert decision.target_position.y == 50


def main():

    test_decision_without_target_position()
    test_decision_with_target_position()

    print("\n⚽ FootballDecision.target_position")
    print("Decision without target_position -> None: OK")
    print("Decision with target_position -> (40, 50): OK")
    print("\nAll target_position checks passed.")


if __name__ == "__main__":
    main()
