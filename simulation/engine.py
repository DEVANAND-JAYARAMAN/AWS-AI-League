"""
Deterministic football simulation engine.

The engine drives the existing decision stack over multiple sequential
ticks:

    GameState
        -> AgentCoordinator (raw agent decisions)
        -> team coordination (TeamDecision)
        -> apply primary team action
        -> simulation dynamics (supporting players evolve)
        -> updated GameState
        -> next tick

Action execution is intentionally minimal - no physics, no probability,
just simple deterministic state updates. Assumptions are documented on
each handler below.
"""

import copy
from dataclasses import dataclass

from agents.coordinator import AgentCoordinator

from simulation.dynamics import PLAYER_MAX_STEP, apply_dynamics, move_towards
from simulation.field import OPPONENT_GOAL
from simulation.game_state import GameState, Position
from simulation.team_coordinator import TeamDecision, coordinate_team_decision


@dataclass
class SimulationStepResult:
    """Result of a single simulation tick, including the state transition."""

    tick: int
    team_decision: TeamDecision
    state_before: GameState
    state_after: GameState

    @property
    def game_state(self) -> GameState:
        """Backwards-compatible alias for the post-tick state."""
        return self.state_after


def _find_our_player(game_state: GameState, player_id: str):
    """Return the player in our team with the given id, or None."""

    for player in game_state.our_team:
        if player.player_id == player_id:
            return player

    return None


class FootballSimulationEngine:
    """
    Steps a GameState forward one deterministic tick at a time.
    """

    def __init__(
        self,
        initial_game_state: GameState,
        player_max_step: float = PLAYER_MAX_STEP,
    ):
        # Deep copy so the caller's scenario object is never mutated.
        self.game_state: GameState = copy.deepcopy(initial_game_state)
        self.tick_number: int = 0
        self.player_max_step = player_max_step
        self.coordinator = AgentCoordinator()
        self.history: list = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def step(self) -> SimulationStepResult:
        """
        Run one tick:

        1. Collect raw agent decisions for the current state.
        2. Reduce them to a single TeamDecision.
        3. Apply the primary team action to a fresh copy of the state.
        4. Apply simulation dynamics (supporting players move a little).
        5. Store and return the state transition.
        """

        self.tick_number += 1

        state_before = copy.deepcopy(self.game_state)

        agent_decisions = self.coordinator.get_team_decisions(
            self.game_state
        )

        team_decision = coordinate_team_decision(
            game_state=self.game_state,
            agent_decisions=agent_decisions,
        )

        # Work on a copy so a half-applied update can never corrupt the
        # live state, and scenario objects stay untouched.
        next_state = copy.deepcopy(self.game_state)

        self._apply_primary_action(next_state, team_decision)

        # Let the rest of the world evolve so nothing freezes forever.
        apply_dynamics(
            state=next_state,
            team_decision=team_decision,
            max_step=self.player_max_step,
        )

        self.game_state = next_state

        result = SimulationStepResult(
            tick=self.tick_number,
            team_decision=team_decision,
            state_before=state_before,
            state_after=next_state,
        )

        self.history.append(result)

        return result

    def run(self, ticks: int) -> list:
        """Run several ticks and return the list of step results."""

        return [self.step() for _ in range(ticks)]

    # ------------------------------------------------------------------
    # Action execution (deterministic, no physics)
    # ------------------------------------------------------------------

    def _apply_primary_action(
        self,
        state: GameState,
        team_decision: TeamDecision,
    ) -> None:

        action = team_decision.primary_action.value
        agent_id = team_decision.primary_agent
        decision = team_decision.agent_decisions[agent_id]

        if action == "MOVE":
            self._apply_move(state, agent_id, decision)

        elif action == "PASS":
            self._apply_pass(state, decision)

        elif action == "SHOOT":
            self._apply_shoot(state)

        elif action == "PRESS":
            self._apply_press(state, agent_id, decision)

        # HOLD_POSITION: the primary agent does not move. Supporting
        # players still evolve via apply_dynamics(), so the world is not
        # frozen.

        # Possession is deliberately left unchanged for every action in
        # this version (see task notes):
        #   PASS  -> stays OUR_TEAM
        #   SHOOT -> stays OUR_TEAM
        #   PRESS -> stays OPPONENT_TEAM (no tackle model yet)
        #   MOVE / HOLD_POSITION -> unchanged

    def _apply_move(self, state, agent_id, decision) -> None:
        """MOVE: step the primary agent toward its target_position."""

        player = _find_our_player(state, agent_id)

        if player is not None and decision.target_position is not None:
            player.position = move_towards(
                current_position=player.position,
                target_position=decision.target_position,
                max_distance=self.player_max_step,
            )

    def _apply_pass(self, state, decision) -> None:
        """PASS: move the ball to the receiving teammate's position."""

        receiver = _find_our_player(state, decision.target_player_id)

        if receiver is not None:
            state.ball_position = Position(
                x=receiver.position.x,
                y=receiver.position.y,
            )

    def _apply_shoot(self, state) -> None:
        """SHOOT: move the ball to the opponent goal (no goal probability)."""

        state.ball_position = Position(
            x=OPPONENT_GOAL.x,
            y=OPPONENT_GOAL.y,
        )

    def _apply_press(self, state, agent_id, decision) -> None:
        """PRESS: step the pressing agent toward the ball / target position."""

        player = _find_our_player(state, agent_id)

        if player is None:
            return

        target = decision.target_position or state.ball_position

        player.position = move_towards(
            current_position=player.position,
            target_position=target,
            max_distance=self.player_max_step,
        )
