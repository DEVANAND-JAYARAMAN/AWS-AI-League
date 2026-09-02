"""
Hybrid match simulator (Step 36).

An orchestration layer that plays a full football match tick by tick,
choosing per tick between the deterministic team decision and an Amazon
Nova Pro recommendation (via the already-built hybrid resolver), and
having the **existing** simulation engine execute whatever final decision
was chosen.

    Game State
        -> deterministic Team Coordinator            (always, cheap)
        -> Amazon Nova Pro tactical analysis         (mode dependent)
        -> Hybrid Decision Resolver                  (HYBRID modes)
        -> final TeamDecision
        -> FootballSimulationEngine.step(decision)   (executes the final)
        -> updated Game State -> next tick

This module duplicates no agent logic and no movement logic - it only
wires existing components together.
"""

import copy
import logging
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from agents.coordinator import AgentCoordinator
from agents.hybrid_decision_resolver import HybridDecisionResolver
from hybrid.decision_comparator import compare
from llm.bedrock_client import BedrockInvocationError
from llm.llm_tactical_analyzer import LLMTacticalAnalyzer
from llm.response_parser import TacticalRecommendation, TacticalValidationError
from simulation.decision import FootballAction, FootballDecision
from simulation.engine import FootballSimulationEngine
from simulation.game_state import GameState
from simulation.team_coordinator import TeamDecision

logger = logging.getLogger(__name__)


class SimulationMode(str, Enum):
    """How each tick's final decision is produced."""

    DETERMINISTIC_ONLY = "DETERMINISTIC_ONLY"
    NOVA_ONLY = "NOVA_ONLY"
    HYBRID = "HYBRID"
    HYBRID_ON_KEY_DECISIONS = "HYBRID_ON_KEY_DECISIONS"


# Actions important enough to spend a Bedrock call on.
DEFAULT_KEY_ACTIONS = frozenset({"SHOOT", "PRESS", "PASS"})

_VALID_MODES = {"ATTACK", "DEFENSE", "TRANSITION"}
_VALID_ACTIONS = {action.value for action in FootballAction}


# ----------------------------------------------------------------------
# Result models
# ----------------------------------------------------------------------

@dataclass
class HybridTickResult:
    """One simulated tick."""

    tick_number: int
    simulation_mode: str

    # Lightweight view of the state transition (full states also kept below).
    ball_before: tuple
    ball_after: tuple
    possession_before: str
    possession_after: str

    deterministic_decision: Optional[dict]      # {tactical_mode, agent, action, confidence}
    nova_recommendation: Optional[dict]         # same shape, or None if skipped/failed

    final_decision: dict                        # same shape

    decision_source: str
    agreement_type: Optional[str]

    nova_called: bool
    nova_skip_reason: Optional[str]

    reason: str

    # Full transition for anyone who wants it (no extra copies - the engine
    # already deep-copied these).
    game_state_before: GameState = field(repr=False, default=None)
    game_state_after: GameState = field(repr=False, default=None)


@dataclass
class HybridMatchResult:
    """The whole match."""

    total_ticks: int
    simulation_mode: str
    tick_results: List[HybridTickResult]
    final_game_state: GameState = field(repr=False, default=None)
    statistics: dict = field(default_factory=dict)


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _xy(position) -> tuple:
    if position is None:
        return (None, None)
    return (round(position.x, 2), round(position.y, 2))


def _summary_from_team_decision(td: TeamDecision) -> dict:
    primary = td.agent_decisions.get(td.primary_agent)
    return {
        "tactical_mode": str(td.tactical_mode).upper(),
        "agent": str(td.primary_agent).lower(),
        "action": td.primary_action.value,
        "confidence": round(float(primary.confidence), 4) if primary else 0.0,
    }


def _summary_from_recommendation(rec: TacticalRecommendation) -> dict:
    return {
        "tactical_mode": str(rec.tactical_mode).upper(),
        "agent": str(rec.recommended_agent).lower(),
        "action": str(rec.recommended_action).upper(),
        "confidence": round(float(rec.confidence), 4),
    }


def _is_valid_choice(mode: str, agent: str, action: str, confidence: float,
                     game_state: GameState) -> bool:
    """Defensive re-validation before an external decision is executed."""

    if str(mode).upper() not in _VALID_MODES:
        return False
    if str(action).upper() not in _VALID_ACTIONS:
        return False
    our_ids = {p.player_id.lower() for p in game_state.our_team}
    if str(agent).lower() not in our_ids:
        return False
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        return False
    return 0.0 <= conf <= 1.0


