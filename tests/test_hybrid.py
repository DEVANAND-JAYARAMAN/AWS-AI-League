"""
Hybrid deterministic + Amazon Nova Pro layer. The decision-resolver and Strands-pipeline cases are offline; the Bedrock, hybrid-analyzer and hybrid-match-simulator cases make REAL Bedrock calls and need AWS credentials + Nova Pro access.

Consolidated from the former per-component test scripts. Each _case_* wraps
one original script; run this file directly to run them all:

    python -m tests.test_hybrid
"""

import sys
import traceback

def _case_test_hybrid_decision_resolver():
    """
    Step 35 - Hybrid Decision Resolver.

    Deterministic and offline: this test builds the deterministic decision
    and the Nova Pro recommendation directly (no Bedrock call), runs them
    through the real comparator + resolver, and checks the resolution rules.

        python -m tests.test_hybrid_decision_resolver
    """

    from app.ai.decision_resolver import (
        DecisionSource,
        HybridDecisionResolver,
        resolve_hybrid_decision,
    )
    from app.ai.decision_comparator import AgreementLevel, compare
    from app.ai.response_parser import TacticalRecommendation
    from app.core.decisions import FootballAction, FootballDecision
    from app.core.team_coordinator import TeamDecision

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
    _rc = main()
    if _rc:
        raise SystemExit(f'test_hybrid_decision_resolver returned exit code {_rc}')


def _case_test_strands_pipeline():
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

    from app.strands import (
        EvaluationAgentAdapter,
        SimulationAgentAdapter,
        TacticalAgentAdapter,
    )
    from app.core.sample_scenario import create_midfielder_pass_scenario
    from app.core.serialization import serialize_game_state

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
            from app.agents.coordinator import AgentCoordinator

            direct = AgentCoordinator().get_coordinated_team_decision(game_state)
            assert direct.primary_agent == team_decision["primary_agent"]
            assert direct.primary_action.value == team_decision["primary_action"]

            print("\nAll Strands pipeline checks passed.")

        finally:
            restore()


    def main():
        test_strands_pipeline()
    _rc = main()
    if _rc:
        raise SystemExit(f'test_strands_pipeline returned exit code {_rc}')


def _case_test_bedrock_tactical_analyzer():
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

    from app.ai.bedrock_client import BedrockInvocationError
    from app.ai.bedrock_nova import LLMTacticalAnalyzer
    from app.ai.response_parser import TacticalRecommendation, TacticalValidationError
    from app.ai.tactical_prompt import ALLOWED_ACTIONS, ALLOWED_MODES
    from app.core.sample_scenario import create_shooting_scenario

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
    _rc = main()
    if _rc:
        raise SystemExit(f'test_bedrock_tactical_analyzer returned exit code {_rc}')


