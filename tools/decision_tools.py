from typing import List, Tuple

from simulation.game_state import Player, Position
from tools.football_tools import calculate_distance


def get_distance(
    source: Position,
    target: Position,
) -> float:
    """
    Helper function for calculating distance between positions.
    """

    return calculate_distance(
        player_x=source.x,
        player_y=source.y,
        target_x=target.x,
        target_y=target.y,
    )


def find_closest_player(
    players: List[Player],
    target_position: Position,
) -> Tuple[Player, float]:
    """
    Find the player closest to a target position.

    Returns:
        A tuple containing the closest player and distance.
    """

    closest_player = None
    closest_distance = float("inf")

    for player in players:

        distance = get_distance(
            source=player.position,
            target=target_position,
        )

        if distance < closest_distance:

            closest_player = player
            closest_distance = distance

    return closest_player, round(closest_distance, 2)


def find_open_players(
    players: List[Player],
    opponents: List[Player],
    safety_distance: float = 10.0,
) -> List[Player]:
    """
    Find players who do not have an opponent within
    the specified safety distance.
    """

    open_players = []

    for player in players:

        nearest_opponent, distance = find_closest_player(
            players=opponents,
            target_position=player.position,
        )

        if distance >= safety_distance:
            open_players.append(player)

    return open_players