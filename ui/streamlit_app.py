"""
Streamlit dashboard for the Agentic Football Tactical AI (Steps 42, 47, 48, 51).

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
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

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

ROLE_EMOJI = {
    "GOALKEEPER": "🧤",
    "DEFENDER": "🛡️",
    "MIDFIELDER": "🎯",
    "STRIKER": "⚡",
}
MODE_EMOJI = {"ATTACK": "🔴", "DEFENSE": "🔵", "TRANSITION": "🟡"}

ARCH_DOT = """
digraph Architecture {
  rankdir=LR;
  bgcolor="transparent";
  node [shape=box, style="rounded,filled", fontname="Helvetica",
        fontsize=11, color="#8aa0c8", fillcolor="#e8eef9"];
  edge [color="#8a8a8a", fontname="Helvetica", fontsize=9];

  subgraph cluster_agents {
    label="Specialised agents (deterministic)";
    style="rounded"; color="#c8d3e6"; fontname="Helvetica"; fontsize=10;
    GK [label="Goalkeeper"]; DF [label="Defender"];
    MF [label="Midfielder"]; ST [label="Striker"];
  }

  COORD [label="AgentCoordinator\\n+ TeamCoordinator\\n(mode-aware scoring)"];
  NOVA  [label="Amazon Nova Pro\\nvia Amazon Bedrock", fillcolor="#fde8cf",
         color="#e0a060"];
  RESOLVER [label="Hybrid Decision Resolver\\nAGREEMENT / HYBRID_RESOLUTION /\\nDETERMINISTIC_FALLBACK",
            fillcolor="#e4f1e4", color="#8ac08a"];
  SIM   [label="FootballSimulationEngine\\nstep(final decision) -> next tick"];
  ANALYTICS [label="Analytics\\nevent log · timeline · report"];
  UI [label="Streamlit dashboard\\n(this app)", fillcolor="#f1e4f1",
      color="#c08ac0"];

  GK -> COORD; DF -> COORD; MF -> COORD; ST -> COORD;
  COORD -> RESOLVER [label="deterministic decision"];
  NOVA  -> RESOLVER [label="recommendation\\n(HYBRID mode only)", style=dashed];
  RESOLVER -> SIM [label="one final TeamDecision"];
  SIM -> ANALYTICS -> UI;
  COORD -> SIM [label="DETERMINISTIC_ONLY\\n(resolver + Nova skipped)",
                style=dotted, constraint=false];
}
"""


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
        scenarios[label] = {"fn": name, "doc": (fn.__doc__ or "").strip()}
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


def _fmt_target(decision) -> str:
    if decision.target_player_id:
        return f"→ {decision.target_player_id}"
    pos = decision.target_position
    if pos is not None:
        return f"({pos.x:.0f}, {pos.y:.0f})"
    return "—"


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
        role = roles.get(pid, "?")
        rows.append(
            {
                "player": pid.capitalize(),
                "role": role,
                "emoji": ROLE_EMOJI.get(str(role).upper(), "•"),
                "action": decision.action.value,
                "confidence": float(decision.confidence),
                "target": _fmt_target(decision),
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


def _bar(counts: dict, value_label: str):
    if not counts:
        st.caption("No data.")
        return
    df = pd.DataFrame({value_label: list(counts.values())}, index=list(counts.keys()))
    st.bar_chart(df, height=240)


def _ball_xy(state: dict | None):
    pos = (state or {}).get("ball_position") or {}
    return pos.get("x"), pos.get("y")


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
# Header / project identity
# ----------------------------------------------------------------------

st.title("⚽ Agentic Football Tactical AI")
st.markdown(
    "**Not just a football simulator — a multi-agent AI system where four "
    "deterministic role agents and Amazon Nova Pro collaborate, through a "
    "Hybrid Decision Resolver, to make tactical decisions every tick.**"
)

with st.container(border=True):
    cols = st.columns([2.4, 0.4, 1.4, 0.4, 1.6, 0.4, 1.2, 0.4, 1.2])
    cols[0].markdown(
        "🧤 Goalkeeper · 🛡️ Defender  \n🎯 Midfielder · ⚡ Striker  \n"
        "_four specialised agents_"
    )
    cols[1].markdown("### →")
    cols[2].markdown("**Team Coordinator**  \n_mode-aware scoring_")
    cols[3].markdown("### →")
    cols[4].markdown("**Hybrid Decision Resolver**  \n_deterministic + Nova Pro_")
    cols[5].markdown("### →")
    cols[6].markdown("**Simulation**  \n_tick-by-tick_")
    cols[7].markdown("### →")
    cols[8].markdown("**Analytics**  \n_timeline + report_")

with st.expander("System architecture"):
    st.graphviz_chart(ARCH_DOT)
    st.caption(
        "Solid = every run · dashed = Amazon Nova Pro, HYBRID mode only · "
        "dotted = DETERMINISTIC_ONLY shortcut. The deterministic path is always "
        "the fallback: an invalid or failed Nova response never blocks a tick."
    )


# ----------------------------------------------------------------------
# Sidebar - 1. match setup
# ----------------------------------------------------------------------

scenarios = discover_scenarios()

with st.sidebar:
    st.header("1 · Match setup")

    if not scenarios:
        st.error("No scenarios found in app.core.sample_scenario.")
        st.stop()

    scenario_label = st.selectbox("Scenario", list(scenarios.keys()))
    doc = scenarios[scenario_label]["doc"]
    if doc:
        st.caption(doc)

    mode_name = st.radio(
        "Simulation mode",
        [DETERMINISTIC, "HYBRID"],
        horizontal=True,
        help="HYBRID calls Amazon Nova Pro on Bedrock (needs AWS credentials).",
    )
    ticks = st.slider("Number of ticks", min_value=1, max_value=10, value=5)

    if mode_name == "HYBRID":
        st.info(
            "HYBRID invokes Amazon Nova Pro once per tick. The backend falls "
            "back to the deterministic decision automatically if a call fails."
        )
    else:
        st.caption("Deterministic mode runs fully offline — no AWS, no network.")

    run_clicked = st.button(
        "▶ Run simulation", type="primary", use_container_width=True
    )

    st.divider()
    st.caption(
        "Tick navigation on the pitch only replays stored snapshots — it never "
        "re-runs the simulation and never calls AWS."
    )

if run_clicked:
    mode = SimulationMode(mode_name)
    with st.spinner(f"Running {ticks}-tick simulation ({mode_name})..."):
        try:
            match, log, analytics = run_simulation(
                scenarios[scenario_label]["fn"], mode, ticks
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
    st.info("Configure the match in the sidebar and click **Run simulation**.")
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
        "**HYBRID mode** — Deterministic Engine  vs  Amazon Nova Pro  →  "
        "Hybrid Decision Resolver   ·   Nova Pro calls: "
        f"**{match.statistics.get('nova_calls', 0)} / {match.total_ticks}**"
    )
else:
    st.info(
        "**DETERMINISTIC_ONLY mode** — the simulation engine executed the team "
        "coordinator decision every tick. Amazon Nova Pro was not called."
    )


# ----------------------------------------------------------------------
# 2. Match status
# ----------------------------------------------------------------------

st.subheader("Match status")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tactical mode", str(final_summary.get("tactical_mode", "-")).upper())
c2.metric("Primary agent", str(final_summary.get("agent", "-")).upper())
c3.metric("Primary action", str(final_summary.get("action", "-")).upper())
c4.metric("Final confidence", _conf(final_summary.get("confidence")))


# ----------------------------------------------------------------------
# 3. Live match visualization  (pitch + tick navigation)
# ----------------------------------------------------------------------

st.subheader("Live match visualization")

n = match.total_ticks
if st.session_state.selected_tick > n:
    st.session_state.selected_tick = n

nav_prev, nav_slider, nav_next = st.columns([1, 8, 1])
if nav_prev.button("◀", use_container_width=True, help="Previous tick"):
    st.session_state.selected_tick = max(0, st.session_state.selected_tick - 1)
if nav_next.button("▶", use_container_width=True, help="Next tick"):
    st.session_state.selected_tick = min(n, st.session_state.selected_tick + 1)
with nav_slider:
    st.slider(
        "Tick  (0 = initial state)",
        min_value=0,
        max_value=n,
        key="selected_tick",
        help="Replays stored state snapshots. No simulation or AWS call here.",
    )

tick = st.session_state.selected_tick
snapshot = snapshot_for_tick(events, tick)
event = event_for_tick(events, tick)

cur_mode = (event.tactical_mode if event else None) or "—"
bx, by = _ball_xy(snapshot)
poss = (snapshot or {}).get("possession", "—")

badge1, badge2, badge3, badge4 = st.columns(4)
badge1.metric("Tick", f"{tick} / {n}")
badge2.metric("Tactical mode", f"{MODE_EMOJI.get(cur_mode, '')} {cur_mode}".strip())
badge3.metric("Possession", poss)
badge4.metric(
    "Ball position",
    f"({bx:.0f}, {by:.0f})" if bx is not None else "—",
)

pitch_col, info_col = st.columns([3, 2])

with pitch_col:
    if snapshot:
        ball_movement = event.ball_movement if event else None
        st.html(build_pitch_svg(snapshot, ball_movement))
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
            st.markdown(f"Possession: `{poss}`")
            st.caption("No decision has been taken yet. Use ▶ to step forward.")
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
# 4. Agent decision panel  (selected tick snapshot)
# ----------------------------------------------------------------------

st.subheader("Agent decision panel")
st.caption(
    f"What each specialised agent wants to do in the tick {tick} snapshot. "
    "AgentCoordinator is a pure function — no simulation is run here."
)
rows = agent_status_rows(snapshot)
cols = st.columns(len(rows) or 1)
for col, row in zip(cols, rows):
    with col:
        with st.container(border=True):
            st.markdown(f"### {row['emoji']} {row['player']}")
            st.caption(f"`{row['role']}`")
            st.metric(row["action"], _conf(row["confidence"]))
            st.markdown(f"**Target:** `{row['target']}`")
            st.caption(row["reason"])


# ----------------------------------------------------------------------
# 5. AI decision comparison
# ----------------------------------------------------------------------

st.subheader("AI decision comparison")

if not is_hybrid:
    st.info(
        "Deterministic-only run — Amazon Nova Pro was not called, so there is "
        "nothing to compare. Switch the sidebar mode to **HYBRID** and re-run "
        "to see Deterministic vs Nova Pro vs Hybrid decisions per tick."
    )
else:
    cmp_event = event or (events[-1] if events else None)
    if cmp_event is None:
        st.warning("No tick data available.")
    else:
        st.caption(
            f"Tick {cmp_event.tick} — Deterministic Engine  vs  Amazon Nova Pro  "
            "→  Hybrid Decision Resolver."
        )
        h1, h2, h3 = st.columns(3)
        with h1:
            with st.container(border=True):
                st.markdown("**⚙️ Deterministic engine**")
                st.markdown(_decision_lines(cmp_event.deterministic_decision))
        with h2:
            with st.container(border=True):
                st.markdown("**🤖 Amazon Nova Pro**")
                if cmp_event.nova_called and cmp_event.nova_recommendation:
                    st.markdown(_decision_lines(cmp_event.nova_recommendation))
                else:
                    st.markdown(
                        f"_skipped_ — {cmp_event.nova_skip_reason or 'not called'}"
                    )
        with h3:
            with st.container(border=True):
                st.markdown("**✅ Hybrid final decision**")
                st.markdown(_decision_lines(cmp_event.final_decision))

        f1, f2 = st.columns(2)
        f1.metric("Agreement", cmp_event.agreement or "N/A")
        f2.metric("Decision source", cmp_event.decision_source)
        if cmp_event.reason:
            st.caption(cmp_event.reason)

    stats = match.statistics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Nova Pro calls", stats.get("nova_calls", 0))
    m2.metric("Nova Pro skipped", stats.get("nova_skipped", 0))
    m3.metric("Full agreement", stats.get("agreement_types", {}).get("FULL_AGREEMENT", 0))
    m4.metric(
        "Hybrid resolutions",
        stats.get("decision_sources", {}).get("HYBRID_RESOLUTION", 0),
    )


# ----------------------------------------------------------------------
# 6. Analytics dashboard
# ----------------------------------------------------------------------

st.subheader("Analytics dashboard")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ticks", analytics.total_ticks)
k2.metric("Ball distance", f"{analytics.ball_distance:.1f}")
k3.metric("Team distance", f"{analytics.team_distance:.1f}")
k4.metric("Nova Pro calls", analytics.nova_calls)

d1, d2, d3 = st.columns(3)
with d1:
    st.markdown("**Tactical modes**")
    _bar(analytics.mode_counts, "ticks")
with d2:
    st.markdown("**Actions**")
    _bar(analytics.action_counts, "ticks")
with d3:
    st.markdown("**Primary agent**")
    agent_dist = Counter(
        t.final_decision.get("agent", "?") for t in match.tick_results
    )
    _bar(dict(agent_dist), "ticks")

st.markdown("**Player movement (total distance)**")
_bar(analytics.player_distance, "distance")

st.markdown("**State evolution — ball position per tick**")
xs, ys = [], []
for t in range(0, n + 1):
    x, y = _ball_xy(snapshot_for_tick(events, t))
    xs.append(x)
    ys.append(y)
st.line_chart(
    pd.DataFrame({"ball x": xs, "ball y": ys}, index=list(range(0, n + 1))),
    height=260,
)

with st.expander("Raw timeline & analytics report"):
    t1, t2 = st.tabs(["Simulation timeline", "Match analytics report"])
    with t1:
        st.code(format_timeline(log), language="text")
    with t2:
        st.code(format_analytics(analytics), language="text")
