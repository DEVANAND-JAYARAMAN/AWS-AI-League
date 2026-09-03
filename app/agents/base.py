from abc import ABC, abstractmethod

from app.core.decisions import FootballDecision
from app.core.game_state import GameState


class BaseFootballAgent(ABC):
    """
    Base class for all specialized football agents.
    """

    def __init__(
        self,
        player_id: str,
        role: str,
    ):
        self.player_id = player_id
        self.role = role

    @abstractmethod
    def decide(
        self,
        game_state: GameState,
    ) -> FootballDecision:
        """
        Analyze the game state and return a football decision.
        """
        pass