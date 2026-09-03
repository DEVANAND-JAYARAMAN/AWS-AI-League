"""
Streamlit dashboard for the Agentic Football Tactical AI (Steps 42, 47, 48).

A thin presentation layer on top of the existing backend. It runs the
existing pipeline once per click and then only *reads* the results:

    app.core.sample_scenario   -> scenario library (auto-discovered)
    app.ai.match_simulator     -> HybridMatchSimulator / SimulationMode
    app.agents.coordinator     -> per-agent decisions (pure, deterministic)
    app.analytics              -> build_event_log / analyze / format_*
    ui.pitch                   -> SVG pitch rendering (this package)

No tactical, simulation, or analytics logic is re-implemented here.
Navigating ticks never re-runs the simulation and never calls AWS.

Run with:

    streamlit run ui/app.py
"""

import inspect
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.agents.coordinator import AgentCoordinator  # noqa: E402
from app.ai.match_simulator import HybridMatchSimulator, SimulationMode  # noqa: E402
from app.analytics import (  # noqa: E402
    analyze,
    build_event_log,
    format_analytics,
    format_timeline,
)
from app.core import sample_scenario  # noqa: E402
from app.core.serialization import game_state_from_dict  # noqa: E402
from ui.pitch import build_pitch_svg  # noqa: E402

TEAM_ORDER = ["goalkeeper", "defender", "midfielder", "striker"]
DETERMINISTIC = SimulationMode.DETERMINISTIC_ONLY.value


# ----------------------------------------------------------------------
# Backend helpers - discovery + orchestration only, no new logic
# ----------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def discover_scenarios() -> dict:
    """Auto-discover scenario factories in app.core.sample_scenario."""

    scenarios = {}
    for name, fn in inspect.getmembers(sample_scenario, inspect.isfunction):
        if fn.__module__ != sample_scenario.__name__ or not name.startswith("create_"):
            continue
        label = (
            name.removeprefix("create_").removesuffix("_scenario")
            .replace("_", " ").title()
        )
        scenarios[label] = name
    return dict(sorted(scenarios.items()))


def run_simulation(scenario_fn_name: str, mode: SimulationMode, ticks: int):
    """Run the existing pipeline once and return (match, event_log, analytics)."""

    factory = getattr(sample_scenario, scenario_fn_name)
    sim = HybridMatchSimulator(factory(), mode=mode, max_ticks=ticks)
    match = sim.run()
    log = build_event_log(match)
    return match, log, analyze(log)


def snapshot_for_tick(events: list, tick: int) -> dict | None:
    """Serialized GameState for a tick. 0 = initial state, k = after tick k."""

    if not events:
        return None
    if tick <= 0:
        return events[0].state_before
    return events[min(tick, len(events)) - 1].state_after


def event_for_tick(events: list, tick: int):
    """The MatchEvent produced by ``tick`` (None for the initial state)."""

    if tick <= 0 or not events:
        return None
    return events[min(tick, len(events)) - 1]


def agent_status_rows(state_dict: dict) -> list:
    """Per-agent deterministic decisions for a snapshot (pure AgentCoordinator)."""

    if not state_dict:
        return []
    game_state = game_state_from_dict(state_dict)
    roles = {p.player_id: p.role for p in game_state.our_team}
    decisions = AgentCoordinator().get_team_decisions(game_state)

    rows = []
    for pid in TEAM_ORDER:
        decision = decisions.get(pid)
        if decision is None:
            continue
        rows.append(
            {
                "player": pid.capitalize(),
                "role": roles.get(pid, "?"),
                "action": decision.action.value,
                "confidence": float(decision.confidence),
                "reason": decision.reason,
            }
        )
    return rows


