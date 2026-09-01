from simulation.decision_engine import make_decision
from simulation.sample_scenario import create_attacking_scenario


def main():

    game_state = create_attacking_scenario()

    decision = make_decision(game_state)

    print("\n⚽ Football Decision Engine")

    tp = decision.target_position

    print(f"\nAction: {decision.action.value}")
    print(f"Target Player: {decision.target_player_id}")
    print(f"Target Position: {f'({tp.x}, {tp.y})' if tp else None}")
    print(f"Confidence: {decision.confidence}")
    print(f"Reason: {decision.reason}")


if __name__ == "__main__":
    main()