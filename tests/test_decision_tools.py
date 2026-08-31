from simulation.sample_scenario import create_attacking_scenario
from tools.decision_tools import (
    find_closest_player,
    find_open_players,
)


def main():

    game_state = create_attacking_scenario()

    print("\n⚽ Football Decision Engine Test")

    # Find our player closest to the ball
    closest_player, distance = find_closest_player(
        players=game_state.our_team,
        target_position=game_state.ball_position,
    )

    print("\nClosest player to the ball:")
    print(f"Player: {closest_player.role}")
    print(f"Distance: {distance}")

    # Find open players
    open_players = find_open_players(
        players=game_state.our_team,
        opponents=game_state.opponent_team,
        safety_distance=10.0,
    )

    print("\nOpen players:")

    if not open_players:
        print("No players are currently open.")

    for player in open_players:
        print(
            f"- {player.role} "
            f"at ({player.position.x}, {player.position.y})"
        )


if __name__ == "__main__":
    main()