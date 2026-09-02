"""
Hybrid Decision Resolver.

Takes the deterministic :class:`~simulation.team_coordinator.TeamDecision`,
the advisory :class:`~llm.response_parser.TacticalRecommendation`, and the
:class:`~hybrid.decision_comparator.DecisionComparison` between them, and
produces **one** final football decision.

Rules (see the project brief for Step 35):

* FULL_AGREEMENT   -> take the shared decision, nudge confidence up.
                      decision_source = AGREEMENT
* PARTIAL_AGREEMENT -> same tactical mode, but agent/action differ. Pick
                      the action with the higher tactical priority
                      (reusing the TeamCoordinator priority tables),
                      with confidence as a secondary factor.
                      decision_source = HYBRID_RESOLUTION
* DISAGREEMENT      -> tactical modes conflict. Fall back to the
                      deterministic decision as the safety baseline; the
                      Nova recommendation is reported, not discarded.
                      decision_source = DETERMINISTIC_FALLBACK

Deterministic and reproducible: identical inputs always give an identical
result. Nothing here mutates the inputs or any GameState.
"""

from dataclasses import dataclass
from enum import Enum

from hybrid.decision_comparator import AgreementLevel, DecisionComparison
from llm.response_parser import TacticalRecommendation
from simulation.decision import FootballAction
from simulation.team_coordinator import TeamDecision, _action_priority

# Weight applied to confidence when breaking a priority near-tie. Kept
# equal to the TeamCoordinator's ``confidence * 10`` so confidence can
# separate equal-priority actions but not jump a whole priority tier.
_CONFIDENCE_WEIGHT = 10.0

# Small bump applied when both systems independently agree.
_AGREEMENT_BONUS = 0.05


class DecisionSource(str, Enum):
    """Where the final hybrid decision came from."""

    AGREEMENT = "AGREEMENT"
    HYBRID_RESOLUTION = "HYBRID_RESOLUTION"
    DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK"


@dataclass
class HybridDecision:
    """The single resolved decision plus an explanation of how it was made."""

    final_tactical_mode: str
    final_agent: str
    final_action: str
    final_confidence: float
    decision_source: DecisionSource
    agreement_type: AgreementLevel
    reason: str

    def as_dict(self) -> dict:
        return {
            "final_tactical_mode": self.final_tactical_mode,
            "final_agent": self.final_agent,
            "final_action": self.final_action,
            "final_confidence": self.final_confidence,
            "decision_source": self.decision_source.value,
            "agreement_type": self.agreement_type.value,
            "reason": self.reason,
        }


# ----------------------------------------------------------------------
# small safe helpers (existing models mix Enum objects and strings)
# ----------------------------------------------------------------------

def _action_str(value) -> str:
    if isinstance(value, FootballAction):
        return value.value
    return str(value).strip().upper()


def _to_football_action(value):
    if isinstance(value, FootballAction):
        return value
    try:
        return FootballAction(_action_str(value))
    except ValueError:
        return None


def _priority(action_value: str, mode: str) -> int:
    action = _to_football_action(action_value)
    if action is None:
        return 0
    return _action_priority(action, str(mode).strip().upper())


def _clamp(confidence: float) -> float:
    return round(max(0.0, min(1.0, confidence)), 4)


# ----------------------------------------------------------------------
# resolver
# ----------------------------------------------------------------------

