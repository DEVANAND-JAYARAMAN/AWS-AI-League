from agents.coordinator import AgentCoordinator

from simulation.sample_scenario import (
    create_attacking_scenario,
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

        print(f"\nAgent: {player_id}")
        print(f"Action: {decision.action.value}")
        print(f"Confidence: {decision.confidence}")
        print(f"Reason: {decision.reason}")


def main():

    run_test(
        "Coordinator - Attacking Pressure",
        create_attacking_scenario,
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


if __name__ == "__main__":
    main()
