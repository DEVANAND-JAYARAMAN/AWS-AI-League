from simulation.decision_engine import make_decision
from simulation.sample_scenario import (
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

    print(f"\nPossession: {game_state.possession}")
    print(f"Action: {decision.action.value}")
    print(f"Target: {decision.target_player_id}")
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


if __name__ == "__main__":
    main()