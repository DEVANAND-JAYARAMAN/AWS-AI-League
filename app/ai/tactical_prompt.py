"""
Football context / prompt builder for the Bedrock tactical analyzer.

Reuses the existing :class:`~app.core.game_state.GameState` - it does
NOT define a second game-state model. It turns a GameState into a compact
text description plus a strict system instruction that forces JSON-only
output using the project's real enum values, and returns everything in
the Bedrock **Converse** message format.
"""

from app.core.decisions import FootballAction
from app.core.game_state import GameState

# Real, allowed values pulled straight from the existing project.
ALLOWED_ACTIONS = [action.value for action in FootballAction]
ALLOWED_MODES = ["ATTACK", "DEFENSE", "TRANSITION"]
# Fallback agent list; the parser prefers the ids in the live GameState.
KNOWN_AGENTS = ["goalkeeper", "defender", "midfielder", "striker"]


def _fmt_pos(position) -> str:
    if position is None:
        return "(unknown)"
    x = round(position.x, 1)
    y = round(position.y, 1)
    x = int(x) if x == int(x) else x
    y = int(y) if y == int(y) else y
    return f"({x}, {y})"


def _fmt_players(players) -> str:
    lines = [
        f"- {p.player_id}: role={p.role}, position={_fmt_pos(p.position)}"
        for p in players
    ]
    return "\n".join(lines) if lines else "- (none)"


def build_football_context(game_state: GameState) -> str:
    """Compact, LLM-friendly description of the current situation."""

    return (
        "BALL\n"
        f"Position: {_fmt_pos(game_state.ball_position)}\n\n"
        "POSSESSION\n"
        f"{game_state.possession}\n\n"
        "OUR PLAYERS\n"
        f"{_fmt_players(game_state.our_team)}\n\n"
        "OPPONENT PLAYERS\n"
        f"{_fmt_players(game_state.opponent_team)}"
    )


SYSTEM_PROMPT = (
    "You are an AI football (soccer) tactical analysis assistant.\n\n"
    "Analyze the current football game state and return exactly one\n"
    "tactical recommendation.\n\n"
    "Your recommendation must use ONLY the tactical modes and football\n"
    "actions supported by the project. Do not invent actions, modes, or\n"
    "player names.\n\n"
    "  tactical_mode      one of: " + ", ".join(ALLOWED_MODES) + "\n"
    "  recommended_action one of: " + ", ".join(ALLOWED_ACTIONS) + "\n"
    "  recommended_agent  must be one of our players listed in the state\n"
    "  confidence         a number between 0 and 1\n"
    "  reason             a short explanation string\n\n"
    "Return VALID JSON ONLY. No markdown, no code fences, no text before\n"
    "or after the JSON object. Example shape:\n"
    '{"tactical_mode": "ATTACK", "recommended_agent": "striker", '
    '"recommended_action": "SHOOT", "confidence": 0.9, '
    '"reason": "..."}'
)


def build_tactical_prompt(game_state: GameState) -> dict:
    """
    Return ``{"system": [...], "messages": [...]}`` in Bedrock Converse
    format, ready for :meth:`app.ai.bedrock_client.BedrockClient.invoke`.
    """

    our_players = ", ".join(p.player_id for p in game_state.our_team) or "(none)"

    user_text = (
        "Current game state:\n\n"
        f"{build_football_context(game_state)}\n\n"
        f"Our players you may recommend: {our_players}\n\n"
        "Give your single tactical recommendation as JSON only."
    )

    return {
        "system": [{"text": SYSTEM_PROMPT}],
        "messages": [
            {"role": "user", "content": [{"text": user_text}]},
        ],
    }
