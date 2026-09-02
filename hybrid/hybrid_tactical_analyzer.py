"""
Hybrid tactical analyzer.

    GameState --+--> deterministic AgentCoordinator -> TeamDecision
                |
                +--> LLMTacticalAnalyzer (Amazon Nova Pro) -> TacticalRecommendation
                |
                +--> compare() -> DecisionComparison

Both analyzers receive the *same* GameState object. The hybrid layer does
not modify the GameState, the deterministic decision, or the LLM output.

If the Bedrock / Nova Pro call fails, the error propagates - the hybrid
layer never fabricates an LLM recommendation or pretends the systems
agree. The deterministic path is fully independent and still works
without AWS (use it directly via ``AgentCoordinator``).
"""

import logging
from typing import Iterable, List, Tuple

from agents.coordinator import AgentCoordinator
from hybrid.decision_comparator import (
    DecisionComparison,
    HybridEvaluationMetrics,
    compare,
    summarize,
)
from llm.llm_tactical_analyzer import LLMTacticalAnalyzer
from simulation.game_state import GameState

logger = logging.getLogger(__name__)


class HybridTacticalAnalyzer:
    """Runs both tactical brains on one GameState and compares them."""

    def __init__(
        self,
        coordinator: AgentCoordinator | None = None,
        llm_analyzer: LLMTacticalAnalyzer | None = None,
    ):
        self.coordinator = coordinator or AgentCoordinator()
        self.llm_analyzer = llm_analyzer or LLMTacticalAnalyzer()

    def analyze(self, game_state: GameState) -> DecisionComparison:
        """Deterministic + Nova Pro analysis of one GameState -> comparison."""

        deterministic_decision = self.coordinator.get_coordinated_team_decision(
            game_state
        )
        logger.info(
            "Deterministic: %s / %s / %s",
            deterministic_decision.tactical_mode,
            deterministic_decision.primary_agent,
            deterministic_decision.primary_action.value,
        )

        # Any BedrockInvocationError / TacticalValidationError propagates.
        llm_recommendation = self.llm_analyzer.analyze(game_state)
        logger.info(
            "Nova Pro: %s / %s / %s",
            llm_recommendation.tactical_mode,
            llm_recommendation.recommended_agent,
            llm_recommendation.recommended_action,
        )

        return compare(deterministic_decision, llm_recommendation)

    def analyze_scenarios(
        self,
        named_scenarios: Iterable[Tuple[str, GameState]],
    ) -> Tuple[List[Tuple[str, DecisionComparison]], HybridEvaluationMetrics]:
        """
        Run several ``(name, game_state)`` pairs.

        Returns ``([(name, comparison), ...], metrics)``.
        """

        results: List[Tuple[str, DecisionComparison]] = []
        for name, game_state in named_scenarios:
            results.append((name, self.analyze(game_state)))

        metrics = summarize([comparison for _, comparison in results])
        return results, metrics
