"""
Core engine: game state, tools, tactical analysis, decision engine, scenarios, dynamics, team coordination, simulation engine, evaluator, and the full deterministic pipeline. All offline.

Consolidated from the former per-component test scripts. Each _case_* wraps
one original script; run this file directly to run them all:

    python -m tests.test_core
"""

import sys
import traceback

def _case_test_game_state():
    from app.core.sample_scenario import create_attacking_scenario


    def main():

        game_state = create_attacking_scenario()

        print("\n⚽ Football Game State")

        print(
            f"Ball Position: "
            f"({game_state.ball_position.x}, "
            f"{game_state.ball_position.y})"
        )

        print(f"\nPossession: {game_state.possession}")

        print("\nOur Team:")

        for player in game_state.our_team:

            print(
                f"- {player.role}: "
                f"({player.position.x}, "
                f"{player.position.y})"
            )

        print("\nOpponent Team:")

        for player in game_state.opponent_team:

            print(
                f"- {player.role}: "
                f"({player.position.x}, "
                f"{player.position.y})"
            )
    _rc = main()
    if _rc:
        raise SystemExit(f'test_game_state returned exit code {_rc}')


def _case_test_tools():
    from app.core.football_tools import calculate_distance


    def main():
        print("\n⚽ Football Tool Test")

        result = calculate_distance(
            player_x=10,
            player_y=20,
            target_x=30,
            target_y=40,
        )

        print(f"Tool result: {result}")
    _rc = main()
    if _rc:
        raise SystemExit(f'test_tools returned exit code {_rc}')


def _case_test_decision_tools():
    from app.core.sample_scenario import create_attacking_scenario
    from app.core.decision_tools import (
        find_closest_player,
        find_open_players,
    )


    def main():

        game_state = create_attacking_scenario()

        print("\n⚽ Football Decision Engine Test")

        # Find our player closest to the ball
        closest_player, distance = find_closest_player(
            players=game_state.our_team,
            target_position=game_state.ball_position,
        )

        print("\nClosest player to the ball:")
        print(f"Player: {closest_player.role}")
        print(f"Distance: {distance}")

        # Find open players
        open_players = find_open_players(
            players=game_state.our_team,
            opponents=game_state.opponent_team,
            safety_distance=10.0,
        )

        print("\nOpen players:")

        if not open_players:
            print("No players are currently open.")

        for player in open_players:
            print(
                f"- {player.role} "
                f"at ({player.position.x}, {player.position.y})"
            )
    _rc = main()
    if _rc:
        raise SystemExit(f'test_decision_tools returned exit code {_rc}')


def _case_test_tactical_analyzer():
    from app.core.sample_scenario import create_attacking_scenario
    from app.core.tactical_engine import analyze_game_state


    def main():

        game_state = create_attacking_scenario()

        analysis = analyze_game_state(game_state)

        print("\n⚽ Tactical Analysis")

        print(f"\nPossession: {analysis['possession']}")
        print(f"Tactical Mode: {analysis['tactical_mode']}")

        closest = analysis["closest_to_ball"]

        print("\nClosest to Ball:")
        print(f"- Player ID: {closest['player_id']}")
        print(f"- Role: {closest['role']}")
        print(f"- Distance: {closest['distance']}")

        print("\nOpen Attacking Players:")

        if not analysis["open_attacking_players"]:
            print("- None")

        for player in analysis["open_attacking_players"]:
            print(
                f"- {player['role']} "
                f"({player['player_id']})"
            )

        print("\nOpen Defensive Players:")

        if not analysis["open_defensive_players"]:
            print("- None")

        for player in analysis["open_defensive_players"]:
            print(
                f"- {player['role']} "
                f"({player['player_id']})"
            )
    _rc = main()
    if _rc:
        raise SystemExit(f'test_tactical_analyzer returned exit code {_rc}')


