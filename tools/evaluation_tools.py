"""
Evaluation tool wrapper over :class:`MatchEvaluator`.

    evaluate_match -> deterministic metrics for a simulation history

Metric calculation is not duplicated here - it is delegated entirely to
MatchEvaluator.
"""

from strands import tool

from simulation.evaluator import MatchEvaluator
from utils.serialization import serialize_evaluation


@tool
def evaluate_match(simulation_history) -> dict:
    """
    Evaluate a completed simulation.

    Args:
        simulation_history: The list of SimulationStepResult objects
            returned by ``FootballSimulationEngine.run()``.

    Returns:
        A serialized MatchEvaluationResult: tick counts, tactical-mode
        counts, action counts, primary-agent counts, total ball distance,
        per-player movement, and changed/static tick counts.
    """

    result = MatchEvaluator().evaluate(simulation_history)

    return serialize_evaluation(result)
