"""
Benchmark runner.

Runs every scenario in the scenario library through the *existing*
deterministic football intelligence (``AgentCoordinator`` ->
``coordinate_team_decision``) and compares the actual decision against
the scenario's expected behaviour.

This module contains no football decision logic of its own - it only
calls the existing pipeline and records PASS / FAIL.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.agents.coordinator import AgentCoordinator
from app.evaluation.scenarios import load_all_scenarios
from app.evaluation.scenarios.scenario_models import EvaluationMode, Scenario, ScenarioCategory


# ----------------------------------------------------------------------
# Result models
# ----------------------------------------------------------------------

@dataclass
class ScenarioResult:
    """Outcome of running one scenario through the pipeline."""

    scenario_name: str
    category: str
    evaluation_mode: str
    expected: Dict[str, str]
    actual: Dict[str, str]
    passed: bool
    failure_reason: Optional[str] = None

    def expected_text(self) -> str:
        return _format_pairs(self.expected)

    def actual_text(self) -> str:
        return _format_pairs(self.actual)


@dataclass
class CategoryStats:
    category: str
    total: int = 0
    passed: int = 0

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def accuracy(self) -> float:
        return _safe_accuracy(self.passed, self.total)


@dataclass
class BenchmarkReport:
    """Aggregated benchmark outcome."""

    results: List[ScenarioResult] = field(default_factory=list)

    @property
    def total_scenarios(self) -> int:
        return len(self.results)

    @property
    def passed_scenarios(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_scenarios(self) -> int:
        return self.total_scenarios - self.passed_scenarios

    @property
    def overall_accuracy(self) -> float:
        return _safe_accuracy(self.passed_scenarios, self.total_scenarios)

    @property
    def failing_scenarios(self) -> List[ScenarioResult]:
        return [r for r in self.results if not r.passed]

    def category_stats(self) -> Dict[str, CategoryStats]:
        stats: Dict[str, CategoryStats] = {}
        for result in self.results:
            entry = stats.setdefault(
                result.category, CategoryStats(category=result.category)
            )
            entry.total += 1
            if result.passed:
                entry.passed += 1
        return stats


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _safe_accuracy(passed: int, total: int) -> float:
    """passed / total * 100, guarding against division by zero."""

    if total <= 0:
        return 0.0
    return round(passed / total * 100, 2)


def _format_pairs(pairs: Dict[str, str]) -> str:
    if not pairs:
        return "(nothing checked)"
    return ", ".join(f"{key}={value}" for key, value in pairs.items())


# ----------------------------------------------------------------------
# Core evaluation
# ----------------------------------------------------------------------

def evaluate_scenario(
    scenario: Scenario,
    coordinator: AgentCoordinator,
) -> ScenarioResult:
    """Run one scenario through the existing pipeline and grade it."""

    team_decision = coordinator.get_coordinated_team_decision(
        scenario.initial_game_state
    )

    expected: Dict[str, str] = {}
    actual: Dict[str, str] = {}
    failures: List[str] = []

    # --- Optional tactical-mode check (applies in any mode) ---
    if scenario.expected_tactical_mode is not None:
        expected["mode"] = scenario.expected_tactical_mode
        actual["mode"] = team_decision.tactical_mode
        if team_decision.tactical_mode != scenario.expected_tactical_mode:
            failures.append(
                f"tactical mode expected {scenario.expected_tactical_mode}, "
                f"got {team_decision.tactical_mode}"
            )

    if scenario.evaluation_mode == EvaluationMode.INDIVIDUAL:
        agent_id = scenario.expected_individual_agent
        agent_decision = team_decision.agent_decisions.get(agent_id)

        expected["agent"] = agent_id
        expected["action"] = scenario.expected_individual_action

        if agent_decision is None:
            actual["agent"] = agent_id
            actual["action"] = "(no decision)"
            failures.append(f"no decision found for agent '{agent_id}'")
        else:
            actual["agent"] = agent_id
            actual["action"] = agent_decision.action.value
            if agent_decision.action.value != scenario.expected_individual_action:
                failures.append(
                    f"{agent_id} action expected "
                    f"{scenario.expected_individual_action}, "
                    f"got {agent_decision.action.value}"
                )

    else:  # EvaluationMode.PRIMARY
        if scenario.expected_primary_agent is not None:
            expected["agent"] = scenario.expected_primary_agent
            actual["agent"] = team_decision.primary_agent
            if team_decision.primary_agent != scenario.expected_primary_agent:
                failures.append(
                    f"primary agent expected "
                    f"{scenario.expected_primary_agent}, "
                    f"got {team_decision.primary_agent}"
                )

        if scenario.expected_primary_action is not None:
            expected["action"] = scenario.expected_primary_action
            actual["action"] = team_decision.primary_action.value
            if (
                team_decision.primary_action.value
                != scenario.expected_primary_action
            ):
                failures.append(
                    f"primary action expected "
                    f"{scenario.expected_primary_action}, "
                    f"got {team_decision.primary_action.value}"
                )

    passed = not failures

    return ScenarioResult(
        scenario_name=scenario.scenario_name,
        category=scenario.category,
        evaluation_mode=scenario.evaluation_mode,
        expected=expected,
        actual=actual,
        passed=passed,
        failure_reason=None if passed else "; ".join(failures),
    )


def run_benchmark(scenarios: Optional[List[Scenario]] = None) -> BenchmarkReport:
    """
    Load scenarios (or use the supplied list), run each one through the
    existing football intelligence and return a :class:`BenchmarkReport`.

    Deterministic: calling this twice with the same scenarios always
    yields identical results.
    """

    if scenarios is None:
        scenarios = load_all_scenarios()

    coordinator = AgentCoordinator()

    report = BenchmarkReport()
    for scenario in scenarios:
        report.results.append(evaluate_scenario(scenario, coordinator))
    return report


# ----------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------

_LINE = "=" * 60
_SUBLINE = "-" * 60


def format_report(report: BenchmarkReport) -> str:
    """Build the full console report as a single string."""

    lines: List[str] = []
    lines.append(_LINE)
    lines.append("⚽ AGENTIC FOOTBALL EVALUATION BENCHMARK")
    lines.append(_LINE)

    for result in report.results:
        status = "PASS ✅" if result.passed else "FAIL ❌"
        lines.append("")
        lines.append(f"Scenario: {result.scenario_name}")
        lines.append(f"Category: {result.category}")
        lines.append(f"Mode: {result.evaluation_mode}")
        lines.append("")
        lines.append("Expected:")
        lines.append(f"  {result.expected_text()}")
        lines.append("")
        lines.append("Actual:")
        lines.append(f"  {result.actual_text()}")
        lines.append("")
        lines.append(f"Result: {status}")
        if not result.passed:
            lines.append(f"Reason: {result.failure_reason}")
        lines.append(_SUBLINE)

    lines.append("")
    lines.append(_LINE)
    lines.append("📊 BENCHMARK SUMMARY")
    lines.append(_LINE)
    lines.append("")
    lines.append(f"Total Scenarios: {report.total_scenarios}")
    lines.append(f"Passed: {report.passed_scenarios}")
    lines.append(f"Failed: {report.failed_scenarios}")
    lines.append("")
    lines.append(f"Overall Accuracy: {report.overall_accuracy}%")
    lines.append("")
    lines.append("Category Results:")

    stats = report.category_stats()
    for category in ScenarioCategory.ALL:
        entry = stats.get(category)
        if entry is None:
            continue
        lines.append("")
        lines.append(category)
        lines.append(f"Passed: {entry.passed} / {entry.total}")
        lines.append(f"Accuracy: {entry.accuracy}%")

    if report.failing_scenarios:
        lines.append("")
        lines.append("Failing Scenarios:")
        for result in report.failing_scenarios:
            lines.append(f"  - {result.scenario_name}: {result.failure_reason}")

    lines.append("")
    return "\n".join(lines)


def main():
    report = run_benchmark()
    print(format_report(report))


if __name__ == "__main__":
    main()
