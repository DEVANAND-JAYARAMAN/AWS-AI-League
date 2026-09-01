from simulation.evaluator import format_report
from simulation.match_runner import run_match
from simulation.sample_scenario import (
    create_defender_press_scenario,
    create_midfielder_pass_scenario,
    create_shooting_scenario,
)


def test_attacking_scenario():

    match = run_match(create_midfielder_pass_scenario, ticks=6)
    result = match.result

    print("\n" + format_report(result))

    assert result.total_ticks == 6
    assert result.attack_ticks > 0
    assert result.total_ball_distance >= 0.0
    assert sum(result.player_movement.values()) >= 0.0
    # Action counts always cover all five actions.
    assert set(result.action_counts) == {
        "PASS",
        "SHOOT",
        "PRESS",
        "MOVE",
        "HOLD_POSITION",
    }
    # Every tick is accounted for.
    assert sum(result.action_counts.values()) == 6
    assert result.changed_ticks + result.static_ticks == 6


def test_defensive_scenario():

    match = run_match(create_defender_press_scenario, ticks=5)
    result = match.result

    print("\n" + format_report(result))

    assert result.defense_ticks > 0
    assert (
        result.action_counts["PRESS"] > 0
        or result.player_movement.get("defender", 0.0) > 0.0
    )


def test_shooting_scenario():

    match = run_match(create_shooting_scenario, ticks=4)
    result = match.result

    print("\n" + format_report(result))

    assert result.action_counts["SHOOT"] >= 1
    assert result.total_ball_distance > 0.0
    # Striker took the primary role at least once.
    assert result.primary_agent_counts["striker"] >= 1


def test_state_evolution():

    match = run_match(create_shooting_scenario, ticks=4)
    result = match.result

    assert result.changed_ticks > 0
    assert result.changed_ticks + result.static_ticks == result.total_ticks


def test_evaluator_is_read_only():
    """Evaluating twice yields identical numbers and does not mutate state."""

    match = run_match(create_midfielder_pass_scenario, ticks=5)

    from simulation.evaluator import MatchEvaluator

    first = MatchEvaluator().evaluate(match.history)
    second = MatchEvaluator().evaluate(match.history)

    assert first == second


def main():

    test_attacking_scenario()
    test_defensive_scenario()
    test_shooting_scenario()
    test_state_evolution()
    test_evaluator_is_read_only()

    print("\nAll match evaluator checks passed.")


if __name__ == "__main__":
    main()
