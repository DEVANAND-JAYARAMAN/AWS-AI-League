"""
Match analytics (Steps 38-40): event logging, timeline, final report.

Deterministic and offline - the match is run with
SimulationMode.DETERMINISTIC_ONLY, so no AWS / Bedrock access is needed.

    python -m tests.test_analytics
"""

import json
import sys

from app.ai.match_simulator import (
    HybridMatchSimulator,
    HybridTickResult,
    SimulationMode,
)
from app.analytics import (
    build_event_log,
    build_events,
    format_analytics,
    format_timeline,
)
from app.analytics.event_logger import MatchEvent
from app.analytics.match_analytics import analyze
from app.core.sample_scenario import create_midfielder_pass_scenario

TICKS = 6


def _run_match():
    sim = HybridMatchSimulator(
        create_midfielder_pass_scenario(),
        mode=SimulationMode.DETERMINISTIC_ONLY,
        max_ticks=TICKS,
    )
    return sim.run()


def test_events_are_structured_per_tick():
    events = build_events(_run_match())

    assert len(events) == TICKS
    for i, event in enumerate(events, start=1):
        assert isinstance(event, MatchEvent)
        assert event.tick == i
        assert event.state_before is not None
        assert event.state_after is not None
        assert event.final_decision["action"] in {
            "PASS", "SHOOT", "PRESS", "MOVE", "HOLD_POSITION"
        }
        assert set(event.ball_movement) == {"before", "after", "distance"}
        assert event.ball_movement["distance"] >= 0.0
        # deterministic-only: no Nova, no agreement
        assert event.nova_recommendation is None
        assert event.agreement is None
        assert event.decision_source == "DETERMINISTIC_ONLY"


def test_event_log_json_round_trips():
    log = build_event_log(_run_match())

    data = json.loads(log.to_json())
    assert data["total_ticks"] == TICKS
    assert data["simulation_mode"] == "DETERMINISTIC_ONLY"
    assert len(data["events"]) == TICKS
    assert data["events"][0]["ball_movement"]["before"] is not None


def test_timeline_is_replayable():
    events = build_events(_run_match())
    text = format_timeline(events)
    print("\n" + text)

    assert text.startswith("MATCH START")
    assert text.rstrip().endswith("MATCH END")
    for i in range(1, TICKS + 1):
        assert f"Tick {i}\n" in text + "\n"
    assert text.count("Ball: ") == TICKS


def test_analytics_report_totals_are_consistent():
    events = build_events(_run_match())
    a = analyze(events)
    report = format_analytics(a)
    print("\n" + report)

    assert a.total_ticks == TICKS
    assert sum(a.action_counts.values()) == TICKS
    assert sum(a.mode_counts.values()) == TICKS
    assert a.nova_calls + a.nova_skipped == TICKS
    assert a.nova_calls == 0
    assert sum(a.agreement_counts.values()) == TICKS
    assert a.agreement_counts["n/a"] == TICKS
    assert sum(a.decision_source_counts.values()) == TICKS
    assert a.ball_distance >= 0.0
    assert round(sum(a.player_distance.values()), 2) == a.team_distance

    assert "MATCH ANALYTICS" in report
    assert "Ball Distance:" in report and "Team Distance:" in report


def test_analytics_is_deterministic():
    events = build_events(_run_match())
    assert analyze(events) == analyze(events)


def test_hybrid_fields_are_carried_through():
    """A synthetic hybrid tick exercises the Nova / agreement code paths."""

    det = {"tactical_mode": "ATTACK", "agent": "midfielder",
           "action": "PASS", "confidence": 0.85}
    nova = {"tactical_mode": "ATTACK", "agent": "striker",
            "action": "SHOOT", "confidence": 0.9}
    tick = HybridTickResult(
        tick_number=1,
        simulation_mode="HYBRID",
        ball_before=(60, 40),
        ball_after=(82, 50),
        possession_before="OUR_TEAM",
        possession_after="OUR_TEAM",
        deterministic_decision=det,
        nova_recommendation=nova,
        final_decision=nova,
        decision_source="HYBRID_RESOLUTION",
        agreement_type="PARTIAL_AGREEMENT",
        nova_called=True,
        nova_skip_reason=None,
        reason="priority: SHOOT > PASS",
        game_state_before=None,
        game_state_after=None,
    )

    (event,) = build_events([tick])
    assert event.deterministic_decision == det
    assert event.nova_recommendation == nova
    assert event.agreement == "PARTIAL_AGREEMENT"
    assert event.decision_source == "HYBRID_RESOLUTION"
    assert event.ball_movement["distance"] == 24.17

    a = analyze([event])
    assert a.nova_calls == 1
    assert a.agreement_counts["Partial"] == 1
    assert a.action_counts == {"SHOOT": 1}


def main():
    failures = []
    cases = [
        test_events_are_structured_per_tick,
        test_event_log_json_round_trips,
        test_timeline_is_replayable,
        test_analytics_report_totals_are_consistent,
        test_analytics_is_deterministic,
        test_hybrid_fields_are_carried_through,
    ]
    for case in cases:
        print("\n" + "#" * 72)
        print("# " + case.__name__)
        print("#" * 72)
        try:
            case()
        except BaseException as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            failures.append((case.__name__, exc))

    print("\n" + "=" * 72)
    if failures:
        print(f"{len(failures)} case(s) FAILED: {[n for n, _ in failures]}")
        sys.exit(1)
    print(f"All {len(cases)} case(s) passed.")


if __name__ == "__main__":
    main()
