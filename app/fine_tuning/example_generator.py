"""
Turn GameStates into training examples using the EXISTING deterministic
football brain.

Pipeline (no football logic re-implemented here):

    GameState
        -> AgentCoordinator.get_coordinated_team_decision   (the real code)
        -> TeamDecision (tactical_mode / primary_agent / primary_action ...)
        -> TrainingExample (input built from the GameState, output = the
           deterministic decision)

Augmentation produces deterministic *variations* of the base scenarios by
jittering positions with a seeded RNG, then re-labels every variation with
the same deterministic pipeline. Labels are therefore always whatever the
existing rules actually produce - never invented by hand.
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from app.agents.coordinator import AgentCoordinator
from app.core.game_state import GameState, Player, Position
from app.core.serialization import serialize_game_state
from app.core.team_coordinator import TeamDecision
from app.evaluation.scenarios import load_all_scenarios
from app.evaluation.scenarios.scenario_models import EvaluationMode, Scenario

from app.fine_tuning.dataset_schema import (
    TrainingExample,
    TrainingInput,
    TrainingOutput,
)


# ----------------------------------------------------------------------
# GameState -> TrainingInput
# ----------------------------------------------------------------------

def _players_to_list(players_dict: dict) -> list:
    """serialize_game_state stores teams as {id: player}; flatten to a list."""

    return list(players_dict.values())


def game_state_to_input(
    game_state: GameState,
    tactical_context: str = "",
) -> TrainingInput:
    """
    Build a :class:`TrainingInput` from a GameState using the project's own
    serializer (so the on-the-wire representation matches the rest of the
    codebase).
    """

    serialized = serialize_game_state(game_state)
    return TrainingInput(
        ball_position=serialized["ball_position"],
        possession=serialized["possession"],
        our_team=_players_to_list(serialized["our_team"]),
        opponent_team=_players_to_list(serialized["opponent_team"]),
        tactical_context=tactical_context,
    )


# ----------------------------------------------------------------------
# TeamDecision -> TrainingOutput
# ----------------------------------------------------------------------

def team_decision_to_output(
    team_decision: TeamDecision,
    *,
    prefer_agent: Optional[str] = None,
) -> TrainingOutput:
    """
    Convert the deterministic :class:`TeamDecision` into a label.

    ``prefer_agent`` lets a scenario that is judged on an *individual* agent
    (e.g. the goalkeeper) label the example with that agent's own decision,
    matching how the benchmark evaluates such scenarios. When ``prefer_agent``
    is not set (or missing), the team's primary decision is used.
    """

    agent_id = team_decision.primary_agent
    decision = team_decision.agent_decisions.get(agent_id)

    if prefer_agent and prefer_agent in team_decision.agent_decisions:
        agent_id = prefer_agent
        decision = team_decision.agent_decisions[prefer_agent]
        action_value = decision.action.value
    else:
        action_value = team_decision.primary_action.value

    confidence = float(decision.confidence) if decision is not None else 0.5
    reason = (
        decision.reason
        if decision is not None and decision.reason
        else team_decision.reason
    )

    return TrainingOutput(
        tactical_mode=team_decision.tactical_mode,
        recommended_agent=agent_id,
        recommended_action=action_value,
        confidence=confidence,
        reason=reason,
    )


# ----------------------------------------------------------------------
# One example from a GameState
# ----------------------------------------------------------------------

def make_example(
    game_state: GameState,
    coordinator: AgentCoordinator,
    *,
    tactical_context: str = "",
    prefer_agent: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> TrainingExample:
    """
    Run the deterministic pipeline on ``game_state`` and build one labelled
    :class:`TrainingExample`.
    """

    team_decision = coordinator.get_coordinated_team_decision(game_state)
    training_input = game_state_to_input(game_state, tactical_context)
    training_output = team_decision_to_output(
        team_decision, prefer_agent=prefer_agent
    )

    return TrainingExample(
        input=training_input,
        output=training_output,
        metadata=metadata or {},
    )


# ----------------------------------------------------------------------
# Base examples straight from the 16-scenario benchmark
# ----------------------------------------------------------------------

def _scenario_prefer_agent(scenario: Scenario) -> Optional[str]:
    """
    Scenarios judged INDIVIDUAL (e.g. goalkeeper) should be labelled with
    that agent's own decision, so the dataset matches how the benchmark
    grades them.
    """

    if scenario.evaluation_mode == EvaluationMode.INDIVIDUAL:
        return scenario.expected_individual_agent
    return None


def build_base_examples(
    coordinator: Optional[AgentCoordinator] = None,
) -> List[TrainingExample]:
    """
    One :class:`TrainingExample` per benchmark scenario, labelled by the
    deterministic pipeline. These are the "anchor" examples every dataset
    starts from.
    """

    coordinator = coordinator or AgentCoordinator()
    scenarios = load_all_scenarios()

    examples: List[TrainingExample] = []
    for scenario in scenarios:
        prefer = _scenario_prefer_agent(scenario)
        example = make_example(
            scenario.initial_game_state,
            coordinator,
            tactical_context=scenario.description,
            prefer_agent=prefer,
            metadata={
                "source_scenario": scenario.scenario_name,
                "category": scenario.category,
                "augmented": False,
                "evaluation_mode": scenario.evaluation_mode,
            },
        )
        examples.append(example)

    return examples


# ----------------------------------------------------------------------
# Deterministic augmentation
# ----------------------------------------------------------------------

def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _jitter_position(
    position: Position,
    rng: random.Random,
    amount: float,
) -> Position:
    return Position(
        x=round(_clamp(position.x + rng.uniform(-amount, amount)), 2),
        y=round(_clamp(position.y + rng.uniform(-amount, amount)), 2),
    )


def _jitter_game_state(
    game_state: GameState,
    rng: random.Random,
    amount: float,
) -> GameState:
    """
    Deterministic positional variation of a GameState.

    Possession is preserved (so the tactical mode family is stable), but
    ball and player positions move a little. Re-labelling with the
    deterministic engine then yields whatever action the rules produce for
    the new geometry - which may or may not match the base example.
    """

    return GameState(
        ball_position=_jitter_position(game_state.ball_position, rng, amount),
        our_team=[
            Player(
                player_id=p.player_id,
                role=p.role,
                position=_jitter_position(p.position, rng, amount),
            )
            for p in game_state.our_team
        ],
        opponent_team=[
            Player(
                player_id=p.player_id,
                role=p.role,
                position=_jitter_position(p.position, rng, amount),
            )
            for p in game_state.opponent_team
        ],
        possession=game_state.possession,
    )


def generate_examples(
    dataset_size: int,
    *,
    seed: int = 42,
    position_jitter: float = 6.0,
    coordinator: Optional[AgentCoordinator] = None,
) -> List[TrainingExample]:
    """
    Generate ``dataset_size`` labelled examples.

    The 16 base scenarios are always included first. The remainder are
    deterministic augmented variations, round-robined across the base
    scenarios and jittered with a seeded RNG. Every example - base or
    augmented - is labelled by the existing deterministic pipeline.

    Fully deterministic: same ``seed`` + ``dataset_size`` -> identical
    dataset.
    """

    if dataset_size < 1:
        raise ValueError(f"dataset_size must be >= 1, got {dataset_size}")

    coordinator = coordinator or AgentCoordinator()
    scenarios = load_all_scenarios()
    rng = random.Random(seed)

    base = build_base_examples(coordinator)

    # If the caller wants fewer than the base set, keep the first N base
    # examples (deterministic, benchmark order).
    if dataset_size <= len(base):
        return base[:dataset_size]

    examples: List[TrainingExample] = list(base)
    needed = dataset_size - len(base)

    variation_index = 0
    for i in range(needed):
        scenario = scenarios[i % len(scenarios)]
        variation_index += 1
        jittered = _jitter_game_state(
            scenario.initial_game_state, rng, position_jitter
        )
        prefer = _scenario_prefer_agent(scenario)
        example = make_example(
            jittered,
            coordinator,
            tactical_context=scenario.description,
            prefer_agent=prefer,
            metadata={
                "source_scenario": scenario.scenario_name,
                "category": scenario.category,
                "augmented": True,
                "variation": variation_index,
                "evaluation_mode": scenario.evaluation_mode,
            },
        )
        examples.append(example)

    return examples
