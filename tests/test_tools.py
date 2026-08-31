from tools.football_tools import calculate_distance


def main():
    print("\n⚽ Football Tool Test")

    result = calculate_distance(
        player_x=10,
        player_y=20,
        target_x=30,
        target_y=40,
    )

    print(f"Tool result: {result}")


if __name__ == "__main__":
    main()