def _synth_primary_decision(
    agent: str,
    action_value: str,
    confidence: float,
    reason: str,
    deterministic_td: TeamDecision,
    game_state: GameState,
) -> FootballDecision:
    """
    Build a FootballDecision for ``agent``/``action_value`` reusing target
    information from the deterministic decisions where possible.
    """

    action = FootballAction(str(action_value).upper())

    own = deterministic_td.agent_decisions.get(agent)
    if own is not None and own.action == action:
        return own  # exact match - already has correct targets

    borrowed = next(
        (d for d in deterministic_td.agent_decisions.values() if d.action == action),
        None,
    )
    target_player_id = borrowed.target_player_id if borrowed else None
    target_position = borrowed.target_position if borrowed else None

    if action == FootballAction.PASS and not target_player_id:
        target_player_id = next(
            (
                p.player_id
                for p in game_state.our_team
                if p.role == "STRIKER" and p.player_id != agent
            ),
            None,
        )

    if action in (FootballAction.MOVE, FootballAction.PRESS) and target_position is None:
        if own is not None and own.target_position is not None:
            target_position = own.target_position
        else:
            target_position = game_state.ball_position

    return FootballDecision(
        action=action,
        target_player_id=target_player_id,
        confidence=float(confidence),
        target_position=target_position,
        reason=reason,
    )


def _team_decision_from_choice(
    mode: str,
    agent: str,
    action_value: str,
    confidence: float,
    reason: str,
    deterministic_td: TeamDecision,
    game_state: GameState,
) -> TeamDecision:
    """Wrap a final (mode, agent, action) choice in a full TeamDecision."""

    primary = _synth_primary_decision(
        agent, action_value, confidence, reason, deterministic_td, game_state
    )

    agent_decisions = dict(deterministic_td.agent_decisions)
    agent_decisions[agent] = primary

    return TeamDecision(
        tactical_mode=str(mode).upper(),
        agent_decisions=agent_decisions,
        primary_action=primary.action,
        primary_agent=agent,
        reason=reason,
        conflicts=list(deterministic_td.conflicts),
    )


# ----------------------------------------------------------------------
# simulator
# ----------------------------------------------------------------------

