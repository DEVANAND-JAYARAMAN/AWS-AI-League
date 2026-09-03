"""
Tactical Agent adapter.

    Receive GameState
          -> call tactical tools
          -> return a TeamDecision summary

A real strands.Agent would let an LLM decide which tool to call; this
local adapter just calls them in a fixed deterministic order.
"""

from app.strands.tactical_tools import analyze_tactical_state, get_team_decision

# Future integration point:
# from strands import Agent
# _agent = Agent(
#     model=<bedrock model provider>,
#     system_prompt="You are a football tactical coordinator...",
#     tools=[analyze_tactical_state, get_team_decision],
# )


class TacticalAgentAdapter:
    """Deterministic adapter over the tactical tools."""

    #: Tools this agent "has access to" (what a real Agent would receive).
    tools = [analyze_tactical_state, get_team_decision]

    def analyze(self, game_state) -> dict:
        """
        Return a combined tactical picture for one game state:

            {
              "analysis": {...},        # from analyze_tactical_state
              "team_decision": {...},   # from get_team_decision
            }
        """

        return {
            "analysis": analyze_tactical_state(game_state),
            "team_decision": get_team_decision(game_state),
        }

    def decide(self, game_state) -> dict:
        """Just the serialized TeamDecision (the primary output)."""
        return get_team_decision(game_state)
