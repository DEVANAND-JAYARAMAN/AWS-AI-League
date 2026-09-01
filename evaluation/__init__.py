"""
Evaluation benchmark for the Agentic Football system.

    Scenario Library -> initial GameState -> expected behaviour
        -> existing AgentCoordinator / TeamCoordinator pipeline
        -> actual decision -> ScenarioResult -> BenchmarkReport

Fully local and deterministic: no AWS, no Bedrock, no API keys, no
network calls, no randomness, no LLM calls.
"""

from evaluation.benchmark_runner import (
    BenchmarkReport,
    ScenarioResult,
    format_report,
    run_benchmark,
)

__all__ = [
    "BenchmarkReport",
    "ScenarioResult",
    "format_report",
    "run_benchmark",
]
