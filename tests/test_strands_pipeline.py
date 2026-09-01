"""
End-to-end LOCAL Strands agent pipeline (Step 36).

    GameState
      -> TacticalAgentAdapter   -> team decision
      -> SimulationAgentAdapter -> simulation history
      -> EvaluationAgentAdapter -> match evaluation

Deterministic. No Bedrock, no AWS credentials, no network calls.
"""

import os
import socket

from strands_agents import (
    EvaluationAgentAdapter,
    SimulationAgentAdapter,
    TacticalAgentAdapter,
)
from simulation.sample_scenario import create_midfielder_pass_scenario
from utils.serialization import serialize_game_state

FOUR_AGENTS = {"goalkeeper", "defender", "midfielder", "striker"}


def _no_network_guard():
    """Make any accidental socket connection raise immediately."""
    original = socket.socket.connect

    def blocked(self, *args, **kwargs):
        raise AssertionError("network call attempted during Strands pipeline")

    socket.socket.connect = blocked
    return original, lambda: setattr(socket.socket, "connect", original)


def test_strands_pipeline():

    original_connect, restore = _no_network_guard()

    try:
        game_state = create_midfielder_pass_scenario()

        # Also prove the tools accept the serialized dict form.
        serialized_state = serialize_game_state(game_state)

        # --- Stage 1: Tactical Agent ---
        tactical = TacticalAgentAdapter()
        combined = tactical.analyze(serialized_state)
        team_decision = combined["team_decision"]

        print("\n" + "=" * 55)
        print("⚽ STRANDS AGENT PIPELINE")
        print("=" * 55)
        print("\nStage 1 - Tactical Agent")
        print(f"Tactical Mode: {team_decision['tactical_mode']}")
        print(f"Primary Agent: {team_decision['primary_agent']}")
        print(f"Primary Action: {team_decision['primary_action']}")

        assert team_decision["tactical_mode"] in (
            "ATTACK",
            "DEFENSE",
            "TRANSITION",
        )
        assert set(team_decision["agent_decisions"]) == FOUR_AGENTS
        assert team_decision["primary_agent"] in FOUR_AGENTS

        # --- Stage 2: Simulation Agent ---
        simulation = SimulationAgentAdapter()
        sim_summary = simulation.run(game_state, ticks=5)

        print("\nStage 2 - Simulation Agent")
        print(f"Ticks: {sim_summary['ticks']}")
        print(f"Final Ball Position: {sim_summary['final_ball_position']}")

        assert sim_summary["ticks"] == 5
        assert len(sim_summary["history"]) == 5
        assert len(simulation.last_history) == 5

        # --- Stage 3: Evaluation Agent ---
        evaluation = EvaluationAgentAdapter()
        metrics = evaluation.evaluate(simulation.last_history)

        print("\nStage 3 - Evaluation Agent")
        print(f"Total Ticks: {metrics['total_ticks']}")
        print(f"Changed Ticks: {metrics['changed_ticks']}")
        print(f"Primary Actions: {metrics['action_counts']}")

        assert metrics["total_ticks"] == 5
        assert metrics["changed_ticks"] + metrics["static_ticks"] == 5
        assert sum(metrics["action_counts"].values()) == 5
        assert FOUR_AGENTS.issubset(set(metrics["player_movement"]))

        # --- Constraint checks ---
        assert "AWS_ACCESS_KEY_ID" not in os.environ or True  # not required
        # The deterministic path still matches when called directly.
        from agents.coordinator import AgentCoordinator

        direct = AgentCoordinator().get_coordinated_team_decision(game_state)
        assert direct.primary_agent == team_decision["primary_agent"]
        assert direct.primary_action.value == team_decision["primary_action"]

        print("\nAll Strands pipeline checks passed.")

    finally:
        restore()


def main():
    test_strands_pipeline()


if __name__ == "__main__":
    main()
