"""
Model evaluation framework.

Runs the *existing* 16-scenario benchmark against any tactical model
provider (DETERMINISTIC / NOVA_BASE / NOVA_CUSTOM) and reports how the
model's recommendations line up with the deterministic baseline
expectations.

Guarantees:

    * The deterministic benchmark stays the yardstick - scenarios and
      their expected outputs are never modified here.
    * Metrics are computed from real calls only. If a provider is
      unavailable (no credentials, no customized model yet) or a call
      fails, the result is reported as ``NOT RUN`` - never fabricated.
    * A test set of fine-tuning examples can be scored too (for the
      held-out evaluation script), reusing the same comparison logic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.ai.response_parser import TacticalRecommendation
from app.evaluation.scenarios import load_all_scenarios
from app.evaluation.scenarios.scenario_models import EvaluationMode, Scenario

from app.fine_tuning.custom_model_client import (
    CustomModelUnavailableError,
    ModelProvider,
    TacticalModelClient,
)

NOT_RUN = "NOT RUN"


# ----------------------------------------------------------------------
# Result models
# ----------------------------------------------------------------------

@dataclass
class ScenarioModelResult:
    scenario_name: str
    category: str
    expected_mode: Optional[str]
    expected_agent: Optional[str]
    expected_action: Optional[str]
    model_mode: Optional[str] = None
    model_agent: Optional[str] = None
    model_action: Optional[str] = None
    mode_match: bool = False
    agent_match: bool = False
    action_match: bool = False
    mode_checked: bool = False
    agent_checked: bool = False
    action_checked: bool = False
    full_match: bool = False
    partial_match: bool = False
    error: Optional[str] = None
    latency_ms: Optional[float] = None

    @property
    def invalid(self) -> bool:
        return self.error is not None


@dataclass
class ModelEvaluationReport:
    provider: str
    ran: bool
    reason_not_run: Optional[str] = None
    results: List[ScenarioModelResult] = field(default_factory=list)

    # -- aggregate metrics (None-safe; "NOT RUN" when not ran) --

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def scored(self) -> int:
        return sum(1 for r in self.results if not r.invalid)

    @property
    def invalid_responses(self) -> int:
        return sum(1 for r in self.results if r.invalid)

    @property
    def full_agreements(self) -> int:
        return sum(1 for r in self.results if r.full_match)

    @property
    def partial_agreements(self) -> int:
        return sum(1 for r in self.results if r.partial_match)

    @property
    def disagreements(self) -> int:
        return sum(
            1 for r in self.results
            if not r.invalid and not r.full_match and not r.partial_match
        )

    def _pct(self, count: int, denom: Optional[int] = None) -> Optional[float]:
        if not self.ran:
            return None
        base = self.scored if denom is None else denom
        if base == 0:
            return None
        return round(count / base * 100, 2)

    @property
    def mode_accuracy(self) -> Optional[float]:
        # Accuracy over the scored scenarios that actually assert a mode.
        checked = sum(1 for r in self.results if r.mode_checked and not r.invalid)
        return self._pct(
            sum(1 for r in self.results if r.mode_match), denom=checked
        )

    @property
    def agent_accuracy(self) -> Optional[float]:
        checked = sum(1 for r in self.results if r.agent_checked and not r.invalid)
        return self._pct(
            sum(1 for r in self.results if r.agent_match), denom=checked
        )

    @property
    def action_accuracy(self) -> Optional[float]:
        checked = sum(1 for r in self.results if r.action_checked and not r.invalid)
        return self._pct(
            sum(1 for r in self.results if r.action_match), denom=checked
        )

    @property
    def full_agreement_pct(self) -> Optional[float]:
        return self._pct(self.full_agreements)

    @property
    def average_latency_ms(self) -> Optional[float]:
        lat = [r.latency_ms for r in self.results if r.latency_ms is not None]
        if not lat:
            return None
        return round(sum(lat) / len(lat), 2)


# ----------------------------------------------------------------------
# Expected-value extraction (mirrors the benchmark's own rules)
# ----------------------------------------------------------------------

def _expected_for(scenario: Scenario) -> Dict[str, Optional[str]]:
    if scenario.evaluation_mode == EvaluationMode.INDIVIDUAL:
        return {
            "mode": scenario.expected_tactical_mode,
            "agent": scenario.expected_individual_agent,
            "action": scenario.expected_individual_action,
        }
    return {
        "mode": scenario.expected_tactical_mode,
        "agent": scenario.expected_primary_agent,
        "action": scenario.expected_primary_action,
    }


def _grade(
    expected: Dict[str, Optional[str]],
    rec: TacticalRecommendation,
) -> Dict[str, bool]:
    mode_match = (
        expected["mode"] is None
        or str(rec.tactical_mode).upper() == str(expected["mode"]).upper()
    )
    agent_match = (
        expected["agent"] is None
        or str(rec.recommended_agent).lower() == str(expected["agent"]).lower()
    )
    action_match = (
        expected["action"] is None
        or str(rec.recommended_action).upper() == str(expected["action"]).upper()
    )
    checked_mode = expected["mode"] is not None
    checked_agent = expected["agent"] is not None
    checked_action = expected["action"] is not None

    full = mode_match and agent_match and action_match
    # partial = at least one checked field matches but not everything
    any_match = (
        (checked_mode and mode_match)
        or (checked_agent and agent_match)
        or (checked_action and action_match)
    )
    return {
        "mode_match": mode_match and checked_mode,
        "agent_match": agent_match and checked_agent,
        "action_match": action_match and checked_action,
        "mode_checked": checked_mode,
        "agent_checked": checked_agent,
        "action_checked": checked_action,
        "full_match": full,
        "partial_match": (not full) and any_match,
    }


# ----------------------------------------------------------------------
# Core evaluation
# ----------------------------------------------------------------------

def evaluate_provider(
    client: TacticalModelClient,
    scenarios: Optional[List[Scenario]] = None,
) -> ModelEvaluationReport:
    """
    Run every scenario through ``client`` and grade its recommendation
    against the benchmark expectations.

    If the provider is unavailable up front, returns a report with
    ``ran=False`` (reported as ``NOT RUN``). If individual calls fail, they
    are recorded as invalid responses rather than crashing the run.
    """

    provider_name = client.provider.value

    if not client.is_available():
        reason = (
            "NOVA_CUSTOM has no customized model id yet"
            if client.provider is ModelProvider.NOVA_CUSTOM
            else "provider unavailable"
        )
        return ModelEvaluationReport(
            provider=provider_name, ran=False, reason_not_run=reason
        )

    scenarios = scenarios if scenarios is not None else load_all_scenarios()
    report = ModelEvaluationReport(provider=provider_name, ran=True)

    for scenario in scenarios:
        expected = _expected_for(scenario)
        result = ScenarioModelResult(
            scenario_name=scenario.scenario_name,
            category=scenario.category,
            expected_mode=expected["mode"],
            expected_agent=expected["agent"],
            expected_action=expected["action"],
        )

        # For the deterministic baseline, mirror the benchmark's own grading:
        # INDIVIDUAL scenarios are judged on a specific agent's decision.
        prefer_agent = None
        if (
            client.provider is ModelProvider.DETERMINISTIC
            and scenario.evaluation_mode == EvaluationMode.INDIVIDUAL
        ):
            prefer_agent = scenario.expected_individual_agent

        try:
            start = time.perf_counter()
            rec = client.analyze(
                scenario.initial_game_state, prefer_agent=prefer_agent
            )
            result.latency_ms = round((time.perf_counter() - start) * 1000, 2)

            result.model_mode = rec.tactical_mode
            result.model_agent = rec.recommended_agent
            result.model_action = rec.recommended_action

            graded = _grade(expected, rec)
            result.mode_match = graded["mode_match"]
            result.agent_match = graded["agent_match"]
            result.action_match = graded["action_match"]
            result.mode_checked = graded["mode_checked"]
            result.agent_checked = graded["agent_checked"]
            result.action_checked = graded["action_checked"]
            result.full_match = graded["full_match"]
            result.partial_match = graded["partial_match"]
        except CustomModelUnavailableError as exc:
            # Whole provider is really unavailable -> report NOT RUN.
            return ModelEvaluationReport(
                provider=provider_name, ran=False, reason_not_run=str(exc)
            )
        except Exception as exc:  # noqa: BLE001 - record, do not crash
            result.error = f"{type(exc).__name__}: {exc}"

        report.results.append(result)

    return report


# ----------------------------------------------------------------------
# Multi-provider comparison report
# ----------------------------------------------------------------------

def _fmt_metric(value: Optional[float], ran: bool) -> str:
    if not ran or value is None:
        return NOT_RUN
    return f"{value}%"


def format_provider_block(report: ModelEvaluationReport) -> str:
    lines: List[str] = []
    title = {
        "DETERMINISTIC": "Deterministic Baseline",
        "NOVA_BASE": "Base Nova",
        "NOVA_CUSTOM": "Customized Nova",
    }.get(report.provider, report.provider)

    lines.append(f"## {title}")
    lines.append("")
    if not report.ran:
        lines.append(f"Status: {NOT_RUN}")
        if report.reason_not_run:
            lines.append(f"Reason: {report.reason_not_run}")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"Scenarios: {report.total}")
    lines.append(f"Scored (valid responses): {report.scored}")
    lines.append(f"Invalid model responses: {report.invalid_responses}")
    lines.append(f"Full agreement: {report.full_agreements}")
    lines.append(f"Partial agreement: {report.partial_agreements}")
    lines.append(f"Disagreement: {report.disagreements}")
    lines.append(f"Tactical mode accuracy: {_fmt_metric(report.mode_accuracy, True)}")
    lines.append(f"Agent accuracy: {_fmt_metric(report.agent_accuracy, True)}")
    lines.append(f"Action accuracy: {_fmt_metric(report.action_accuracy, True)}")
    if report.average_latency_ms is not None:
        lines.append(f"Average latency: {report.average_latency_ms} ms")
    lines.append("")
    return "\n".join(lines)


def format_comparison_report(reports: List[ModelEvaluationReport]) -> str:
    """Build the multi-provider MODEL EVALUATION report."""

    lines: List[str] = ["# MODEL EVALUATION", ""]
    for report in reports:
        lines.append(format_provider_block(report))

    # Agreement vs the deterministic baseline (only for providers that ran).
    baseline = next(
        (r for r in reports if r.provider == ModelProvider.DETERMINISTIC.value),
        None,
    )
    lines.append("## Agreement vs Deterministic Baseline")
    lines.append("")
    for report in reports:
        if report.provider == ModelProvider.DETERMINISTIC.value:
            continue
        label = {
            "NOVA_BASE": "Deterministic vs Base Nova",
            "NOVA_CUSTOM": "Deterministic vs Customized Nova",
        }.get(report.provider, f"Deterministic vs {report.provider}")
        value = _fmt_metric(report.full_agreement_pct, report.ran)
        lines.append(f"{label}: {value}")
    lines.append("")

    lines.append(
        "> Model rows other than the deterministic baseline show real "
        "measured numbers only. Any provider that was not executed reports "
        f"'{NOT_RUN}'. No metrics are fabricated."
    )
    lines.append("")
    return "\n".join(lines)
