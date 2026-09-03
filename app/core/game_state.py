from dataclasses import dataclass
from typing import List


@dataclass
class Position:
    x: float
    y: float


@dataclass
class Player:
    player_id: str
    role: str
    position: Position


@dataclass
class GameState:
    ball_position: Position
    our_team: List[Player]
    opponent_team: List[Player]
    possession: str