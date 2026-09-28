"""
Training-data schema for football tactical fine-tuning.

A fine-tuning example teaches a foundation model to perform the same kind
of tactical reasoning the deterministic football brain already performs:

    INPUT   a compact description of the GameState + tactical context
    OUTPUT  tactical_mode / recommended_agent / recommended_action /
            confidence / reason

The allowed vocabularies are pulled straight from the existing project so
this schema can never drift away from the real engine:

    ALLOWED_ACTIONS  <- app.core.decisions.FootballAction
    ALLOWED_MODES    <- app.ai.tactical_prompt.ALLOWED_MODES

The dataclasses here are plain, JSON-serializable containers. They own no
football logic - labels are always produced by the deterministic pipeline
(see :mod:`app.fine_tuning.example_generator`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# Real, allowed values pulled straight from the existing project.
from app.core.decisions import FootballAction
from app.ai.tactical_prompt import ALLOWED_MODES as _ALLOWED_MODES

ALLOWED_ACTIONS: List[str] = [action.value for action in FootballAction]
ALLOWED_MODES: List[str] = list(_ALLOWED_MODES)


# ----------------------------------------------------------------------
# Input side
# ----------------------------------------------------------------------

@dataclass
class TrainingInput:
    """
    The situation shown to the model.

    ``ball_position`` is ``{"x": float, "y": float}``.
    ``our_team`` / ``opponent_team`` are lists of
    ``{"player_id", "role", "position": {"x", "y"}}`` dicts.
    """

    ball_position: Dict[str, float]
    possession: str
    our_team: List[Dict[str, Any]]
    opponent_team: List[Dict[str, Any]]
    tactical_context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ball_position": self.ball_position,
            "possession": self.possession,
            "our_team": self.our_team,
            "opponent_team": self.opponent_team,
            "tactical_context": self.tactical_context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingInput":
        return cls(
            ball_position=data["ball_position"],
            possession=data["possession"],
            our_team=data.get("our_team", []),
            opponent_team=data.get("opponent_team", []),
            tactical_context=data.get("tactical_context", ""),
        )


# ----------------------------------------------------------------------
# Output side
# ----------------------------------------------------------------------

@dataclass
class TrainingOutput:
    """The label the model should learn to produce for a given input."""

    tactical_mode: str
    recommended_agent: str
    recommended_action: str
    confidence: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tactical_mode": self.tactical_mode,
            "recommended_agent": self.recommended_agent,
            "recommended_action": self.recommended_action,
            "confidence": self.confidence,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingOutput":
        return cls(
            tactical_mode=data["tactical_mode"],
            recommended_agent=data["recommended_agent"],
            recommended_action=data["recommended_action"],
            confidence=float(data["confidence"]),
            reason=data["reason"],
        )


# ----------------------------------------------------------------------
# One example
# ----------------------------------------------------------------------

@dataclass
class TrainingExample:
    """
    One supervised fine-tuning record: ``input`` -> ``output``.

    ``metadata`` carries provenance (source scenario, category, whether it
    is an augmented variation, ...) so datasets stay auditable. Metadata is
    never shown to the model at training time - it is stripped when writing
    the SageMaker conversational format.
    """

    input: TrainingInput
    output: TrainingOutput
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ---- generic JSON dict form (used by our own tooling) ----

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": self.input.to_dict(),
            "output": self.output.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingExample":
        return cls(
            input=TrainingInput.from_dict(data["input"]),
            output=TrainingOutput.from_dict(data["output"]),
            metadata=data.get("metadata", {}),
        )
