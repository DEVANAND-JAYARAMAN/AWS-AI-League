from dataclasses import dataclass
from enum import Enum
from typing import Optional


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