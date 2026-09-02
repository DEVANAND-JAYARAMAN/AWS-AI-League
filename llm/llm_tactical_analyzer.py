"""
LLM tactical analyzer (Amazon Nova Pro via the Bedrock Converse API).

    GameState
        -> build_tactical_prompt        (Converse messages + system)
        -> BedrockClient.invoke          (real Nova Pro call)
        -> parse_recommendation          (validate against real enums +
        -> TacticalRecommendation         the live GameState players)

Advisory only. This module does not import or modify any deterministic
decision code, and it never mutates the GameState. It is written to be
reused later from a Strands agent.
"""

import logging

from llm.bedrock_client import BedrockClient
from llm.response_parser import TacticalRecommendation, parse_recommendation
from llm.tactical_prompt import build_tactical_prompt
from simulation.game_state import GameState

logger = logging.getLogger(__name__)


class LLMTacticalAnalyzer:
    """Turns a GameState into an advisory :class:`TacticalRecommendation`."""

    def __init__(
        self,
        client: BedrockClient | None = None,
        *,
        region_name: str | None = None,
        model_id: str | None = None,
        max_tokens: int = 500,
        temperature: float = 0.2,
    ):
        self.client = client or BedrockClient(
            region_name=region_name, model_id=model_id
        )
        self.max_tokens = max_tokens
        self.temperature = temperature

    def analyze(self, game_state: GameState) -> TacticalRecommendation:
        """Run the full prompt -> Nova Pro -> parse pipeline."""

        prompt = build_tactical_prompt(game_state)

        logger.info("Requesting tactical recommendation from Bedrock")
        raw_text = self.client.invoke(
            prompt["messages"],
            system=prompt["system"],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        valid_agents = [player.player_id for player in game_state.our_team]
        recommendation = parse_recommendation(raw_text, valid_agents=valid_agents)

        logger.info(
            "LLM recommends: %s / %s (confidence %.2f)",
            recommendation.recommended_agent,
            recommendation.recommended_action,
            recommendation.confidence,
        )
        return recommendation
