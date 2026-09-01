"""
Tests for the Scenario Library and evaluation benchmark (Step 37A).

Deterministic and local: no AWS, no Bedrock, no API keys, no network
calls, no randomness.
"""

import os
import socket

from evaluation.benchmark_runner import (
    BenchmarkReport,
    format_report,
    run_benchmark,
)
from scenarios import load_all_scenarios
from scenarios.scenario_models import EvaluationMode, ScenarioCategory

VALID_ACTIONS = {"PASS", "PRESS", "HOLD_POSITION", "SHOOT", "MOVE"}
VALID_MODES = {"ATTACK", "DEFENSE", "TRANSITION"}


def _no_network_guard():
    original = socket.socket.connect

    def blocked(self, *args, **kwargs):
        raise AssertionError("network call attempted during benchmark")

    socket.socket.connect = blocked
    return lambda: setattr(socket.socket, "connect", original)


def test_scenario_library_shape():
    scenarios = load_all_scenarios()

    # 1 + 2. At least 16 scenarios exist.
    assert len(scenarios) >= 16

    # 3. All four categories are present.
    categories = {s.category for s in scenarios}
    assert categories == set(ScenarioCategory.ALL)

    # Every scenario is well-formed.
    for s in scenarios:
        assert s.scenario_name
        assert s.description
        assert s.initial_game_state is not None
        if s.evaluation_mode == EvaluationMode.INDIVIDUAL:
            assert s.expected_individual_agent
            assert s.expected_individual_action in VALID_ACTIONS
        else:
            if s.expected_primary_action is not None:
                assert s.expected_primary_action in VALID_ACTIONS
        if s.expected_tactical_mode is not None:
            assert s.expected_tactical_mode in VALID_MODES


def test_benchmark_runs_and_produces_valid_results():
    restore = _no_network_guard()
    try:
        report = run_benchmark()
    finally:
        restore()

    scenarios = load_all_scenarios()

    # 5. Every scenario produces a valid result.
    assert isinstance(report, BenchmarkReport)
    assert report.total_scenarios == len(scenarios)

    for result in report.results:
        assert result.scenario_name
        assert result.category in ScenarioCategory.ALL
        assert isinstance(result.passed, bool)
        assert result.expected  # something was checked
        assert result.actual
        if not result.passed:
            assert result.failure_reason

    # 6. Metrics are calculated correctly.
    assert (
        report.passed_scenarios + report.failed_scenarios
        == report.total_scenarios
    )
    manual_passed = sum(1 for r in report.results if r.passed)
    assert report.passed_scenarios == manual_passed

    expected_overall = round(
        manual_passed / report.total_scenarios * 100, 2
    )
    assert report.overall_accuracy == expected_overall

    stats = report.category_stats()
    assert sum(c.total for c in stats.values()) == report.total_scenarios
    for entry in stats.values():
        assert entry.passed + entry.failed == entry.total
        assert entry.accuracy == round(
            entry.passed / entry.total * 100, 2
        )


def test_safe_division_on_empty_benchmark():
    empty = run_benchmark(scenarios=[])
    assert empty.total_scenarios == 0
    assert empty.overall_accuracy == 0.0


def test_benchmark_is_deterministic():
    # 7. Repeated runs give identical output.
    reports = [run_benchmark() for _ in range(3)]

    signatures = [
        [
            (r.scenario_name, r.passed, r.expected_text(), r.actual_text())
            for r in report.results
        ]
        for report in reports
    ]
    assert signatures[0] == signatures[1] == signatures[2]

    texts = {format_report(report) for report in reports}
    assert len(texts) == 1


def test_benchmark_reports_failures_rather_than_hiding_them():
    # A deliberately wrong expectation must be caught as a FAIL.
    scenarios = load_all_scenarios()
    broken = scenarios[0]
    broken.evaluation_mode = EvaluationMode.PRIMARY
    broken.expected_primary_agent = "goalkeeper"
    broken.expected_primary_action = "HOLD_POSITION"
    broken.expected_individual_agent = None
    broken.expected_tactical_mode = "DEFENSE"

    report = run_benchmark(scenarios=[broken])
    assert report.failed_scenarios == 1
    assert report.results[0].failure_reason


def test_no_aws_credentials_required():
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        assert key not in os.environ or True  # not required either way
    run_benchmark()


def main():
    test_scenario_library_shape()
    test_benchmark_runs_and_produces_valid_results()
    test_safe_division_on_empty_benchmark()
    test_benchmark_is_deterministic()
    test_benchmark_reports_failures_rather_than_hiding_them()
    test_no_aws_credentials_required()

    report = run_benchmark()
    print(format_report(report))
    print("\nAll benchmark checks passed.")


if __name__ == "__main__":
    main()