def _case_test_hybrid_tactical_analyzer():
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

    from app.ai.decision_comparator import AgreementLevel
    from app.ai.hybrid_analyzer import HybridTacticalAnalyzer
    from app.ai.bedrock_client import BedrockInvocationError
    from app.ai.response_parser import TacticalValidationError
    from app.core.sample_scenario import (
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
    _rc = main()
    if _rc:
        raise SystemExit(f'test_hybrid_tactical_analyzer returned exit code {_rc}')


def _case_test_hybrid_match_simulator():
    """
    Step 36 - hybrid match simulator.

        scenario GameState
            -> HybridMatchSimulator(mode=...)
            -> per tick: deterministic + (optional) Nova Pro + resolver
            -> FootballSimulationEngine executes the FINAL decision
            -> HybridMatchResult + statistics

    >>> WARNING <<<
    Tests 2 and 3 make REAL Amazon Bedrock ``converse`` calls (one per
    hybrid tick that is not skipped). Scenarios are kept short on purpose.
    Test 1 makes ZERO Bedrock calls.

    Run explicitly:

        python -m tests.test_hybrid_match_simulator

    The deterministic benchmark (tests/test_benchmark.py) is independent of
    this and needs no AWS access.
    """

    from app.ai.match_simulator import (
        HybridMatchSimulator,
        SimulationMode,
        format_statistics,
        format_tick,
    )
    from app.core.sample_scenario import (
        create_midfielder_pass_scenario,
        create_shooting_scenario,
    )

    LINE = "=" * 55


    class _ExplodingAnalyzer:
        """Stand-in LLM analyzer that fails the test if it is ever called."""

        called = False

        def analyze(self, game_state):  # noqa: D401 - test double
            _ExplodingAnalyzer.called = True
            raise AssertionError("Nova Pro was called during a no-Nova test")


    def _print_header(mode) -> None:
        print("\n" + LINE)
        print("⚽ HYBRID MATCH SIMULATION")
        print(LINE)
        print(f"\nSimulation Mode: {mode}\n")


    def _print_match(result) -> None:
        for tick in result.tick_results:
            print()
            print(format_tick(tick))
        print()
        print(format_statistics(result))


    def _assert_statistics_consistent(result) -> None:
        stats = result.statistics
        n = result.total_ticks

        assert stats["nova_calls"] + stats["nova_skipped"] == n
        assert sum(stats["decision_sources"].values()) == n
        assert sum(stats["primary_actions"].values()) == n
        assert sum(stats["final_tactical_modes"].values()) == n
        assert sum(stats["agreement_types"].values()) <= n
        assert result.final_game_state is not None
        for tick in result.tick_results:
            assert tick.final_decision["action"] in {
                "PASS", "SHOOT", "MOVE", "PRESS", "HOLD_POSITION"
            }
            assert tick.game_state_before is not None
            assert tick.game_state_after is not None


    # ---------------------------------------------------------------------------
    # Test 1 - Deterministic only (no Bedrock)
    # ---------------------------------------------------------------------------

    def test_deterministic_only_makes_no_nova_call():
        _ExplodingAnalyzer.called = False

        sim = HybridMatchSimulator(
            create_shooting_scenario(),
            mode=SimulationMode.DETERMINISTIC_ONLY,
            max_ticks=3,
            llm_analyzer=_ExplodingAnalyzer(),
        )
        result = sim.run()

        _print_header(result.simulation_mode)
        _print_match(result)

        assert _ExplodingAnalyzer.called is False
        assert result.total_ticks == 3
        for tick in result.tick_results:
            assert tick.nova_called is False
            assert tick.decision_source == "DETERMINISTIC_ONLY"
            assert tick.agreement_type is None
        assert result.statistics["nova_calls"] == 0
        _assert_statistics_consistent(result)


    # ---------------------------------------------------------------------------
    # Test 2 - Hybrid match (real Nova Pro calls)
    # ---------------------------------------------------------------------------

    def test_hybrid_match_runs_multiple_ticks():
        sim = HybridMatchSimulator(
            create_midfielder_pass_scenario(),
            mode=SimulationMode.HYBRID,
            max_ticks=3,
        )
        result = sim.run()

        _print_header(result.simulation_mode)
        _print_match(result)

        assert result.total_ticks == 3
        assert len(result.tick_results) == 3
        assert result.statistics["nova_calls"] > 0
        # every hybrid tick called Nova and produced a real comparison
        for tick in result.tick_results:
            assert tick.nova_called is True
            assert tick.nova_recommendation is not None
            assert tick.decision_source in {
                "AGREEMENT", "HYBRID_RESOLUTION", "DETERMINISTIC_FALLBACK"
            }
        _assert_statistics_consistent(result)


    # ---------------------------------------------------------------------------
    # Test 3 - Hybrid on key decisions (Nova only for PASS / SHOOT / PRESS)
    # ---------------------------------------------------------------------------

    def test_hybrid_on_key_decisions_skips_non_key_actions():
        # midfielder_pass deterministic sequence over 4 ticks: PASS, SHOOT, MOVE, MOVE
        sim = HybridMatchSimulator(
            create_midfielder_pass_scenario(),
            mode=SimulationMode.HYBRID_ON_KEY_DECISIONS,
            max_ticks=4,
            key_actions={"PASS", "SHOOT", "PRESS"},
        )
        result = sim.run()

        _print_header(result.simulation_mode)
        _print_match(result)

        for tick in result.tick_results:
            det_action = tick.deterministic_decision["action"]
            if det_action in {"PASS", "SHOOT", "PRESS"}:
                assert tick.nova_called is True, f"expected Nova call for {det_action}"
            if det_action in {"MOVE", "HOLD_POSITION"}:
                assert tick.nova_called is False, f"expected Nova skip for {det_action}"
                assert tick.decision_source == "DETERMINISTIC_ONLY"
                assert tick.nova_skip_reason is not None

        assert result.statistics["nova_calls"] >= 1
        assert result.statistics["nova_skipped"] >= 1
        _assert_statistics_consistent(result)


    def main():
        test_deterministic_only_makes_no_nova_call()
        test_hybrid_match_runs_multiple_ticks()
        test_hybrid_on_key_decisions_skips_non_key_actions()

        print("\nAll hybrid match simulator checks passed.")
    _rc = main()
    if _rc:
        raise SystemExit(f'test_hybrid_match_simulator returned exit code {_rc}')




_CASES = [
    ("test_hybrid_decision_resolver", _case_test_hybrid_decision_resolver),
    ("test_strands_pipeline", _case_test_strands_pipeline),
    ("test_bedrock_tactical_analyzer", _case_test_bedrock_tactical_analyzer),
    ("test_hybrid_tactical_analyzer", _case_test_hybrid_tactical_analyzer),
    ("test_hybrid_match_simulator", _case_test_hybrid_match_simulator)
]


def main():
    failures = []
    for label, fn in _CASES:
        print("\n" + "#" * 72)
        print("# " + label)
        print("#" * 72)
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - report and continue
            traceback.print_exc()
            failures.append((label, exc))
    print("\n" + "=" * 72)
    if failures:
        print(f"{len(failures)} case(s) FAILED: {[n for n, _ in failures]}")
        sys.exit(1)
    print(f"All {len(_CASES)} case(s) passed.")


if __name__ == "__main__":
    main()