def _case_test_decision_engine():
    from app.core.decision_engine import make_decision
    from app.core.sample_scenario import create_attacking_scenario


    def main():

        game_state = create_attacking_scenario()

        decision = make_decision(game_state)

        print("\n⚽ Football Decision Engine")

        tp = decision.target_position

        print(f"\nAction: {decision.action.value}")
        print(f"Target Player: {decision.target_player_id}")
        print(f"Target Position: {f'({tp.x}, {tp.y})' if tp else None}")
        print(f"Confidence: {decision.confidence}")
        print(f"Reason: {decision.reason}")
    _rc = main()
    if _rc:
        raise SystemExit(f'test_decision_engine returned exit code {_rc}')


def _case_test_scenarios():
    from app.core.decision_engine import make_decision
    from app.core.sample_scenario import (
        create_attacking_scenario,
        create_open_pass_scenario,
        create_defensive_scenario,
    )


    def run_scenario(name, scenario_function):

        print("\n" + "=" * 50)
        print(f"⚽ {name}")
        print("=" * 50)

        game_state = scenario_function()

        decision = make_decision(game_state)

        tp = decision.target_position

        print(f"\nPossession: {game_state.possession}")
        print(f"Action: {decision.action.value}")
        print(f"Target: {decision.target_player_id}")
        print(f"Target Position: {f'({tp.x}, {tp.y})' if tp else None}")
        print(f"Confidence: {decision.confidence}")
        print(f"Reason: {decision.reason}")


    def main():

        run_scenario(
            "Scenario 1 - Attacking Under Pressure",
            create_attacking_scenario,
        )

        run_scenario(
            "Scenario 2 - Open Passing Opportunity",
            create_open_pass_scenario,
        )

        run_scenario(
            "Scenario 3 - Defensive Situation",
            create_defensive_scenario,
        )
    _rc = main()
    if _rc:
        raise SystemExit(f'test_scenarios returned exit code {_rc}')


def _case_test_target_position():
    """
    Focused test: FootballDecision can carry an optional target_position.
    """

    from app.core.decisions import FootballAction, FootballDecision
    from app.core.game_state import Position


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
    _rc = main()
    if _rc:
        raise SystemExit(f'test_target_position returned exit code {_rc}')


def _case_test_dynamics():
    """Unit tests for the deterministic move_towards helper."""

    import math

    from app.core.dynamics import move_towards
    from app.core.game_state import Position


    def test_moves_at_most_max_distance():

        start = Position(x=0, y=0)
        target = Position(x=100, y=0)

        result = move_towards(start, target, max_distance=8.0)

        moved = math.hypot(result.x - start.x, result.y - start.y)

        assert moved <= 8.0 + 0.05
        assert result.x == 8.0
        assert result.y == 0.0


    def test_does_not_overshoot_close_target():

        start = Position(x=0, y=0)
        target = Position(x=3, y=4)  # distance 5

        result = move_towards(start, target, max_distance=8.0)

        assert (result.x, result.y) == (3, 4)


    def test_already_at_target():

        start = Position(x=10, y=10)
        target = Position(x=10, y=10)

        result = move_towards(start, target, max_distance=8.0)

        assert (result.x, result.y) == (10, 10)


    def test_diagonal_step_length():

        start = Position(x=0, y=0)
        target = Position(x=10, y=10)  # distance ~14.14

        result = move_towards(start, target, max_distance=5.0)

        moved = math.hypot(result.x, result.y)

        assert abs(moved - 5.0) < 0.05


    def main():

        test_moves_at_most_max_distance()
        test_does_not_overshoot_close_target()
        test_already_at_target()
        test_diagonal_step_length()

        print("⚽ move_towards helper")
        print("All move_towards checks passed.")
    _rc = main()
    if _rc:
        raise SystemExit(f'test_dynamics returned exit code {_rc}')


