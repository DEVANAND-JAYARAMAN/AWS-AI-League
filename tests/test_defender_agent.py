from agents.defender_agent import DefenderAgent

from simulation.sample_scenario import (
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


if __name__ == "__main__":
    main()
