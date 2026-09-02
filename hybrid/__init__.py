"""
Hybrid tactical evaluation layer (Step 39).

Compares, for the *same* GameState:

    deterministic TeamCoordinator decision   <-- trusted baseline
    Amazon Nova Pro tactical recommendation  <-- advisory

and reports how much the two agree. Nothing here modifies the
deterministic logic, the LLM output, or the GameState.
"""

from hybrid.decision_comparator import (
    AgreementLevel,
    DecisionComparison,
    HybridEvaluationMetrics,
    compare,
    summarize,
)
from hybrid.hybrid_tactical_analyzer import HybridTacticalAnalyzer

__all__ = [
    "AgreementLevel",
    "DecisionComparison",
    "HybridEvaluationMetrics",
    "compare",
    "summarize",
    "HybridTacticalAnalyzer",
]