def _case_test_team_prioritization():
    """
    Step 35 - team-level primary decision prioritization.

    These tests feed hand-built agent decisions straight into
    coordinate_team_decision(), so they isolate the scoring model from the
    individual agents.
    """

    from app.core.decisions import FootballAction, FootballDecision
    from app.core.game_state import GameState
    from app.core.team_coordinator import coordinate_team_decision, score_decision


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
    _rc = main()
    if _rc:
        raise SystemExit(f'test_team_prioritization returned exit code {_rc}')


def _case_test_team_coordinator():
    from app.agents.coordinator import AgentCoordinator

    from app.core.sample_scenario import (
        create_attacking_scenario,
        create_defender_press_scenario,
        create_midfielder_pass_scenario,
        create_shooting_scenario,
    )


    def _format_position(position):
        if position is None:
            return None
        return f"({position.x}, {position.y})"


    def run_test(
        scenario_name,
        scenario_function,
    ):

        print("\n" + "=" * 60)
        print(f"⚽ {scenario_name}")
        print("=" * 60)

        game_state = scenario_function()

        coordinator = AgentCoordinator()
        team_decision = coordinator.get_coordinated_team_decision(game_state)

        print(f"\nTactical Mode: {team_decision.tactical_mode}")
        print(f"Primary Agent: {team_decision.primary_agent}")
        print(f"Primary Action: {team_decision.primary_action.value}")
        print(f"Team Reason: {team_decision.reason}")

        if team_decision.conflicts:
            print(f"Conflicts: {team_decision.conflicts}")

        print("\nAll Agent Decisions:")

        for agent_id in ("goalkeeper", "defender", "midfielder", "striker"):

            decision = team_decision.agent_decisions[agent_id]

            print(f"    {agent_id.capitalize()}")
            print(f"        Action: {decision.action.value}")
            print(f"        Target Player: {decision.target_player_id}")
            print(
                "        Target Position: "
                f"{_format_position(decision.target_position)}"
            )
            print(f"        Confidence: {decision.confidence}")
            print(f"        Reason: {decision.reason}")

        return team_decision


    def main():

        attack = run_test(
            "Team - Attacking Pressure",
            create_attacking_scenario,
        )

        forward_pass = run_test(
            "Team - Midfielder Forward Pass",
            create_midfielder_pass_scenario,
        )

        shooting = run_test(
            "Team - Shooting Opportunity",
            create_shooting_scenario,
        )

        defense = run_test(
            "Team - Defensive Pressure",
            create_defender_press_scenario,
        )

        # 1. Attacking pressure
        assert attack.tactical_mode == "ATTACK"

        # 2. Midfielder forward pass
        assert forward_pass.tactical_mode == "ATTACK"
        assert forward_pass.primary_action.value == "PASS"
        assert forward_pass.primary_agent == "midfielder"

        # 3. Shooting opportunity
        assert shooting.tactical_mode == "ATTACK"
        assert shooting.primary_action.value == "SHOOT"
        assert shooting.primary_agent == "striker"

        # 4. Defensive pressure
        assert defense.tactical_mode == "DEFENSE"
        assert defense.primary_action.value == "PRESS"
        assert defense.primary_agent == "defender"

        # Agent autonomy is preserved.
        assert set(attack.agent_decisions) == {
            "goalkeeper",
            "defender",
            "midfielder",
            "striker",
        }

        print("\nAll team coordination checks passed.")
    _rc = main()
    if _rc:
        raise SystemExit(f'test_team_coordinator returned exit code {_rc}')


