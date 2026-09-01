from agents.midfielder_agent import MidfielderAgent

from simulation.sample_scenario import (
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

    print(f"\nAction: {decision.action.value}")
    print(f"Target: {decision.target_player_id}")
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


if __name__ == "__main__":
    main()