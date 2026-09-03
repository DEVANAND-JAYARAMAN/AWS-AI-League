"""
Deterministic match evaluation and metrics.

The :class:`MatchEvaluator` is **read-only**: it consumes a list of
``SimulationStepResult`` objects produced by
:class:`~app.core.simulation.FootballSimulationEngine` and reports what
happened. It never touches decision-making and never mutates a GameState.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List

from app.core.game_state import GameState


# Positions closer than this are treated as "not moved" (float noise).
MOVEMENT_EPSILON = 1e-6

TACTICAL_MODES = ["ATTACK", "DEFENSE", "TRANSITION"]

PRIMARY_ACTIONS = [
    "PASS",
    "SHOOT",
    "PRESS",
    "MOVE",
    "HOLD_POSITION",
]

KNOWN_AGENTS = ["goalkeeper", "defender", "midfielder", "striker"]


@dataclass
class MatchEvaluationResult:
    """Structured, typed summary of a multi-tick simulation."""

    total_ticks: int
    mode_counts: Dict[str, int]
    action_counts: Dict[str, int]
    primary_agent_counts: Dict[str, int]
    total_ball_distance: float
    player_movement: Dict[str, float]
    changed_ticks: int
    static_ticks: int

    # Convenience accessors used by tests / reports.
    @property
    def attack_ticks(self) -> int:
        return self.mode_counts.get("ATTACK", 0)

    @property
    def defense_ticks(self) -> int:
        return self.mode_counts.get("DEFENSE", 0)

    @property
    def transition_ticks(self) -> int:
        return self.mode_counts.get("TRANSITION", 0)


def _distance(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _players_by_id(state: GameState) -> Dict[str, object]:
    return {player.player_id: player for player in state.our_team}


class MatchEvaluator:
    """Turns simulation history into a :class:`MatchEvaluationResult`."""

    def evaluate(
        self,
        history: List,
    ) -> MatchEvaluationResult:

        mode_counts = {mode: 0 for mode in TACTICAL_MODES}
        action_counts = {action: 0 for action in PRIMARY_ACTIONS}
        primary_agent_counts = {agent: 0 for agent in KNOWN_AGENTS}

        total_ball_distance = 0.0
        player_movement: Dict[str, float] = {}

        changed_ticks = 0
        static_ticks = 0

        for step in history:

            decision = step.team_decision

            # --- tactical mode ---
            mode = decision.tactical_mode
            mode_counts[mode] = mode_counts.get(mode, 0) + 1

            # --- primary action ---
            action = decision.primary_action.value
            action_counts[action] = action_counts.get(action, 0) + 1

            # --- primary agent ---
            agent = decision.primary_agent
            primary_agent_counts[agent] = (
                primary_agent_counts.get(agent, 0) + 1
            )

            # --- ball movement ---
            ball_delta = _distance(
                step.state_before.ball_position,
                step.state_after.ball_position,
            )
            total_ball_distance += ball_delta

            # --- player movement ---
            before_players = _players_by_id(step.state_before)
            after_players = _players_by_id(step.state_after)

            tick_had_player_movement = False

            for player_id, before in before_players.items():

                after = after_players.get(player_id)
                if after is None:
                    continue

                delta = _distance(before.position, after.position)

                player_movement[player_id] = (
                    player_movement.get(player_id, 0.0) + delta
                )

                if delta > MOVEMENT_EPSILON:
                    tick_had_player_movement = True

            # --- state evolution ---
            if (
                ball_delta > MOVEMENT_EPSILON
                or tick_had_player_movement
            ):
                changed_ticks += 1
            else:
                static_ticks += 1

        return MatchEvaluationResult(
            total_ticks=len(history),
            mode_counts=mode_counts,
            action_counts=action_counts,
            primary_agent_counts=primary_agent_counts,
            total_ball_distance=round(total_ball_distance, 2),
            player_movement={
                pid: round(dist, 2)
                for pid, dist in player_movement.items()
            },
            changed_ticks=changed_ticks,
            static_ticks=static_ticks,
        )


def format_report(result: MatchEvaluationResult) -> str:
    """Return a human-readable multi-line evaluation report."""

    lines = []
    lines.append("=" * 55)
    lines.append("⚽ MATCH EVALUATION REPORT")
    lines.append("=" * 55)
    lines.append("")
    lines.append(f"Total Ticks: {result.total_ticks}")
    lines.append("")

    lines.append("Tactical Modes:")
    for mode in TACTICAL_MODES:
        lines.append(f"{mode}: {result.mode_counts.get(mode, 0)}")
    lines.append("")

    lines.append("Primary Actions:")
    for action in PRIMARY_ACTIONS:
        lines.append(f"{action}: {result.action_counts.get(action, 0)}")
    lines.append("")

    lines.append("Primary Agents:")
    for agent in KNOWN_AGENTS:
        lines.append(
            f"{agent.capitalize()}: "
            f"{result.primary_agent_counts.get(agent, 0)}"
        )
    lines.append("")

    lines.append("Movement:")
    lines.append(f"Ball Distance: {result.total_ball_distance:.2f}")
    lines.append("")

    lines.append("Player Movement:")
    for player_id, dist in result.player_movement.items():
        lines.append(f"{player_id.capitalize()}: {dist:.2f}")
    lines.append("")

    lines.append("State Evolution:")
    lines.append(f"Changed Ticks: {result.changed_ticks}")
    lines.append(f"Static Ticks: {result.static_ticks}")

    return "\n".join(lines)