def _case_test_simulation_engine():
    import math

    from app.core.dynamics import PLAYER_MAX_STEP
    from app.core.simulation import FootballSimulationEngine
    from app.core.field import OPPONENT_GOAL
    from app.core.sample_scenario import (
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
    _rc = main()
    if _rc:
        raise SystemExit(f'test_simulation_engine returned exit code {_rc}')


def _case_test_match_evaluator():
    from app.core.evaluator import format_report
    from app.core.match_runner import run_match
    from app.core.sample_scenario import (
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

        from app.core.evaluator import MatchEvaluator

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
    _rc = main()
    if _rc:
        raise SystemExit(f'test_match_evaluator returned exit code {_rc}')


def _case_test_full_pipeline():
    """
    End-to-end integration test:

        GameState
            -> AgentCoordinator (goalkeeper + defender + midfielder + striker)
            -> TeamCoordinator (TeamDecision)
            -> FootballSimulationEngine (multi-tick)
            -> MatchEvaluator (metrics)
    """

    from app.agents.coordinator import AgentCoordinator

    from app.core.match_runner import run_match
    from app.core.sample_scenario import (
        create_goalkeeper_danger_scenario,
        create_midfielder_pass_scenario,
    )

    FOUR_AGENTS = {"goalkeeper", "defender", "midfielder", "striker"}


    def test_all_four_agents_in_raw_decisions():

        coordinator = AgentCoordinator()
        decisions = coordinator.get_team_decisions(
            create_midfielder_pass_scenario()
        )

        assert set(decisions) == FOUR_AGENTS


    def test_all_four_agents_in_team_decision():

        coordinator = AgentCoordinator()
        team_decision = coordinator.get_coordinated_team_decision(
            create_midfielder_pass_scenario()
        )

        assert set(team_decision.agent_decisions) == FOUR_AGENTS
        assert team_decision.primary_agent in FOUR_AGENTS


    def test_pipeline_through_engine_and_evaluator():

        match = run_match(create_goalkeeper_danger_scenario, ticks=5)
        result = match.result

        # Every tick's TeamDecision kept all four agents.
        for step in match.history:
            assert set(step.team_decision.agent_decisions) == FOUR_AGENTS

        # Evaluator tracks all four players, not a hardcoded three.
        assert FOUR_AGENTS.issubset(set(result.player_movement))

        # Goalkeeper has a primary-agent slot in the metrics.
        assert "goalkeeper" in result.primary_agent_counts

        # In this scenario the keeper is in danger and should have moved.
        assert result.player_movement["goalkeeper"] > 0.0

        print("\nGoalkeeper total movement:",
              result.player_movement["goalkeeper"])
        print("Primary agent counts:", result.primary_agent_counts)


    def main():

        test_all_four_agents_in_raw_decisions()
        test_all_four_agents_in_team_decision()
        test_pipeline_through_engine_and_evaluator()

        print("\nAll full-pipeline checks passed.")
    _rc = main()
    if _rc:
        raise SystemExit(f'test_full_pipeline returned exit code {_rc}')




_CASES = [
    ("test_game_state", _case_test_game_state),
    ("test_tools", _case_test_tools),
    ("test_decision_tools", _case_test_decision_tools),
    ("test_tactical_analyzer", _case_test_tactical_analyzer),
    ("test_decision_engine", _case_test_decision_engine),
    ("test_scenarios", _case_test_scenarios),
    ("test_target_position", _case_test_target_position),
    ("test_dynamics", _case_test_dynamics),
    ("test_team_prioritization", _case_test_team_prioritization),
    ("test_team_coordinator", _case_test_team_coordinator),
    ("test_simulation_engine", _case_test_simulation_engine),
    ("test_match_evaluator", _case_test_match_evaluator),
    ("test_full_pipeline", _case_test_full_pipeline)
]


def main():
    failures = []
    for label, fn in _CASES:
        print("\n" + "#" * 72)
        print("# " + label)
        print("#" * 72)
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - report and continue
            traceback.print_exc()
            failures.append((label, exc))
    print("\n" + "=" * 72)
    if failures:
        print(f"{len(failures)} case(s) FAILED: {[n for n, _ in failures]}")
        sys.exit(1)
    print(f"All {len(_CASES)} case(s) passed.")


if __name__ == "__main__":
    main()
