"""
Compare a deterministic :class:`~app.core.team_coordinator.TeamDecision`
against an advisory :class:`~app.ai.response_parser.TacticalRecommendation`.

Read-only: the comparator never mutates either input or a GameState.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List

from app.ai.response_parser import TacticalRecommendation
from app.core.team_coordinator import TeamDecision


class AgreementLevel(str, Enum):
    """How closely the two systems agree on one GameState."""

    FULL_AGREEMENT = "FULL_AGREEMENT"        # mode + agent + action match
    PARTIAL_AGREEMENT = "PARTIAL_AGREEMENT"  # mode matches, agent/action differ
    DISAGREEMENT = "DISAGREEMENT"            # tactical mode differs


@dataclass
class DecisionComparison:
    """Structured result of comparing one deterministic vs LLM decision."""

    # Original objects, untouched.
    deterministic_decision: TeamDecision
    llm_recommendation: TacticalRecommendation

    # Flattened values that were actually compared (easy to print).
    deterministic_mode: str
    deterministic_agent: str
    deterministic_action: str
    llm_mode: str
    llm_agent: str
    llm_action: str

    # Field-level matches.
    mode_match: bool
    agent_match: bool
    action_match: bool

    # Metadata.
    deterministic_confidence: float
    llm_confidence: float

    overall_agreement: AgreementLevel

    def differences(self) -> List[str]:
        """Human-readable list of the fields that differ (empty if none)."""

        diffs = []
        if not self.mode_match:
            diffs.append(
                f"mode: deterministic={self.deterministic_mode} "
                f"vs nova={self.llm_mode}"
            )
        if not self.agent_match:
            diffs.append(
                f"agent: deterministic={self.deterministic_agent} "
                f"vs nova={self.llm_agent}"
            )
        if not self.action_match:
            diffs.append(
                f"action: deterministic={self.deterministic_action} "
                f"vs nova={self.llm_action}"
            )
        return diffs


def _primary_confidence(decision: TeamDecision) -> float:
    """Confidence of the agent whose decision became the primary one."""

    agent_decision = decision.agent_decisions.get(decision.primary_agent)
    return float(agent_decision.confidence) if agent_decision else 0.0


def _classify(mode_match: bool, agent_match: bool, action_match: bool) -> AgreementLevel:
    if not mode_match:
        return AgreementLevel.DISAGREEMENT
    if agent_match and action_match:
        return AgreementLevel.FULL_AGREEMENT
    return AgreementLevel.PARTIAL_AGREEMENT


def compare(
    deterministic_decision: TeamDecision,
    llm_recommendation: TacticalRecommendation,
) -> DecisionComparison:
    """Compare mode, primary/recommended agent, and primary/recommended action."""

    det_mode = str(deterministic_decision.tactical_mode).upper()
    det_agent = str(deterministic_decision.primary_agent).lower()
    det_action = str(deterministic_decision.primary_action.value).upper()

    llm_mode = str(llm_recommendation.tactical_mode).upper()
    llm_agent = str(llm_recommendation.recommended_agent).lower()
    llm_action = str(llm_recommendation.recommended_action).upper()

    mode_match = det_mode == llm_mode
    agent_match = det_agent == llm_agent
    action_match = det_action == llm_action

    return DecisionComparison(
        deterministic_decision=deterministic_decision,
        llm_recommendation=llm_recommendation,
        deterministic_mode=det_mode,
        deterministic_agent=det_agent,
        deterministic_action=det_action,
        llm_mode=llm_mode,
        llm_agent=llm_agent,
        llm_action=llm_action,
        mode_match=mode_match,
        agent_match=agent_match,
        action_match=action_match,
        deterministic_confidence=_primary_confidence(deterministic_decision),
        llm_confidence=float(llm_recommendation.confidence),
        overall_agreement=_classify(mode_match, agent_match, action_match),
    )


# ----------------------------------------------------------------------
# Aggregate metrics
# ----------------------------------------------------------------------

@dataclass
class HybridEvaluationMetrics:
    """Aggregated agreement stats over many comparisons."""

    total: int
    full_agreements: int
    partial_agreements: int
    disagreements: int
    mode_agreement_pct: float
    agent_agreement_pct: float
    action_agreement_pct: float


def _pct(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total * 100, 2)


def summarize(comparisons: List[DecisionComparison]) -> HybridEvaluationMetrics:
    """Compute real aggregate metrics - no assumptions about agreement."""

    total = len(comparisons)

    return HybridEvaluationMetrics(
        total=total,
        full_agreements=sum(
            1 for c in comparisons
            if c.overall_agreement is AgreementLevel.FULL_AGREEMENT
        ),
        partial_agreements=sum(
            1 for c in comparisons
            if c.overall_agreement is AgreementLevel.PARTIAL_AGREEMENT
        ),
        disagreements=sum(
            1 for c in comparisons
            if c.overall_agreement is AgreementLevel.DISAGREEMENT
        ),
        mode_agreement_pct=_pct(
            sum(1 for c in comparisons if c.mode_match), total
        ),
        agent_agreement_pct=_pct(
            sum(1 for c in comparisons if c.agent_match), total
        ),
        action_agreement_pct=_pct(
            sum(1 for c in comparisons if c.action_match), total
        ),
    )