class HybridMatchSimulator:
    """Plays a match, one tick at a time, in the chosen SimulationMode."""

    def __init__(
        self,
        initial_game_state: GameState,
        mode: SimulationMode = SimulationMode.HYBRID,
        *,
        max_ticks: int = 5,
        key_actions=None,
        coordinator: AgentCoordinator | None = None,
        llm_analyzer: LLMTacticalAnalyzer | None = None,
        resolver: HybridDecisionResolver | None = None,
    ):
        self.engine = FootballSimulationEngine(initial_game_state)
        self.mode = mode
        self.max_ticks = max_ticks
        self.key_actions = {
            str(a).upper() for a in (key_actions or DEFAULT_KEY_ACTIONS)
        }
        self.coordinator = coordinator or AgentCoordinator()
        self._llm_analyzer = llm_analyzer  # built lazily - never for DETERMINISTIC_ONLY
        self.resolver = resolver or HybridDecisionResolver()
        self.tick_results: List[HybridTickResult] = []

    # ------------------------------------------------------------------
    @property
    def llm_analyzer(self) -> LLMTacticalAnalyzer:
        if self._llm_analyzer is None:
            self._llm_analyzer = LLMTacticalAnalyzer()
        return self._llm_analyzer

    # ------------------------------------------------------------------
    def run(self) -> HybridMatchResult:
        for _ in range(self.max_ticks):
            self.tick_results.append(self._run_tick())

        return HybridMatchResult(
            total_ticks=len(self.tick_results),
            simulation_mode=self.mode.value,
            tick_results=self.tick_results,
            final_game_state=self.engine.game_state,
            statistics=self._statistics(),
        )

    # ------------------------------------------------------------------
    def _run_tick(self) -> HybridTickResult:
        tick_number = self.engine.tick_number + 1
        state_for_decision = self.engine.game_state

        # DETERMINISTIC_ONLY: let the engine do everything, no Nova.
        if self.mode is SimulationMode.DETERMINISTIC_ONLY:
            step = self.engine.step()
            summary = _summary_from_team_decision(step.team_decision)
            return self._make_tick_result(
                tick_number, step,
                deterministic=summary, nova=None, final=summary,
                decision_source="DETERMINISTIC_ONLY", agreement_type=None,
                nova_called=False, nova_skip_reason=None,
                reason="Deterministic-only mode: the simulation engine "
                       "executed the team coordinator decision.",
            )

        # Every other mode needs the deterministic decision first.
        deterministic_td = self.coordinator.get_coordinated_team_decision(
            state_for_decision
        )
        det_summary = _summary_from_team_decision(deterministic_td)
        det_action = deterministic_td.primary_action.value

        # Decide whether to spend a Bedrock call this tick.
        nova_skip_reason = None
        if (
            self.mode is SimulationMode.HYBRID_ON_KEY_DECISIONS
            and det_action not in self.key_actions
        ):
            nova_skip_reason = (
                f"deterministic primary action '{det_action}' is not a key "
                f"decision ({sorted(self.key_actions)})"
            )

        recommendation = None
        nova_called = False
        if nova_skip_reason is None:
            try:
                recommendation = self.llm_analyzer.analyze(state_for_decision)
                nova_called = True
            except (BedrockInvocationError, TacticalValidationError) as exc:
                nova_skip_reason = f"Nova call failed or returned invalid output: {exc}"
                logger.warning("Tick %d: %s", tick_number, nova_skip_reason)

        nova_summary = (
            _summary_from_recommendation(recommendation)
            if recommendation is not None
            else None
        )

        # Resolve the final decision for this tick.
        final_td, source, agreement, reason = self._resolve_final(
            deterministic_td, recommendation, nova_skip_reason, state_for_decision
        )

        step = self.engine.step(final_td)

        return self._make_tick_result(
            tick_number, step,
            deterministic=det_summary, nova=nova_summary,
            final=_summary_from_team_decision(final_td),
            decision_source=source, agreement_type=agreement,
            nova_called=nova_called, nova_skip_reason=nova_skip_reason,
            reason=reason,
        )

    # ------------------------------------------------------------------
    def _resolve_final(
        self,
        deterministic_td: TeamDecision,
        recommendation: Optional[TacticalRecommendation],
        nova_skip_reason: Optional[str],
        game_state: GameState,
    ):
        """Return ``(final_team_decision, decision_source, agreement_type, reason)``."""

        det_summary = _summary_from_team_decision(deterministic_td)

        # --- NOVA_ONLY ------------------------------------------------
        if self.mode is SimulationMode.NOVA_ONLY:
            if recommendation is not None and _is_valid_choice(
                recommendation.tactical_mode,
                recommendation.recommended_agent,
                recommendation.recommended_action,
                recommendation.confidence,
                game_state,
            ):
                final_td = _team_decision_from_choice(
                    recommendation.tactical_mode,
                    recommendation.recommended_agent,
                    recommendation.recommended_action,
                    recommendation.confidence,
                    f"Nova-only mode: {recommendation.reason}",
                    deterministic_td,
                    game_state,
                )
                return final_td, "NOVA_ONLY", None, final_td.reason

            return (
                deterministic_td,
                "DETERMINISTIC_FALLBACK",
                None,
                "Nova-only mode, but the Nova recommendation was unavailable "
                f"or invalid ({nova_skip_reason or 'no recommendation'}); "
                "fell back to the deterministic decision.",
            )

        # --- HYBRID / HYBRID_ON_KEY_DECISIONS -----------------------
        if recommendation is None:
            # Skipped because not a key decision -> deterministic, no Nova.
            if nova_skip_reason and "not a key decision" in nova_skip_reason:
                return (
                    deterministic_td,
                    "DETERMINISTIC_ONLY",
                    None,
                    f"Nova skipped ({nova_skip_reason}); executed the "
                    f"deterministic decision "
                    f"{det_summary['tactical_mode']}/{det_summary['agent']}/"
                    f"{det_summary['action']}.",
                )
            # Nova failed / invalid -> safety fallback.
            return (
                deterministic_td,
                "DETERMINISTIC_FALLBACK",
                None,
                f"Nova output could not be used ({nova_skip_reason}); "
                "fell back to the deterministic decision for safety.",
            )

        comparison = compare(deterministic_td, recommendation)
        hybrid = self.resolver.resolve(deterministic_td, recommendation, comparison)

        if not _is_valid_choice(
            hybrid.final_tactical_mode, hybrid.final_agent,
            hybrid.final_action, hybrid.final_confidence, game_state,
        ):
            return (
                deterministic_td,
                "DETERMINISTIC_FALLBACK",
                comparison.overall_agreement.value,
                "Resolved hybrid decision failed defensive validation; "
                "fell back to the deterministic decision.",
            )

        final_td = _team_decision_from_choice(
            hybrid.final_tactical_mode,
            hybrid.final_agent,
            hybrid.final_action,
            hybrid.final_confidence,
            hybrid.reason,
            deterministic_td,
            game_state,
        )
        return (
            final_td,
            hybrid.decision_source.value,
            hybrid.agreement_type.value,
            hybrid.reason,
        )

    # ------------------------------------------------------------------
    def _make_tick_result(
        self, tick_number, step, *, deterministic, nova, final,
        decision_source, agreement_type, nova_called, nova_skip_reason, reason,
    ) -> HybridTickResult:
        return HybridTickResult(
            tick_number=tick_number,
            simulation_mode=self.mode.value,
            ball_before=_xy(step.state_before.ball_position),
            ball_after=_xy(step.state_after.ball_position),
            possession_before=step.state_before.possession,
            possession_after=step.state_after.possession,
            deterministic_decision=deterministic,
            nova_recommendation=nova,
            final_decision=final,
            decision_source=decision_source,
            agreement_type=agreement_type,
            nova_called=nova_called,
            nova_skip_reason=nova_skip_reason,
            reason=reason,
            game_state_before=step.state_before,
            game_state_after=step.state_after,
        )

    # ------------------------------------------------------------------
    def _statistics(self) -> dict:
        ticks = self.tick_results

        decision_sources = Counter(t.decision_source for t in ticks)
        agreement_types = Counter(
            t.agreement_type for t in ticks if t.agreement_type is not None
        )
        primary_actions = Counter(t.final_decision["action"] for t in ticks)
        final_modes = Counter(t.final_decision["tactical_mode"] for t in ticks)

        return {
            "nova_calls": sum(1 for t in ticks if t.nova_called),
            "nova_skipped": sum(1 for t in ticks if not t.nova_called),
            "decision_sources": dict(decision_sources),
            "agreement_types": dict(agreement_types),
            "primary_actions": dict(primary_actions),
            "final_tactical_modes": dict(final_modes),
        }


