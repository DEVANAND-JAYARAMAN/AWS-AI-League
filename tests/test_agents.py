"""
The four specialised agents and the agent coordinator. All offline.

Consolidated from the former per-component test scripts. Each _case_* wraps
one original script; run this file directly to run them all:

    python -m tests.test_agents
"""

import sys
import traceback

def _case_test_striker_agent():
    from app.agents.striker import StrikerAgent
    from app.core.sample_scenario import (
        create_attacking_scenario,
        create_defensive_scenario,
        create_shooting_scenario,
    )


    def run_test(
        scenario_name,
        scenario_function,
    ):

        print("\n" + "=" * 50)
        print(f"⚽ {scenario_name}")
        print("=" * 50)

        game_state = scenario_function()

        striker_agent = StrikerAgent(
            player_id="striker",
            role="STRIKER",
        )

        decision = striker_agent.decide(game_state)

        tp = decision.target_position

        print(f"\nAction: {decision.action.value}")
        print(f"Target Position: {f'({tp.x}, {tp.y})' if tp else None}")
        print(f"Confidence: {decision.confidence}")
        print(f"Reason: {decision.reason}")


    def main():

        run_test(
            "Striker - Attacking Pressure",
            create_attacking_scenario,
        )

        run_test(
            "Striker - Defensive Situation",
            create_defensive_scenario,
        )

        run_test(
            "Striker - Clear Shooting Opportunity",
            create_shooting_scenario,
        )
    _rc = main()
    if _rc:
        raise SystemExit(f'test_striker_agent returned exit code {_rc}')


def _case_test_midfielder_agent():
    from app.agents.midfielder import MidfielderAgent

    from app.core.sample_scenario import (
        create_attacking_scenario,
        create_defensive_scenario,
        create_midfielder_pass_scenario,
    )


    def run_test(
        scenario_name,
        scenario_function,
    ):

        print("\n" + "=" * 55)
        print(f"⚽ {scenario_name}")
        print("=" * 55)

        game_state = scenario_function()

        midfielder_agent = MidfielderAgent(
            player_id="midfielder",
            role="MIDFIELDER",
        )

        decision = midfielder_agent.decide(
            game_state
        )

        tp = decision.target_position

        print(f"\nAction: {decision.action.value}")
        print(f"Target: {decision.target_player_id}")
        print(f"Target Position: {f'({tp.x}, {tp.y})' if tp else None}")
        print(f"Confidence: {decision.confidence}")
        print(f"Reason: {decision.reason}")


    def main():

        run_test(
            "Midfielder - Attacking Pressure",
            create_attacking_scenario,
        )

        run_test(
            "Midfielder - Defensive Situation",
            create_defensive_scenario,
        )

        run_test(
            "Midfielder - Clear Forward Pass",
            create_midfielder_pass_scenario,
        )
    _rc = main()
    if _rc:
        raise SystemExit(f'test_midfielder_agent returned exit code {_rc}')


def _case_test_defender_agent():
    from app.agents.defender import DefenderAgent

    from app.core.sample_scenario import (
        create_defender_press_scenario,
        create_defender_reposition_scenario,
        create_defender_support_scenario,
    )


    def run_test(
        scenario_name,
        scenario_function,
    ):

        print("\n" + "=" * 55)
        print(f"⚽ {scenario_name}")
        print("=" * 55)

        game_state = scenario_function()

        defender_agent = DefenderAgent(
            player_id="defender",
            role="DEFENDER",
        )

        decision = defender_agent.decide(game_state)

        tp = decision.target_position

        print(f"\nAction: {decision.action.value}")
        print(f"Target Player: {decision.target_player_id}")
        print(f"Target Position: {f'({tp.x}, {tp.y})' if tp else None}")
        print(f"Confidence: {decision.confidence}")
        print(f"Reason: {decision.reason}")

        return decision


    def main():

        press = run_test(
            "Defender - Close Opponent Possession",
            create_defender_press_scenario,
        )

        reposition = run_test(
            "Defender - Opponent Possession Far Away",
            create_defender_reposition_scenario,
        )

        support = run_test(
            "Defender - Our Team Possession",
            create_defender_support_scenario,
        )

        # The defender must behave differently across the three situations.
        assert press.action.value == "PRESS"
        assert press.target_player_id is not None

        assert reposition.action.value == "MOVE"
        assert reposition.target_position is not None

        assert support.action.value == "MOVE"
        assert support.target_position is not None

        assert press.action != reposition.action
        assert reposition.reason != support.reason

        print("\nAll defender behaviour checks passed.")
    _rc = main()
    if _rc:
        raise SystemExit(f'test_defender_agent returned exit code {_rc}')


