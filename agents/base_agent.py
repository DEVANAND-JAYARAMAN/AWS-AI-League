from abc import ABC, abstractmethod

from simulation.decision import FootballDecision
from simulation.game_state import GameState


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