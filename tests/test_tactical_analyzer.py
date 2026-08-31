from simulation.sample_scenario import create_attacking_scenario
from simulation.tactical_analyzer import analyze_game_state


def main():

    game_state = create_attacking_scenario()

    analysis = analyze_game_state(game_state)

    print("\n⚽ Tactical Analysis")

    print(f"\nPossession: {analysis['possession']}")
    print(f"Tactical Mode: {analysis['tactical_mode']}")

    closest = analysis["closest_to_ball"]

    print("\nClosest to Ball:")
    print(f"- Player ID: {closest['player_id']}")
    print(f"- Role: {closest['role']}")
    print(f"- Distance: {closest['distance']}")

    print("\nOpen Attacking Players:")

    if not analysis["open_attacking_players"]:
        print("- None")

    for player in analysis["open_attacking_players"]:
        print(
            f"- {player['role']} "
            f"({player['player_id']})"
        )

    print("\nOpen Defensive Players:")

    if not analysis["open_defensive_players"]:
        print("- None")

    for player in analysis["open_defensive_players"]:
        print(
            f"- {player['role']} "
            f"({player['player_id']})"
        )


if __name__ == "__main__":
    main()