def _case_test_goalkeeper_agent():
    from app.agents.goalkeeper import GoalkeeperAgent

    from app.core.sample_scenario import (
        create_attacking_scenario,
        create_goalkeeper_danger_scenario,
        create_goalkeeper_emergency_scenario,
        create_shooting_scenario,
    )


    def run_test(scenario_name, scenario_function):

        print("\n" + "=" * 55)
        print(f"⚽ Goalkeeper - {scenario_name}")
        print("=" * 55)

        game_state = scenario_function()

        goalkeeper_agent = GoalkeeperAgent(
            player_id="goalkeeper",
            role="GOALKEEPER",
        )

        decision = goalkeeper_agent.decide(game_state)

        tp = decision.target_position

        print(f"\nAction: {decision.action.value}")
        print(f"Target Player: {decision.target_player_id}")
        print(f"Target Position: {f'({tp.x}, {tp.y})' if tp else None}")
        print(f"Confidence: {decision.confidence}")
        print(f"Reason: {decision.reason}")

        return decision


    def main():

        safe = run_test(
            "Safe Ball Far From Our Goal",
            create_shooting_scenario,
        )

        danger = run_test(
            "Opponent Attack Near Our Goal",
            create_goalkeeper_danger_scenario,
        )

        emergency = run_test(
            "Emergency Near Our Goal",
            create_goalkeeper_emergency_scenario,
        )

        our_possession = run_test(
            "Our Team Possession",
            create_attacking_scenario,
        )

        # 1. Safe ball far away -> hold the line.
        assert safe.action.value == "HOLD_POSITION"

        # 2. Opponent attacking near goal -> move to an interception position.
        assert danger.action.value == "MOVE"
        assert danger.target_position is not None
        # Interception sits between our goal (x=0) and the ball (x=22).
        assert 0 < danger.target_position.x < 22

        # 3. Emergency on the goal line -> press / immediate intervention.
        assert emergency.action.value == "PRESS"
        assert emergency.target_player_id is not None

        # 4. Our team has possession -> no panic, hold (or a safe non-press).
        assert our_possession.action.value in ("HOLD_POSITION", "MOVE")

        # The keeper behaves differently across situations.
        assert len({
            safe.action.value,
            danger.action.value,
            emergency.action.value,
        }) == 3

        print("\nAll goalkeeper checks passed.")
    _rc = main()
    if _rc:
        raise SystemExit(f'test_goalkeeper_agent returned exit code {_rc}')


def _case_test_coordinator():
    from app.agents.coordinator import AgentCoordinator

    from app.core.sample_scenario import (
        create_attacking_scenario,
        create_defender_press_scenario,
        create_defensive_scenario,
        create_midfielder_pass_scenario,
        create_shooting_scenario,
    )


    def run_test(
        scenario_name,
        scenario_function,
    ):

        print("\n" + "=" * 55)
        print(f"⚽ {scenario_name}")
        print("=" * 55)

        game_state = scenario_function()

        coordinator = AgentCoordinator()

        decisions = coordinator.get_team_decisions(
            game_state
        )

        for player_id, decision in decisions.items():

            tp = decision.target_position

            print(f"\nAgent: {player_id}")
            print(f"Action: {decision.action.value}")
            print(f"Target Player: {decision.target_player_id}")
            print(f"Target Position: {f'({tp.x}, {tp.y})' if tp else None}")
            print(f"Confidence: {decision.confidence}")
            print(f"Reason: {decision.reason}")


    def main():

        run_test(
            "Coordinator - Attacking Pressure",
            create_attacking_scenario,
        )

        run_test(
            "Coordinator - Defensive Pressure",
            create_defender_press_scenario,
        )

        run_test(
            "Coordinator - Defensive Situation",
            create_defensive_scenario,
        )

        run_test(
            "Coordinator - Midfielder Forward Pass",
            create_midfielder_pass_scenario,
        )

        run_test(
            "Coordinator - Shooting Opportunity",
            create_shooting_scenario,
        )
    _rc = main()
    if _rc:
        raise SystemExit(f'test_coordinator returned exit code {_rc}')




_CASES = [
    ("test_striker_agent", _case_test_striker_agent),
    ("test_midfielder_agent", _case_test_midfielder_agent),
    ("test_defender_agent", _case_test_defender_agent),
    ("test_goalkeeper_agent", _case_test_goalkeeper_agent),
    ("test_coordinator", _case_test_coordinator)
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
