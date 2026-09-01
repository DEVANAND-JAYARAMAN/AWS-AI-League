"""Unit tests for the deterministic move_towards helper."""

import math

from simulation.dynamics import move_towards
from simulation.game_state import Position


def test_moves_at_most_max_distance():

    start = Position(x=0, y=0)
    target = Position(x=100, y=0)

    result = move_towards(start, target, max_distance=8.0)

    moved = math.hypot(result.x - start.x, result.y - start.y)

    assert moved <= 8.0 + 0.05
    assert result.x == 8.0
    assert result.y == 0.0


def test_does_not_overshoot_close_target():

    start = Position(x=0, y=0)
    target = Position(x=3, y=4)  # distance 5

    result = move_towards(start, target, max_distance=8.0)

    assert (result.x, result.y) == (3, 4)


def test_already_at_target():

    start = Position(x=10, y=10)
    target = Position(x=10, y=10)

    result = move_towards(start, target, max_distance=8.0)

    assert (result.x, result.y) == (10, 10)


def test_diagonal_step_length():

    start = Position(x=0, y=0)
    target = Position(x=10, y=10)  # distance ~14.14

    result = move_towards(start, target, max_distance=5.0)

    moved = math.hypot(result.x, result.y)

    assert abs(moved - 5.0) < 0.05


def main():

    test_moves_at_most_max_distance()
    test_does_not_overshoot_close_target()
    test_already_at_target()
    test_diagonal_step_length()

    print("⚽ move_towards helper")
    print("All move_towards checks passed.")


if __name__ == "__main__":
    main()