# ----------------------------------------------------------------------
# formatting helpers (used by the test / any CLI)
# ----------------------------------------------------------------------

_DASH = "-" * 55


def _fmt_decision(summary: Optional[dict]) -> str:
    if summary is None:
        return "(none)"
    return (
        f"{summary['tactical_mode']} / {summary['agent']} / {summary['action']}"
    )


def format_tick(tick: HybridTickResult) -> str:
    lines = [
        _DASH,
        f"TICK {tick.tick_number}",
        _DASH,
        "",
        "Deterministic Decision:",
        _fmt_decision(tick.deterministic_decision),
    ]
    if tick.deterministic_decision:
        lines.append(f"Confidence: {tick.deterministic_decision['confidence']:.2f}")

    lines += ["", "Amazon Nova Pro:"]
    if tick.nova_called and tick.nova_recommendation:
        lines.append(_fmt_decision(tick.nova_recommendation))
        lines.append(f"Confidence: {tick.nova_recommendation['confidence']:.2f}")
    else:
        lines.append(f"(skipped) {tick.nova_skip_reason or ''}".rstrip())

    lines += [
        "",
        "Hybrid Final Decision:",
        _fmt_decision(tick.final_decision),
        f"Confidence: {tick.final_decision['confidence']:.2f}",
        "",
        f"Decision Source:\n{tick.decision_source}",
        "",
        f"Agreement:\n{tick.agreement_type or '(n/a)'}",
        "",
        "Ball:",
        f"Before: {tick.ball_before}",
        f"After:  {tick.ball_after}",
    ]
    return "\n".join(lines)


def format_statistics(match: HybridMatchResult) -> str:
    stats = match.statistics
    line = "=" * 55

    def _block(title, counter: dict, keys):
        rows = [title]
        shown = set()
        for key in keys:
            rows.append(f"{key}: {counter.get(key, 0)}")
            shown.add(key)
        for key, value in counter.items():
            if key not in shown:
                rows.append(f"{key}: {value}")
        return "\n".join(rows)

    return "\n".join([
        line,
        "📊 HYBRID MATCH STATISTICS",
        line,
        "",
        f"Total Ticks: {match.total_ticks}",
        "",
        f"Simulation Mode: {match.simulation_mode}",
        "",
        f"Nova Calls: {stats['nova_calls']}",
        f"Nova Skipped: {stats['nova_skipped']}",
        "",
        _block("Decision Sources:", stats["decision_sources"], [
            "AGREEMENT", "HYBRID_RESOLUTION",
            "DETERMINISTIC_FALLBACK", "DETERMINISTIC_ONLY",
        ]),
        "",
        _block("Agreement Types:", stats["agreement_types"], [
            "FULL_AGREEMENT", "PARTIAL_AGREEMENT", "DISAGREEMENT",
        ]),
        "",
        _block("Primary Actions:", stats["primary_actions"], [
            "PASS", "SHOOT", "MOVE", "PRESS", "HOLD_POSITION",
        ]),
        "",
        _block("Final Tactical Modes:", stats["final_tactical_modes"], [
            "ATTACK", "DEFENSE", "TRANSITION",
        ]),
        line,
    ])