class HybridDecisionResolver:
    """Resolves a deterministic decision + a Nova Pro recommendation into one."""

    def resolve(
        self,
        deterministic_decision: TeamDecision,
        llm_recommendation: TacticalRecommendation,
        comparison: DecisionComparison,
    ) -> HybridDecision:
        agreement = comparison.overall_agreement

        if agreement is AgreementLevel.FULL_AGREEMENT:
            return self._resolve_full_agreement(comparison)

        if agreement is AgreementLevel.PARTIAL_AGREEMENT:
            return self._resolve_partial_agreement(comparison)

        return self._resolve_disagreement(comparison)

    # -- Rule 1 --------------------------------------------------------
    def _resolve_full_agreement(
        self, comparison: DecisionComparison
    ) -> HybridDecision:
        det_conf = comparison.deterministic_confidence
        llm_conf = comparison.llm_confidence
        final_conf = _clamp((det_conf + llm_conf) / 2.0 + _AGREEMENT_BONUS)

        reason = (
            "Both deterministic multi-agent reasoning and Amazon Nova Pro "
            "independently recommended the same tactical decision "
            f"({comparison.deterministic_mode} / {comparison.deterministic_agent} "
            f"/ {comparison.deterministic_action}). Confidence was nudged up "
            f"from {det_conf:.2f}/{llm_conf:.2f} because the two systems agree."
        )

        return HybridDecision(
            final_tactical_mode=comparison.deterministic_mode,
            final_agent=comparison.deterministic_agent,
            final_action=comparison.deterministic_action,
            final_confidence=final_conf,
            decision_source=DecisionSource.AGREEMENT,
            agreement_type=AgreementLevel.FULL_AGREEMENT,
            reason=reason,
        )

    # -- Rule 2 --------------------------------------------------------
    def _resolve_partial_agreement(
        self, comparison: DecisionComparison
    ) -> HybridDecision:
        mode = comparison.deterministic_mode  # modes match here

        det_priority = _priority(comparison.deterministic_action, mode)
        llm_priority = _priority(comparison.llm_action, mode)

        det_score = det_priority + comparison.deterministic_confidence * _CONFIDENCE_WEIGHT
        llm_score = llm_priority + comparison.llm_confidence * _CONFIDENCE_WEIGHT

        # Tie -> keep the deterministic decision (reproducible baseline).
        if llm_score > det_score:
            chosen_agent = comparison.llm_agent
            chosen_action = comparison.llm_action
            chosen_conf = comparison.llm_confidence
            picked = "Amazon Nova Pro"
        else:
            chosen_agent = comparison.deterministic_agent
            chosen_action = comparison.deterministic_action
            chosen_conf = comparison.deterministic_confidence
            picked = "the deterministic engine"

        reason = (
            f"Both systems agree the tactical mode is {mode}, but differ on "
            f"agent/action (deterministic: {comparison.deterministic_agent}/"
            f"{comparison.deterministic_action} @ "
            f"{comparison.deterministic_confidence:.2f}; nova: "
            f"{comparison.llm_agent}/{comparison.llm_action} @ "
            f"{comparison.llm_confidence:.2f}). Using tactical action priority "
            f"for {mode} ({comparison.deterministic_action}={det_priority}, "
            f"{comparison.llm_action}={llm_priority}) with confidence as a "
            f"secondary factor, {picked}'s "
            f"{chosen_agent}/{chosen_action} was selected."
        )

        return HybridDecision(
            final_tactical_mode=mode,
            final_agent=chosen_agent,
            final_action=chosen_action,
            final_confidence=_clamp(chosen_conf),
            decision_source=DecisionSource.HYBRID_RESOLUTION,
            agreement_type=AgreementLevel.PARTIAL_AGREEMENT,
            reason=reason,
        )

    # -- Rule 3 --------------------------------------------------------
    def _resolve_disagreement(
        self, comparison: DecisionComparison
    ) -> HybridDecision:
        reason = (
            "The systems disagreed on tactical mode (deterministic: "
            f"{comparison.deterministic_mode}, nova: {comparison.llm_mode}). "
            "The deterministic tactical engine was selected as the safety "
            f"fallback: {comparison.deterministic_mode} / "
            f"{comparison.deterministic_agent} / "
            f"{comparison.deterministic_action}. The Nova Pro recommendation "
            f"({comparison.llm_mode} / {comparison.llm_agent} / "
            f"{comparison.llm_action} @ {comparison.llm_confidence:.2f}) is "
            "recorded for review, not discarded."
        )

        return HybridDecision(
            final_tactical_mode=comparison.deterministic_mode,
            final_agent=comparison.deterministic_agent,
            final_action=comparison.deterministic_action,
            final_confidence=_clamp(comparison.deterministic_confidence),
            decision_source=DecisionSource.DETERMINISTIC_FALLBACK,
            agreement_type=AgreementLevel.DISAGREEMENT,
            reason=reason,
        )


def resolve_hybrid_decision(
    deterministic_decision: TeamDecision,
    llm_recommendation: TacticalRecommendation,
    comparison: DecisionComparison,
) -> HybridDecision:
    """Module-level convenience wrapper around :class:`HybridDecisionResolver`."""

    return HybridDecisionResolver().resolve(
        deterministic_decision, llm_recommendation, comparison
    )
