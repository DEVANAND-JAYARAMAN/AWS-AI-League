"""
Amazon Bedrock integration layer.

    GameState
        -> tactical_prompt.build_tactical_prompt   (football context)
        -> BedrockClient.invoke                     (Amazon Nova Pro,
                                                     Converse API)
        -> response_parser.parse_recommendation    (validate JSON)
        -> TacticalRecommendation                  (advisory only)

This layer is **advisory**. It never mutates a GameState and never
replaces the deterministic football engine, which stays the source of
truth. AWS credentials are resolved by boto3's default provider chain -
nothing here reads or stores secrets.
"""

from llm.bedrock_client import (
    BedrockClient,
    BedrockInvocationError,
    DEFAULT_MODEL_ID,
    DEFAULT_REGION,
)
from llm.response_parser import (
    TacticalRecommendation,
    TacticalValidationError,
    parse_recommendation,
)
from llm.tactical_prompt import (
    ALLOWED_ACTIONS,
    ALLOWED_MODES,
    KNOWN_AGENTS,
    build_football_context,
    build_tactical_prompt,
)
from llm.llm_tactical_analyzer import LLMTacticalAnalyzer

__all__ = [
    "BedrockClient",
    "BedrockInvocationError",
    "DEFAULT_MODEL_ID",
    "DEFAULT_REGION",
    "TacticalRecommendation",
    "TacticalValidationError",
    "parse_recommendation",
    "ALLOWED_ACTIONS",
    "ALLOWED_MODES",
    "KNOWN_AGENTS",
    "build_football_context",
    "build_tactical_prompt",
    "LLMTacticalAnalyzer",
]
