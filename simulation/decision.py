from dataclasses import dataclass
from typing import Optional


@dataclass
class FootballDecision:
    """
    Represents a machine-readable football decision.
    """

    action: str
    target_player_id: Optional[str]
    confidence: float
    reason: str