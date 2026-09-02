"""
Step 39 - hybrid tactical analysis (deterministic vs Amazon Nova Pro).

    Existing scenarios
        -> HybridTacticalAnalyzer
             -> deterministic AgentCoordinator  (no AWS)
             -> LLMTacticalAnalyzer / Nova Pro  <-- REAL Bedrock calls
             -> DecisionComparison
        -> agreement metrics

>>> WARNING <<<
This test makes REAL Amazon Bedrock ``converse`` calls (one per
scenario) and needs:
  * valid AWS credentials in the default provider chain
  * Amazon Bedrock access in the configured region
  * access to the Nova Pro inference profile (apac.amazon.nova-pro-v1:0)

It is NOT part of the deterministic regression suite and must be run
explicitly:

    python -m tests.test_hybrid_tactical_analyzer

The deterministic benchmark (tests/test_benchmark.py) stays independent
of this and needs no AWS access.
"""

import sys

from hybrid.decision_comparator import AgreementLevel
from hybrid.hybrid_tactical_analyzer import HybridTacticalAnalyzer
from llm.bedrock_client import BedrockInvocationError
from llm.response_parser import TacticalValidationError
from simulation.sample_scenario import (
    create_defender_press_scenario,
    create_midfielder_pass_scenario,
    create_shooting_scenario,
)

LINE = "=" * 55

SCENARIOS = [
    ("Clear Shooting Opportunity", create_shooting_scenario),
    ("Open Forward Pass", create_midfielder_pass_scenario),
    ("Defensive Pressure", create_defender_press_scenario),
]


def _yn(value: bool) -> str:
    return "YES" if value else "NO"


def _print_comparison(name: str, comparison) -> None:
    det = comparison.deterministic_decision
    rec = comparison.llm_recommendation

    print("\n" + LINE)
    print("⚽ HYBRID TACTICAL ANALYSIS")
    print(LINE)
    print(f"\nScenario:\n{name}")

    print("\nDETERMINISTIC ENGINE\n")
    print(f"Tactical Mode: {det.tactical_mode}")
    print(f"Primary Agent: {det.primary_agent}")
    print(f"Primary Action: {det.primary_action.value}")
    print(f"Confidence: {comparison.deterministic_confidence:.2f}")

    print("\nAMAZON NOVA PRO\n")
    print(f"Tactical Mode: {rec.tactical_mode}")
    print(f"Recommended Agent: {rec.recommended_agent}")
    print(f"Recommended Action: {rec.recommended_action}")
    print(f"Confidence: {comparison.llm_confidence:.2f}")

    print("\nCOMPARISON\n")
    print(f"Mode Match: {_yn(comparison.mode_match)}")
    print(f"Agent Match: {_yn(comparison.agent_match)}")
    print(f"Action Match: {_yn(comparison.action_match)}")

    if comparison.differences():
        print("\nDifferences:")
        for diff in comparison.differences():
            print(f"  - {diff}")

    print(f"\nOverall Agreement: {comparison.overall_agreement.value}")
    print(LINE)


def _print_summary(metrics) -> None:
    print("\n" + LINE)
    print("📊 HYBRID EVALUATION SUMMARY")
    print(LINE)
    print(f"\nTotal Scenarios: {metrics.total}")
    print(f"\nFull Agreement: {metrics.full_agreements}")
    print(f"Partial Agreement: {metrics.partial_agreements}")
    print(f"Disagreement: {metrics.disagreements}")
    print(f"\nMode Agreement: {metrics.mode_agreement_pct}%")
    print(f"\nAgent Agreement: {metrics.agent_agreement_pct}%")
    print(f"\nAction Agreement: {metrics.action_agreement_pct}%")
    print(LINE)


def run() -> int:
    analyzer = HybridTacticalAnalyzer()
    print(
        f"Using Nova Pro model '{analyzer.llm_analyzer.client.model_id}' "
        f"in region '{analyzer.llm_analyzer.client.region_name}'"
    )

    named_states = [(name, builder()) for name, builder in SCENARIOS]

    try:
        results, metrics = analyzer.analyze_scenarios(named_states)
    except BedrockInvocationError as exc:
        print(f"\n[FAIL] Bedrock call failed: {exc}")
        print("Check AWS credentials, region, and Nova Pro access.")
        return 1
    except TacticalValidationError as exc:
        print(f"\n[FAIL] Nova Pro returned an invalid recommendation: {exc}")
        return 1

    for name, comparison in results:
        _print_comparison(name, comparison)

    _print_summary(metrics)

    # Sanity checks on the computed metrics (not on agreement itself).
    assert metrics.total == len(SCENARIOS)
    assert (
        metrics.full_agreements
        + metrics.partial_agreements
        + metrics.disagreements
        == metrics.total
    )
    for _, comparison in results:
        assert comparison.overall_agreement in AgreementLevel
        # mode mismatch must never be classified as agreement
        if not comparison.mode_match:
            assert comparison.overall_agreement is AgreementLevel.DISAGREEMENT

    print("\nHybrid tactical analysis completed with real Nova Pro calls.")
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
