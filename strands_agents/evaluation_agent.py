"""
Evaluation Agent adapter.

    Receive simulation history
          -> call the evaluation tool
          -> return a match evaluation summary
"""

from tools.evaluation_tools import evaluate_match

# Future integration point:
# from strands import Agent
# _agent = Agent(model=<bedrock model provider>, tools=[evaluate_match])


class EvaluationAgentAdapter:
    """Deterministic adapter over the evaluation tool."""

    tools = [evaluate_match]

    def evaluate(self, simulation_history) -> dict:
        """
        Args:
            simulation_history: raw SimulationStepResult list from the
                Simulation Agent (``adapter.last_history``).

        Returns:
            Serialized MatchEvaluationResult.
        """

        return evaluate_match(simulation_history)
