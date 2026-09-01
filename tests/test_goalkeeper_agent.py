from agents.goalkeeper_agent import GoalkeeperAgent

from simulation.sample_scenario import (
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


if __name__ == "__main__":
    main()
