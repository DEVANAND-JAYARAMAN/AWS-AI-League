"""
Run a single deterministic match simulation and print the evaluation report.

Usage:
    python -m scripts.run_match [scenario] [ticks]

``scenario`` is the name of a factory in app.core.sample_scenario
(default: create_attacking_scenario). ``ticks`` defaults to 10.
"""

import json
import sys
from datetime import datetime, timezone

from app.config.settings import MATCH_RESULTS_DIR
from app.core import sample_scenario
from app.core.evaluator import format_report
from app.core.match_runner import run_match


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    scenario_name = argv[0] if argv else "create_attacking_scenario"
    ticks = int(argv[1]) if len(argv) > 1 else 10

    factory = getattr(sample_scenario, scenario_name)
    match = run_match(factory, ticks=ticks)

    print(format_report(match.result))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = MATCH_RESULTS_DIR / f"{scenario_name}_{stamp}.json"
    result = match.result
    out.write_text(
        json.dumps(
            {
                "scenario": scenario_name,
                "ticks": ticks,
                "mode_counts": result.mode_counts,
                "action_counts": result.action_counts,
                "primary_agent_counts": result.primary_agent_counts,
                "total_ball_distance": result.total_ball_distance,
                "player_movement": result.player_movement,
                "changed_ticks": result.changed_ticks,
                "static_ticks": result.static_ticks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
