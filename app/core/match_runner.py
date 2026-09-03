"""
Convenience wiring:

    load scenario -> build engine -> run N ticks -> evaluate -> report

Adds no new simulation behaviour; it only composes the existing engine
and evaluator.
"""

from dataclasses import dataclass
from typing import Callable, List

from app.core.simulation import FootballSimulationEngine
from app.core.evaluator import (
    MatchEvaluationResult,
    MatchEvaluator,
    format_report,
)
from app.core.game_state import GameState


@dataclass
class MatchRun:
    """Everything produced by a single evaluated match run."""

    history: List
    result: MatchEvaluationResult


def run_match(
    scenario_function: Callable[[], GameState],
    ticks: int = 10,
) -> MatchRun:
    """Run a scenario for ``ticks`` ticks and evaluate the history."""

    engine = FootballSimulationEngine(
        initial_game_state=scenario_function()
    )

    history = engine.run(ticks=ticks)

    result = MatchEvaluator().evaluate(history)

    return MatchRun(history=history, result=result)


def print_match_report(match_run: MatchRun) -> None:
    print(format_report(match_run.result))
