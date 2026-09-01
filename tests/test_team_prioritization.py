"""
Step 35 - team-level primary decision prioritization.

These tests feed hand-built agent decisions straight into
coordinate_team_decision(), so they isolate the scoring model from the
individual agents.
"""

from simulation.decision import FootballAction, FootballDecision
from simulation.game_state import GameState
from simulation.team_coordinator import coordinate_team_decision, score_decision


def _state(possession: str) -> GameState:
    """Minimal GameState - only possession matters for prioritization."""
    return GameState(
        ball_position=None,
        our_team=[],
        opponent_team=[],
        possession=possession,
    )


def _decision(action: FootballAction, confidence: float, target=None):
    return FootballDecision(
        action=action,
        target_player_id=target,
        confidence=confidence,
        reason=f"{action.value} decision",
    )


def _print(td):
    print(f"\nTactical Mode: {td.tactical_mode}")
    print(f"Primary Agent: {td.primary_agent}")
    print(f"Primary Action: {td.primary_action.value}")
    print(f"Team Reason: {td.reason}")


def test_attack_prioritizes_shoot():

    decisions = {
        "goalkeeper": _decision(FootballAction.HOLD_POSITION, 0.75),
        "defender": _decision(FootballAction.MOVE, 0.70),
        "midfielder": _decision(FootballAction.PASS, 0.85, target="striker"),
        "striker": _decision(FootballAction.SHOOT, 0.90),
    }

    td = coordinate_team_decision(_state("OUR_TEAM"), decisions)
    _print(td)

    assert td.tactical_mode == "ATTACK"
    assert td.primary_agent == "striker"
    assert td.primary_action == FootballAction.SHOOT


def test_attack_prioritizes_pass_over_move():

    decisions = {
        "goalkeeper": _decision(FootballAction.HOLD_POSITION, 0.75),
        "defender": _decision(FootballAction.MOVE, 0.70),
        "midfielder": _decision(FootballAction.PASS, 0.65, target="striker"),
        "striker": _decision(FootballAction.MOVE, 0.95),
    }

    td = coordinate_team_decision(_state("OUR_TEAM"), decisions)
    _print(td)

    assert td.primary_agent == "midfielder"
    assert td.primary_action == FootballAction.PASS


def test_defense_prioritizes_press():

    decisions = {
        "goalkeeper": _decision(FootballAction.HOLD_POSITION, 0.90),
        "defender": _decision(FootballAction.PRESS, 0.70, target="opponent_1"),
        "midfielder": _decision(FootballAction.MOVE, 0.80),
        "striker": _decision(FootballAction.MOVE, 0.80),
    }

    td = coordinate_team_decision(_state("OPPONENT_TEAM"), decisions)
    _print(td)

    assert td.tactical_mode == "DEFENSE"
    assert td.primary_agent == "defender"
    assert td.primary_action == FootballAction.PRESS


def test_confidence_does_not_override_tactical_importance():

    decisions = {
        "goalkeeper": _decision(FootballAction.HOLD_POSITION, 0.99),
        "striker": _decision(FootballAction.SHOOT, 0.60),
    }

    td = coordinate_team_decision(_state("OUR_TEAM"), decisions)
    _print(td)

    assert td.primary_agent == "striker"
    assert td.primary_action == FootballAction.SHOOT


def test_deterministic_tie_breaking():

    # Identical action + identical confidence -> identical score.
    # ATTACK tie-break order: striker, midfielder, defender, goalkeeper.
    decisions = {
        "goalkeeper": _decision(FootballAction.MOVE, 0.70),
        "defender": _decision(FootballAction.MOVE, 0.70),
        "midfielder": _decision(FootballAction.MOVE, 0.70),
        "striker": _decision(FootballAction.MOVE, 0.70),
    }

    # Same scores for the plain MOVE agents; striker/midfielder also get a
    # small role bonus, but striker outranks midfielder on the tie-break.
    results = {
        coordinate_team_decision(_state("OUR_TEAM"), decisions).primary_agent
        for _ in range(20)
    }

    assert results == {"striker"}

    # Now a pure tie with no role bonuses at all: defender vs goalkeeper.
    plain = {
        "goalkeeper": _decision(FootballAction.PASS, 0.70),
        "defender": _decision(FootballAction.PASS, 0.70),
    }
    agent = coordinate_team_decision(_state("OUR_TEAM"), plain).primary_agent
    assert agent == "defender"  # earlier in the ATTACK tie-break order

    # score_decision is a pure function - same inputs, same output.
    d = _decision(FootballAction.SHOOT, 0.9)
    assert score_decision("striker", d, "ATTACK") == score_decision(
        "striker", d, "ATTACK"
    )


def main():

    test_attack_prioritizes_shoot()
    test_attack_prioritizes_pass_over_move()
    test_defense_prioritizes_press()
    test_confidence_does_not_override_tactical_importance()
    test_deterministic_tie_breaking()

    print("\nAll team prioritization checks passed.")


if __name__ == "__main__":
    main()
