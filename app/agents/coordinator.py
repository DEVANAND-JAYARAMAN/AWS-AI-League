from app.agents.defender import DefenderAgent
from app.agents.goalkeeper import GoalkeeperAgent
from app.agents.midfielder import MidfielderAgent
from app.agents.striker import StrikerAgent

from app.core.decisions import FootballDecision
from app.core.game_state import GameState
from app.core.team_coordinator import (
    TeamDecision,
    coordinate_team_decision,
)


class AgentCoordinator:
    """
    Coordinates specialized football agents.

    Each registered agent receives the same GameState
    and returns a structured FootballDecision.
    """

    def __init__(self):

        self.goalkeeper_agent = GoalkeeperAgent(
            player_id="goalkeeper",
            role="GOALKEEPER",
        )

        self.defender_agent = DefenderAgent(
            player_id="defender",
            role="DEFENDER",
        )

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

        goalkeeper_decision = self.goalkeeper_agent.decide(
            game_state
        )

        defender_decision = self.defender_agent.decide(
            game_state
        )

        midfielder_decision = self.midfielder_agent.decide(
            game_state
        )

        striker_decision = self.striker_agent.decide(
            game_state
        )

        decisions["goalkeeper"] = goalkeeper_decision
        decisions["defender"] = defender_decision
        decisions["midfielder"] = midfielder_decision
        decisions["striker"] = striker_decision

        return decisions

    def get_coordinated_team_decision(
        self,
        game_state: GameState,
    ) -> TeamDecision:
        """
        Collect raw agent decisions and run them through the deterministic
        team coordination layer to produce a single TeamDecision.
        """

        agent_decisions = self.get_team_decisions(game_state)

        return coordinate_team_decision(
            game_state=game_state,
            agent_decisions=agent_decisions,
        )
