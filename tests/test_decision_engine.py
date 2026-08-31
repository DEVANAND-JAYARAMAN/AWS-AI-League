from simulation.sample_scenario import create_attacking_scenario
from simulation.decision_engine import make_decision


def main():

    game_state = create_attacking_scenario()

    decision = make_decision(game_state)

    print("\n⚽ Football Decision Engine")

    print(f"\nAction: {decision.action}")
    print(f"Target Player: {decision.target_player_id}")
    print(f"Confidence: {decision.confidence}")
    print(f"Reason: {decision.reason}")


if __name__ == "__main__":
    main()