"""
First real LLM tactical analysis - Amazon Nova Pro via the Bedrock
Converse API.

    Existing GameState  (Clear Shooting Opportunity scenario)
        -> LLMTacticalAnalyzer
        -> Amazon Nova Pro on Bedrock   <-- REAL network call
        -> validated TacticalRecommendation

>>> WARNING <<<
Running this test makes a real Amazon Bedrock ``converse`` call and
therefore requires:
  * valid AWS credentials in the default provider chain
  * Amazon Bedrock access in the configured region
  * access to the Nova Pro inference profile (apac.amazon.nova-pro-v1:0)
It may incur a small AWS charge.

It is intentionally NOT part of the deterministic regression suite. Run
it explicitly:

    python -m tests.test_bedrock_tactical_analyzer

The deterministic engine and the evaluation benchmark are unaffected -
the LLM output here is advisory only and never touches a GameState.
"""

import sys

from llm.bedrock_client import BedrockInvocationError
from llm.llm_tactical_analyzer import LLMTacticalAnalyzer
from llm.response_parser import TacticalRecommendation, TacticalValidationError
from llm.tactical_prompt import ALLOWED_ACTIONS, ALLOWED_MODES
from simulation.sample_scenario import create_shooting_scenario

LINE = "=" * 55


def _print_recommendation(rec: TacticalRecommendation) -> None:
    print("\n" + LINE)
    print("⚽ AMAZON NOVA PRO TACTICAL ANALYSIS")
    print(LINE)
    print(f"\nTactical Mode: {rec.tactical_mode}")
    print(f"\nRecommended Agent: {rec.recommended_agent}")
    print(f"\nRecommended Action: {rec.recommended_action}")
    print(f"\nConfidence: {rec.confidence:.2f}")
    print("\nReason:")
    print(rec.reason)
    print(LINE)


def run_real_analysis() -> TacticalRecommendation:
    game_state = create_shooting_scenario()
    valid_agents = {p.player_id for p in game_state.our_team}

    analyzer = LLMTacticalAnalyzer()
    print(
        f"Calling Bedrock Converse model '{analyzer.client.model_id}' "
        f"in region '{analyzer.client.region_name}' ..."
    )

    recommendation = analyzer.analyze(game_state)

    # The parser already validated this; assert the contract again so the
    # test fails loudly if that ever regresses.
    assert recommendation.tactical_mode in ALLOWED_MODES
    assert recommendation.recommended_action in ALLOWED_ACTIONS
    assert recommendation.recommended_agent in valid_agents
    assert 0.0 <= recommendation.confidence <= 1.0
    assert recommendation.reason

    _print_recommendation(recommendation)
    return recommendation


def main() -> int:
    try:
        run_real_analysis()
    except BedrockInvocationError as exc:
        print(f"\n[FAIL] Bedrock call failed: {exc}")
        print(
            "Check AWS credentials (aws sts get-caller-identity), the "
            "region, and Bedrock / Nova Pro inference profile access."
        )
        return 1
    except TacticalValidationError as exc:
        print(f"\n[FAIL] Nova Pro returned an invalid recommendation: {exc}")
        return 1

    print("\nReal Amazon Nova Pro tactical analysis succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
