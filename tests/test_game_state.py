from simulation.sample_scenario import create_attacking_scenario


def main():

    game_state = create_attacking_scenario()

    print("\n⚽ Football Game State")

    print(
        f"Ball Position: "
        f"({game_state.ball_position.x}, "
        f"{game_state.ball_position.y})"
    )

    print(f"\nPossession: {game_state.possession}")

    print("\nOur Team:")

    for player in game_state.our_team:

        print(
            f"- {player.role}: "
            f"({player.position.x}, "
            f"{player.position.y})"
        )

    print("\nOpponent Team:")

    for player in game_state.opponent_team:

        print(
            f"- {player.role}: "
            f"({player.position.x}, "
            f"{player.position.y})"
        )


if __name__ == "__main__":
    main()