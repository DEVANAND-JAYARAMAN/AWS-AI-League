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

from simulation.hybrid_match_simulator import (
    HybridMatchSimulator,
    SimulationMode,
    format_statistics,
    format_tick,
)
from simulation.sample_scenario import (
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


if __name__ == "__main__":
    main()
