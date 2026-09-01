from agents.coordinator import AgentCoordinator

from simulation.sample_scenario import (
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


if __name__ == "__main__":
    main()
