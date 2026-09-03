from dataclasses import dataclass
from enum import Enum
from typing import Optional

# Position lives in game_state, which imports nothing from this module,
# so this import is safe and does not create a circular dependency.
from app.core.game_state import Position


class FootballAction(str, Enum):
    """
    Valid actions that a football agent can take.
    """

    PASS = "PASS"
    PRESS = "PRESS"
    HOLD_POSITION = "HOLD_POSITION"
    SHOOT = "SHOOT"
    MOVE = "MOVE"


@dataclass
class FootballDecision:
    """
    Represents a validated machine-readable football decision.
    """

    action: FootballAction
    target_player_id: Optional[str]
    confidence: float
    reason: str
    # Optional destination for movement-style actions (e.g. MOVE).
    # Defaults to None so existing call sites remain valid.
    target_position: Optional[Position] = None