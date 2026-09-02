"""
Step 35 - Hybrid Decision Resolver.

Deterministic and offline: this test builds the deterministic decision
and the Nova Pro recommendation directly (no Bedrock call), runs them
through the real comparator + resolver, and checks the resolution rules.

    python -m tests.test_hybrid_decision_resolver
"""

from agents.hybrid_decision_resolver import (
    DecisionSource,
    HybridDecisionResolver,
    resolve_hybrid_decision,
)
from hybrid.decision_comparator import AgreementLevel, compare
from llm.response_parser import TacticalRecommendation
from simulation.decision import FootballAction, FootballDecision
from simulation.team_coordinator import TeamDecision

LINE = "=" * 55


def _team_decision(mode, agent, action, confidence) -> TeamDecision:
    football_action = FootballAction(action)
    decision = FootballDecision(
        action=football_action,
        target_player_id=None,
        confidence=confidence,
        reason="deterministic test decision",
    )
    return TeamDecision(
        tactical_mode=mode,
        agent_decisions={agent: decision},
        primary_action=football_action,
        primary_agent=agent,
        reason="deterministic test decision",
        conflicts=[],
    )


def _nova(mode, agent, action, confidence) -> TacticalRecommendation:
    return TacticalRecommendation(
        tactical_mode=mode,
        recommended_agent=agent,
        recommended_action=action,
        confidence=confidence,
        reason="nova pro test recommendation",
    )


def _print_report(name, det, nova, hybrid) -> None:
    print("\n" + LINE)
    print("⚽ HYBRID DECISION RESOLUTION")
    print(LINE)
    print(f"\nScenario:\n{name}")
    print("\nDeterministic Decision:")
    print(f"{det.tactical_mode} / {det.primary_agent} / {det.primary_action.value}")
    print(
        f"Confidence: "
        f"{det.agent_decisions[det.primary_agent].confidence:.2f}"
    )
    print("\nNova Pro Recommendation:")
    print(
        f"{nova.tactical_mode} / {nova.recommended_agent} / "
        f"{nova.recommended_action}"
    )
    print(f"Confidence: {nova.confidence:.2f}")
    print("\nFinal Hybrid Decision:")
    print(
        f"{hybrid.final_tactical_mode} / {hybrid.final_agent} / "
        f"{hybrid.final_action}"
    )
    print(f"Confidence: {hybrid.final_confidence:.2f}")
    print(f"\nDecision Source:\n{hybrid.decision_source.value}")
    print(f"\nAgreement:\n{hybrid.agreement_type.value}")
    print(f"\nReason:\n{hybrid.reason}")
    print(LINE)


def _resolve(name, det, nova):
    comparison = compare(det, nova)
    hybrid = HybridDecisionResolver().resolve(det, nova, comparison)
    _print_report(name, det, nova, hybrid)
    return hybrid


def test_scenario_1_full_agreement():
    det = _team_decision("ATTACK", "striker", "SHOOT", 0.90)
    nova = _nova("ATTACK", "striker", "SHOOT", 0.85)

    hybrid = _resolve("Clear Shooting Opportunity", det, nova)

    assert hybrid.final_tactical_mode == "ATTACK"
    assert hybrid.final_agent == "striker"
    assert hybrid.final_action == "SHOOT"
    assert hybrid.decision_source is DecisionSource.AGREEMENT
    assert hybrid.agreement_type is AgreementLevel.FULL_AGREEMENT
    # moderate, capped increase over the raw average
    assert 0.875 < hybrid.final_confidence <= 1.0


def test_scenario_2_partial_agreement_priority_keeps_deterministic():
    det = _team_decision("ATTACK", "midfielder", "PASS", 0.85)
    nova = _nova("ATTACK", "striker", "MOVE", 0.85)

    hybrid = _resolve("Midfield Build-Up (priority: PASS > MOVE)", det, nova)

    # PASS outranks MOVE in ATTACK -> deterministic action wins.
    assert hybrid.final_tactical_mode == "ATTACK"
    assert hybrid.final_agent == "midfielder"
    assert hybrid.final_action == "PASS"
    assert hybrid.decision_source is DecisionSource.HYBRID_RESOLUTION
    assert hybrid.agreement_type is AgreementLevel.PARTIAL_AGREEMENT


def test_scenario_2b_partial_agreement_priority_can_pick_nova():
    det = _team_decision("ATTACK", "midfielder", "MOVE", 0.70)
    nova = _nova("ATTACK", "striker", "SHOOT", 0.88)

    hybrid = _resolve("Nova Sees a Shot (priority: SHOOT > MOVE)", det, nova)

    # SHOOT outranks MOVE in ATTACK -> Nova's action is selected.
    assert hybrid.final_agent == "striker"
    assert hybrid.final_action == "SHOOT"
    assert hybrid.decision_source is DecisionSource.HYBRID_RESOLUTION
    assert hybrid.agreement_type is AgreementLevel.PARTIAL_AGREEMENT


def test_scenario_3_tactical_mode_disagreement():
    det = _team_decision("DEFENSE", "defender", "PRESS", 0.80)
    nova = _nova("ATTACK", "striker", "SHOOT", 0.90)

    hybrid = _resolve("Conflicting Reads", det, nova)

    assert hybrid.final_tactical_mode == "DEFENSE"
    assert hybrid.final_agent == "defender"
    assert hybrid.final_action == "PRESS"
    assert hybrid.decision_source is DecisionSource.DETERMINISTIC_FALLBACK
    assert hybrid.agreement_type is AgreementLevel.DISAGREEMENT
    assert hybrid.final_confidence == 0.80
    # Nova recommendation is acknowledged, not silently dropped.
    assert "ATTACK" in hybrid.reason and "striker" in hybrid.reason


def test_resolver_is_deterministic():
    det = _team_decision("ATTACK", "midfielder", "PASS", 0.85)
    nova = _nova("ATTACK", "striker", "MOVE", 0.80)
    comparison = compare(det, nova)

    first = resolve_hybrid_decision(det, nova, comparison).as_dict()
    for _ in range(5):
        assert resolve_hybrid_decision(det, nova, comparison).as_dict() == first


def main():
    test_scenario_1_full_agreement()
    test_scenario_2_partial_agreement_priority_keeps_deterministic()
    test_scenario_2b_partial_agreement_priority_can_pick_nova()
    test_scenario_3_tactical_mode_disagreement()
    test_resolver_is_deterministic()

    print("\nAll hybrid decision resolver checks passed.")


if __name__ == "__main__":
    main()
