import math

from simulation.dynamics import PLAYER_MAX_STEP
from simulation.engine import FootballSimulationEngine
from simulation.field import OPPONENT_GOAL
from simulation.sample_scenario import (
    create_attacking_scenario,
    create_defender_press_scenario,
    create_defender_reposition_scenario,
    create_midfielder_pass_scenario,
    create_shooting_scenario,
)


def _fmt(position):
    return f"({position.x}, {position.y})"


def _player(state, player_id):
    return next(p for p in state.our_team if p.player_id == player_id)


def print_step(result):

    td = result.team_decision

    print("\n" + "=" * 55)
    print(f"⚽ Simulation Tick {result.tick}")
    print("=" * 55)

    print(f"\nTactical Mode: {td.tactical_mode}")
    print(f"Primary Agent: {td.primary_agent}")
    print(f"Primary Action: {td.primary_action.value}")

    print(f"\nBall Before: {_fmt(result.state_before.ball_position)}")
    print(f"Ball After:  {_fmt(result.state_after.ball_position)}")


# ---------------------------------------------------------------------------
# Original behaviour (still holds)
# ---------------------------------------------------------------------------

def test_midfielder_forward_pass():

    game_state = create_midfielder_pass_scenario()
    striker = _player(game_state, "striker")

    engine = FootballSimulationEngine(initial_game_state=game_state)
    result = engine.step()
    print_step(result)

    assert result.team_decision.primary_action.value == "PASS"
    assert result.team_decision.primary_agent == "midfielder"
    assert result.state_after.ball_position.x == striker.position.x
    assert result.state_after.ball_position.y == striker.position.y
    # Original scenario object was not mutated.
    assert game_state.ball_position.x == 60


def test_shooting_opportunity():

    engine = FootballSimulationEngine(
        initial_game_state=create_shooting_scenario()
    )
    result = engine.step()
    print_step(result)

    assert result.team_decision.primary_action.value == "SHOOT"
    assert result.state_after.ball_position.x == OPPONENT_GOAL.x
    assert result.state_after.ball_position.y == OPPONENT_GOAL.y


def test_defensive_pressure():

    engine = FootballSimulationEngine(
        initial_game_state=create_defender_press_scenario()
    )
    start = _player(engine.game_state, "defender").position
    start = (start.x, start.y)

    result = engine.step()
    print_step(result)

    end = _player(result.state_after, "defender").position
    print(f"Defender Before: ({start[0]}, {start[1]})")
    print(f"Defender After:  ({end.x}, {end.y})")

    assert result.team_decision.primary_action.value == "PRESS"
    assert (end.x, end.y) != start


# ---------------------------------------------------------------------------
# Step 33 - dynamics
# ---------------------------------------------------------------------------

def test_supporting_movement():
    """Scenario 1: a non-primary player's position changes across ticks."""

    engine = FootballSimulationEngine(
        initial_game_state=create_shooting_scenario()
    )

    midfielder_start = _player(engine.game_state, "midfielder").position
    midfielder_start = (midfielder_start.x, midfielder_start.y)

    engine.run(ticks=3)

    midfielder_end = _player(engine.game_state, "midfielder").position

    print("\nSupporting movement (midfielder):")
    print(f"  start: {midfielder_start}")
    print(f"  end:   ({midfielder_end.x}, {midfielder_end.y})")

    # Striker is primary (SHOOT); midfielder is a supporting agent and
    # should have drifted toward its balanced target position.
    assert (midfielder_end.x, midfielder_end.y) != midfielder_start


def test_hold_position_progression():
    """
    Scenario 2: a scenario where the striker holds position.

    Step 35: the striker's HOLD_POSITION is no longer promoted to the
    primary team action in ATTACK mode (MOVE outranks it), and the world
    keeps evolving across ticks instead of freezing.
    """

    engine = FootballSimulationEngine(
        initial_game_state=create_attacking_scenario()
    )

    defender_start = _player(engine.game_state, "defender").position
    defender_start = (defender_start.x, defender_start.y)

    results = engine.run(ticks=4)

    actions = [r.team_decision.primary_action.value for r in results]
    print(f"\nProgression actions: {actions}")

    striker_decisions = [
        r.team_decision.agent_decisions["striker"].action.value
        for r in results
    ]

    defender_end = _player(engine.game_state, "defender").position

    # The striker really does hold position ...
    assert striker_decisions[0] == "HOLD_POSITION"
    # ... but a HOLD_POSITION is never the team's primary action in ATTACK.
    assert "HOLD_POSITION" not in actions
    # ... and the world is not frozen: a supporting player moved.
    assert (defender_end.x, defender_end.y) != defender_start


def test_pass_then_next_tick_uses_updated_state():
    """Scenario 3: tick 2 decisions are made from the post-pass state."""

    engine = FootballSimulationEngine(
        initial_game_state=create_midfielder_pass_scenario()
    )
    striker = _player(engine.game_state, "striker").position

    step1 = engine.step()
    assert step1.team_decision.primary_action.value == "PASS"

    step2 = engine.step()

    print("\nPASS -> next tick:")
    print(f"  tick 1 ball after: {_fmt(step1.state_after.ball_position)}")
    print(f"  tick 2 ball before: {_fmt(step2.state_before.ball_position)}")
    print(f"  tick 2 primary: {step2.team_decision.primary_action.value}")

    # Tick 2 started from the updated ball position (at the striker).
    assert step2.state_before.ball_position.x == striker.x
    assert step2.state_before.ball_position.y == striker.y
    # And so the midfielder no longer sees a fresh forward pass.
    assert step2.team_decision.primary_action.value != "PASS"


def test_movement_never_exceeds_max_step():
    """Scenario 4: no player moves more than PLAYER_MAX_STEP in one tick."""

    engine = FootballSimulationEngine(
        initial_game_state=create_defender_reposition_scenario()
    )

    result = engine.step()

    for pid in ("defender", "midfielder", "striker"):
        before = _player(result.state_before, pid).position
        after = _player(result.state_after, pid).position

        moved = math.hypot(after.x - before.x, after.y - before.y)

        print(f"  {pid} moved {round(moved, 2)} (max {PLAYER_MAX_STEP})")

        # Small tolerance: move_towards rounds x/y to 2 decimals, which can
        # nudge the vector length a hundredth of a unit past the cap.
        assert moved <= PLAYER_MAX_STEP + 0.05


def test_multi_tick_history():

    print("\n" + "=" * 55)
    print("⚽ Multi-tick simulation")
    print("=" * 55 + "\n")

    engine = FootballSimulationEngine(
        initial_game_state=create_attacking_scenario()
    )

    results = engine.run(ticks=3)

    assert [r.tick for r in results] == [1, 2, 3]
    assert engine.tick_number == 3
    assert len(engine.history) == 3

    for r in results:
        print(
            f"Tick: {r.tick}  ->  {r.team_decision.tactical_mode} / "
            f"{r.team_decision.primary_action.value}"
        )
        assert r.team_decision is not None
        assert len(r.state_after.our_team) == 4
        assert len(r.state_after.opponent_team) == 3
        assert r.state_after.possession in ("OUR_TEAM", "OPPONENT_TEAM")
        assert r.state_before is not r.state_after


def main():

    test_midfielder_forward_pass()
    test_shooting_opportunity()
    test_defensive_pressure()

    test_supporting_movement()
    test_hold_position_progression()
    test_pass_then_next_tick_uses_updated_state()
    test_movement_never_exceeds_max_step()
    test_multi_tick_history()

    print("\nAll simulation engine checks passed.")


if __name__ == "__main__":
    main()
