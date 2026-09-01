"""
End-to-end integration test:

    GameState
        -> AgentCoordinator (goalkeeper + defender + midfielder + striker)
        -> TeamCoordinator (TeamDecision)
        -> FootballSimulationEngine (multi-tick)
        -> MatchEvaluator (metrics)
"""

from agents.coordinator import AgentCoordinator

from simulation.match_runner import run_match
from simulation.sample_scenario import (
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


if __name__ == "__main__":
    main()
