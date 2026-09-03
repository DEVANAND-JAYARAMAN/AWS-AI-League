from app.core.game_state import GameState, Player
from app.core.decision_tools import (
    find_closest_player,
    find_open_players,
)


def analyze_game_state(game_state: GameState) -> dict:
    """
    Analyze the current football game state and return
    structured tactical information.
    """

    closest_player, closest_distance = find_closest_player(
        players=game_state.our_team,
        target_position=game_state.ball_position,
    )

    open_players = find_open_players(
        players=game_state.our_team,
        opponents=game_state.opponent_team,
        safety_distance=10.0,
    )

    attacking_options = [
        player
        for player in open_players
        if player.role in {"MIDFIELDER", "STRIKER"}
    ]

    defensive_options = [
        player
        for player in open_players
        if player.role in {"DEFENDER", "GOALKEEPER"}
    ]

    if game_state.possession == "OUR_TEAM":
        tactical_mode = "ATTACK"
    else:
        tactical_mode = "DEFEND"

    return {
        "possession": game_state.possession,
        "tactical_mode": tactical_mode,
        "closest_to_ball": {
            "player_id": closest_player.player_id,
            "role": closest_player.role,
            "distance": closest_distance,
        },
        "open_attacking_players": [
            {
                "player_id": player.player_id,
                "role": player.role,
            }
            for player in attacking_options
        ],
        "open_defensive_players": [
            {
                "player_id": player.player_id,
                "role": player.role,
            }
            for player in defensive_options
        ],
    }