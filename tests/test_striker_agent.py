from agents.striker_agent import StrikerAgent
from simulation.sample_scenario import (
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


if __name__ == "__main__":
    main()