def _conf(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"


def _decision_lines(summary: dict | None) -> str:
    if not summary:
        return "_not available_"
    return (
        f"- Tactical mode: `{summary.get('tactical_mode', '-')}`\n"
        f"- Agent: `{summary.get('agent', '-')}`\n"
        f"- Action: `{summary.get('action', '-')}`\n"
        f"- Confidence: `{_conf(summary.get('confidence'))}`"
    )


# ----------------------------------------------------------------------
# Page setup + session state
# ----------------------------------------------------------------------

st.set_page_config(
    page_title="Agentic Football Tactical AI",
    page_icon="⚽",
    layout="wide",
)

_DEFAULTS = {
    "latest_match_result": None,
    "latest_events": None,
    "latest_analytics": None,
    "simulation_completed": False,
    "run_config": None,
    "run_error": None,
    "selected_tick": 0,
}
for key, default in _DEFAULTS.items():
    st.session_state.setdefault(key, default)


# ----------------------------------------------------------------------
# 1. Header / project identity
# ----------------------------------------------------------------------

st.title("⚽ Agentic Football Tactical AI")
st.write(
    "Agentic Football is a multi-agent tactical simulation where specialised "
    "football agents coordinate decisions using deterministic reasoning and "
    "Amazon Nova Pro through Amazon Bedrock."
)

with st.container(border=True):
    a, b, c, d, e = st.columns([2, 1, 1, 1, 1])
    a.markdown(
        "**Agents**  \nGoalkeeper · Defender  \nMidfielder · Striker"
    )
    b.markdown("→  \n**Team  \nCoordinator**")
    c.markdown("→  \n**Hybrid Decision  \nResolver**")
    d.markdown("→  \n**Simulation**")
    e.markdown("→  \n**Analytics**")


# ----------------------------------------------------------------------
# 2. Sidebar - simulation controls
# ----------------------------------------------------------------------

scenarios = discover_scenarios()

with st.sidebar:
    st.header("Simulation controls")

    if not scenarios:
        st.error("No scenarios found in app.core.sample_scenario.")
        st.stop()

    scenario_label = st.selectbox("Scenario", list(scenarios.keys()))
    mode_name = st.selectbox(
        "Simulation mode",
        [DETERMINISTIC, "HYBRID"],
        help="HYBRID calls Amazon Nova Pro on Bedrock (needs AWS credentials).",
    )
    ticks = st.slider("Ticks", min_value=1, max_value=10, value=5)

    if mode_name == "HYBRID":
        st.info(
            "HYBRID invokes Amazon Nova Pro per tick. The backend falls back "
            "to the deterministic decision automatically if AWS is unavailable."
        )

    run_clicked = st.button(
        "Run simulation", type="primary", use_container_width=True
    )

    st.divider()
    st.caption(
        "Tick navigation below the pitch only replays stored snapshots - it "
        "never re-runs the simulation or calls AWS."
    )

if run_clicked:
    mode = SimulationMode(mode_name)
    with st.spinner(f"Running {ticks}-tick simulation ({mode_name})..."):
        try:
            match, log, analytics = run_simulation(
                scenarios[scenario_label], mode, ticks
            )
            st.session_state.latest_match_result = match
            st.session_state.latest_events = log
            st.session_state.latest_analytics = analytics
            st.session_state.simulation_completed = True
            st.session_state.run_error = None
            st.session_state.selected_tick = 0
            st.session_state.run_config = {
                "scenario": scenario_label,
                "mode": mode_name,
                "ticks": ticks,
            }
        except Exception as exc:  # noqa: BLE001 - surface any backend/AWS failure
            st.session_state.run_error = f"{type(exc).__name__}: {exc}"
            st.session_state.simulation_completed = False


# ----------------------------------------------------------------------
# Guard: nothing to show yet
# ----------------------------------------------------------------------

if st.session_state.run_error:
    st.error(
        "Simulation failed.\n\n"
        f"{st.session_state.run_error}\n\n"
        "If you selected HYBRID mode, check your AWS credentials and Amazon "
        "Bedrock / Nova Pro access. DETERMINISTIC_ONLY mode runs fully offline."
    )

if not st.session_state.simulation_completed:
    st.info("Configure the simulation in the sidebar and click **Run simulation**.")
    st.stop()

match = st.session_state.latest_match_result
log = st.session_state.latest_events
analytics = st.session_state.latest_analytics
events = list(log.events)
config = st.session_state.run_config or {}
is_hybrid = match.simulation_mode != DETERMINISTIC
last_tick = match.tick_results[-1] if match.tick_results else None
final_summary = last_tick.final_decision if last_tick else {}


# ----------------------------------------------------------------------
# Mode banner
# ----------------------------------------------------------------------

if is_hybrid:
    st.success(
        f"**HYBRID mode** — Deterministic Engine  vs  Amazon Nova Pro  →  "
        f"Hybrid Decision Resolver   ·   Nova Pro calls: "
        f"**{match.statistics.get('nova_calls', 0)} / {match.total_ticks}**"
    )
else:
    st.info(
        "**DETERMINISTIC_ONLY mode** — the simulation engine executed the team "
        "coordinator decision every tick. Amazon Nova Pro was not called."
    )


# ----------------------------------------------------------------------
# 3. Match status
# ----------------------------------------------------------------------

st.subheader("Match status")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tactical mode", str(final_summary.get("tactical_mode", "-")).upper())
c2.metric("Primary agent", str(final_summary.get("agent", "-")).upper())
c3.metric("Primary action", str(final_summary.get("action", "-")).upper())
c4.metric("Final confidence", _conf(final_summary.get("confidence")))


# ----------------------------------------------------------------------
# 4. Football pitch visualization + 5. selected tick decision
# ----------------------------------------------------------------------

st.subheader("Football pitch")

n = match.total_ticks
if st.session_state.selected_tick > n:
    st.session_state.selected_tick = n
st.slider(
    "Tick  (0 = initial state)",
    min_value=0,
    max_value=n,
    key="selected_tick",
    help="Replays stored state snapshots. No simulation or AWS call happens here.",
)
tick = st.session_state.selected_tick
snapshot = snapshot_for_tick(events, tick)
event = event_for_tick(events, tick)

pitch_col, info_col = st.columns([3, 2])

with pitch_col:
    if snapshot:
        ball_movement = event.ball_movement if event else None
        components.html(
            build_pitch_svg(snapshot, ball_movement),
            height=540,
        )
        st.caption(
            "Blue = our agents (GK / DF / MF / ST) · Grey = opponents · "
            "White dot = ball · Dashed yellow arrow = ball movement this tick"
        )
    else:
        st.warning("No state snapshot available for this tick.")

with info_col:
    with st.container(border=True):
        if event is None:
            st.markdown(f"### Tick {tick} — initial state")
            poss = (snapshot or {}).get("possession", "-")
            st.markdown(f"Possession: `{poss}`")
            st.caption("No decision has been taken yet.")
        else:
            final = event.final_decision
            st.markdown(f"### Tick {event.tick}")
            st.markdown(f"**Mode:** `{event.tactical_mode or '-'}`")
            st.markdown(
                f"**Decision:**  \n`{final.get('agent', '-')}` → "
                f"`{final.get('action', '-')}`"
            )
            st.markdown(f"**Confidence:** `{_conf(final.get('confidence'))}`")
            st.markdown(f"**Source:** `{event.decision_source}`")
            st.markdown(f"**Agreement:** `{event.agreement or 'N/A'}`")
            if is_hybrid and not event.nova_called:
                st.warning(
                    f"Nova Pro skipped this tick: {event.nova_skip_reason or 'unknown'}"
                )
            if event.reason:
                st.caption(event.reason)


# ----------------------------------------------------------------------
# 6. Agent status (for the selected tick's snapshot)
# ----------------------------------------------------------------------

st.subheader("Agent status")
st.caption(
    f"Deterministic agent intentions for the tick {tick} snapshot "
    "(AgentCoordinator is a pure function - no simulation is run)."
)
rows = agent_status_rows(snapshot)
cols = st.columns(len(rows) or 1)
for col, row in zip(cols, rows):
    with col:
        with st.container(border=True):
            st.markdown(f"**{row['player']}**  \n`{row['role']}`")
            st.metric(row["action"], _conf(row["confidence"]))
            st.caption(row["reason"])


# ----------------------------------------------------------------------
# 7. Hybrid AI decision comparison
# ----------------------------------------------------------------------

st.subheader("Hybrid AI decision comparison")

if not is_hybrid:
    st.info(
        "Amazon Nova Pro was not called because this simulation was run in "
        "deterministic-only mode."
    )
else:
    cmp_event = event or (events[-1] if events else None)
    if cmp_event is None:
        st.warning("No tick data available.")
    else:
        st.caption(
            f"Showing tick {cmp_event.tick}. "
            "Deterministic Engine  vs  Amazon Nova Pro  →  Hybrid Decision Resolver."
        )
        h1, h2, h3 = st.columns(3)
        with h1:
            st.markdown("**Deterministic engine**")
            st.markdown(_decision_lines(cmp_event.deterministic_decision))
        with h2:
            st.markdown("**Amazon Nova Pro**")
            if cmp_event.nova_called and cmp_event.nova_recommendation:
                st.markdown(_decision_lines(cmp_event.nova_recommendation))
            else:
                st.markdown(
                    f"_skipped_ — {cmp_event.nova_skip_reason or 'not called this tick'}"
                )
        with h3:
            st.markdown("**Hybrid final decision**")
            st.markdown(_decision_lines(cmp_event.final_decision))

        f1, f2 = st.columns(2)
        f1.metric("Agreement", cmp_event.agreement or "N/A")
        f2.metric("Decision source", cmp_event.decision_source)
        if cmp_event.reason:
            st.caption(cmp_event.reason)

    with st.expander("Nova Pro usage across the whole match"):
        st.write(
            {
                "nova_calls": match.statistics.get("nova_calls", 0),
                "nova_skipped": match.statistics.get("nova_skipped", 0),
                "decision_sources": match.statistics.get("decision_sources", {}),
                "agreement_types": match.statistics.get("agreement_types", {}),
            }
        )


# ----------------------------------------------------------------------
# 8. Simulation timeline + 9. match analytics
# ----------------------------------------------------------------------

st.subheader("Timeline & analytics")
t1, t2 = st.tabs(["Simulation timeline", "Match analytics"])
with t1:
    st.code(format_timeline(log), language="text")
with t2:
    st.code(format_analytics(analytics), language="text")
