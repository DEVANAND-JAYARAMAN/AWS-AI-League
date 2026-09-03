"""
Run a hybrid match and print the Step 38-40 analytics.

Usage:
    python -m scripts.run_hybrid_match [scenario] [ticks] [mode]

    scenario  factory name in app.core.sample_scenario
              (default: create_midfielder_pass_scenario)
    ticks     number of ticks (default: 8)
    mode      DETERMINISTIC_ONLY | HYBRID | NOVA_ONLY | HYBRID_ON_KEY_DECISIONS
              (default: DETERMINISTIC_ONLY - no AWS needed)

HYBRID / NOVA_ONLY / HYBRID_ON_KEY_DECISIONS make real Amazon Bedrock
calls and need AWS credentials + Nova Pro access.
"""

import sys
from datetime import datetime, timezone

from app.ai.match_simulator import HybridMatchSimulator, SimulationMode
from app.analytics import build_event_log, format_analytics, format_timeline
from app.config.settings import MATCH_RESULTS_DIR
from app.core import sample_scenario


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    scenario_name = argv[0] if argv else "create_midfielder_pass_scenario"
    ticks = int(argv[1]) if len(argv) > 1 else 8
    mode = SimulationMode(argv[2]) if len(argv) > 2 else SimulationMode.DETERMINISTIC_ONLY

    factory = getattr(sample_scenario, scenario_name)
    sim = HybridMatchSimulator(factory(), mode=mode, max_ticks=ticks)
    match = sim.run()

    log = build_event_log(match)

    print(format_timeline(log))
    print("\n" + "=" * 55 + "\n")
    print(format_analytics(log))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = MATCH_RESULTS_DIR / f"{scenario_name}_{mode.value}_{stamp}.json"
    out.write_text(log.to_json(), encoding="utf-8")
    print(f"\nEvent log saved: {out}")


if __name__ == "__main__":
    main()
