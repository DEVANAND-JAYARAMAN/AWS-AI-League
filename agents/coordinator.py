from agents.midfielder_agent import MidfielderAgent
from agents.striker_agent import StrikerAgent

from simulation.decision import FootballDecision
from simulation.game_state import GameState


class AgentCoordinator:
    """
    Coordinates specialized football agents.

    Each registered agent receives the same GameState
    and returns a structured FootballDecision.
    """

    def __init__(self):

        self.midfielder_agent = MidfielderAgent(
            player_id="midfielder",
            role="MIDFIELDER",
        )

        self.striker_agent = StrikerAgent(
            player_id="striker",
            role="STRIKER",
        )

    def get_team_decisions(
        self,
        game_state: GameState,
    ) -> dict[str, FootballDecision]:
        """
        Collect decisions from all registered agents.
        """

        decisions = {}

        midfielder_decision = self.midfielder_agent.decide(
            game_state
        )

        striker_decision = self.striker_agent.decide(
            game_state
        )

        decisions["midfielder"] = midfielder_decision
        decisions["striker"] = striker_decision

        return decisions
