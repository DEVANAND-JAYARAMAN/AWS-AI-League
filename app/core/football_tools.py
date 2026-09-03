import math

from strands import tool


@tool
def calculate_distance(
    player_x: float,
    player_y: float,
    target_x: float,
    target_y: float,
) -> float:
    """
    Calculate the Euclidean distance between a player
    and a target position on the football field.

    Args:
        player_x: X coordinate of the player.
        player_y: Y coordinate of the player.
        target_x: X coordinate of the target.
        target_y: Y coordinate of the target.

    Returns:
        The distance between the player and target.
    """

    distance = math.sqrt(
        (target_x - player_x) ** 2
        + (target_y - player_y) ** 2
    )

    return round(distance, 2)