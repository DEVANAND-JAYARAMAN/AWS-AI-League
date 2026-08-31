from simulation.decision import FootballDecision
from simulation.game_state import GameState
from simulation.tactical_analyzer import analyze_game_state


def make_decision(game_state: GameState) -> FootballDecision:
    """
    Make a basic tactical decision based on the
    structured tactical analysis.

    This is a temporary deterministic decision engine.

    Later, the Strands agent will improve or replace
    the strategic reasoning layer.
    """

    analysis = analyze_game_state(game_state)

    # Defensive mode
    if analysis["tactical_mode"] == "DEFEND":

        closest_player = analysis["closest_to_ball"]

        return FootballDecision(
            action="PRESS",
            target_player_id=closest_player["player_id"],
            confidence=0.75,
            reason=(
                "The opponent has possession, so the player "
                "closest to the ball should apply pressure."
            ),
        )

    # Attacking mode
    attacking_players = analysis["open_attacking_players"]

    if attacking_players:

        target = attacking_players[0]

        return FootballDecision(
            action="PASS",
            target_player_id=target["player_id"],
            confidence=0.80,
            reason=(
                "An attacking teammate is available without "
                "close opponent pressure."
            ),
        )

    # No open attacking option
    closest_player = analysis["closest_to_ball"]

    return FootballDecision(
        action="HOLD_POSITION",
        target_player_id=closest_player["player_id"],
        confidence=0.60,
        reason=(
            "No clearly open attacking player is currently "
            "available, so maintain possession and positioning."
        ),
    )