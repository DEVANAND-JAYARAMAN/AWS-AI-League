from simulation.game_state import (
    GameState,
    Player,
    Position,
)


def create_attacking_scenario() -> GameState:
    """
    Creates a sample attacking football situation.
    """

    return GameState(
        ball_position=Position(x=70, y=40),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),

            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=35, y=45),
            ),

            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=65, y=35),
            ),

            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=75, y=42),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="DEFENDER",
                position=Position(x=73, y=41),
            ),

            Player(
                player_id="opponent_2",
                role="DEFENDER",
                position=Position(x=78, y=45),
            ),

            Player(
                player_id="opponent_3",
                role="MIDFIELDER",
                position=Position(x=60, y=40),
            ),
        ],

        possession="OUR_TEAM",
    )

def create_open_pass_scenario() -> GameState:
    """
    Creates a scenario where an attacking teammate
    is clearly available for a pass.
    """

    return GameState(
        ball_position=Position(x=60, y=40),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=30, y=45),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=65, y=30),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=80, y=50),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="DEFENDER",
                position=Position(x=55, y=42),
            ),
            Player(
                player_id="opponent_2",
                role="DEFENDER",
                position=Position(x=55, y=55),
            ),
            Player(
                player_id="opponent_3",
                role="MIDFIELDER",
                position=Position(x=45, y=40),
            ),
        ],

        possession="OUR_TEAM",
    )


def create_defensive_scenario() -> GameState:
    """
    Creates a scenario where the opponent has possession.
    """

    return GameState(
        ball_position=Position(x=35, y=45),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=30, y=45),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=50, y=40),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=75, y=42),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="ATTACKER",
                position=Position(x=35, y=45),
            ),
            Player(
                player_id="opponent_2",
                role="MIDFIELDER",
                position=Position(x=45, y=40),
            ),
            Player(
                player_id="opponent_3",
                role="ATTACKER",
                position=Position(x=60, y=50),
            ),
        ],

        possession="OPPONENT_TEAM",
    )

def create_midfielder_pass_scenario() -> GameState:
    """
    Creates a scenario where the midfielder has the ball
    and the striker is clearly open for a forward pass.
    """

    return GameState(
        ball_position=Position(x=60, y=40),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=30, y=45),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=60, y=40),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=82, y=50),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="DEFENDER",
                position=Position(x=55, y=55),
            ),
            Player(
                player_id="opponent_2",
                role="DEFENDER",
                position=Position(x=65, y=25),
            ),
            Player(
                player_id="opponent_3",
                role="MIDFIELDER",
                position=Position(x=45, y=35),
            ),
        ],

        possession="OUR_TEAM",
    )


def create_shooting_scenario() -> GameState:
    """
    Creates a scenario where the striker has a
    clear shooting opportunity.
    """

    return GameState(
        ball_position=Position(x=82, y=50),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=40, y=45),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=70, y=40),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=82, y=50),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="DEFENDER",
                position=Position(x=70, y=40),
            ),
            Player(
                player_id="opponent_2",
                role="DEFENDER",
                position=Position(x=72, y=60),
            ),
            Player(
                player_id="opponent_3",
                role="MIDFIELDER",
                position=Position(x=60, y=45),
            ),
        ],

        possession="OUR_TEAM",
    )


def create_defender_press_scenario() -> GameState:
    """
    Opponent has possession and the ball (and our defender) are deep in
    our half. The defender is close enough to step out and press.

    defender: (30, 48)   ball: (25, 50)   -> distance ~4  (<= PRESS_RANGE)
    """

    return GameState(
        ball_position=Position(x=25, y=50),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=30, y=48),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=50, y=45),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=70, y=50),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="ATTACKER",
                position=Position(x=24, y=50),
            ),
            Player(
                player_id="opponent_2",
                role="MIDFIELDER",
                position=Position(x=35, y=40),
            ),
            Player(
                player_id="opponent_3",
                role="ATTACKER",
                position=Position(x=40, y=60),
            ),
        ],

        possession="OPPONENT_TEAM",
    )


def create_defender_reposition_scenario() -> GameState:
    """
    Opponent has possession but the ball is on the far side of the pitch.
    The defender should not chase it; instead move to a covering position
    between the ball and our goal.

    defender: (25, 50)   ball: (75, 50)   -> distance 50  (> PRESS_RANGE)
    """

    return GameState(
        ball_position=Position(x=75, y=50),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=25, y=50),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=55, y=45),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=80, y=50),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="ATTACKER",
                position=Position(x=74, y=50),
            ),
            Player(
                player_id="opponent_2",
                role="MIDFIELDER",
                position=Position(x=70, y=40),
            ),
            Player(
                player_id="opponent_3",
                role="ATTACKER",
                position=Position(x=78, y=60),
            ),
        ],

        possession="OPPONENT_TEAM",
    )


def create_defender_support_scenario() -> GameState:
    """
    Our team has possession in the opponent half. The defender should hold
    a deep supporting position rather than pressing.

    defender: (35, 45)   ball: (65, 45)   possession: OUR_TEAM
    """

    return GameState(
        ball_position=Position(x=65, y=45),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=35, y=45),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=65, y=45),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=85, y=50),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="DEFENDER",
                position=Position(x=75, y=45),
            ),
            Player(
                player_id="opponent_2",
                role="DEFENDER",
                position=Position(x=80, y=55),
            ),
            Player(
                player_id="opponent_3",
                role="MIDFIELDER",
                position=Position(x=60, y=40),
            ),
        ],

        possession="OUR_TEAM",
    )


def create_goalkeeper_danger_scenario() -> GameState:
    """
    Opponent has possession and is attacking near our goal, but the ball
    is not right on top of it. The keeper should MOVE to an interception
    position between the ball and the goal.

    keeper: (5, 50)   ball: (22, 50)   OUR_GOAL: (0, 50)
    ball -> goal distance ~22  (EMERGENCY < 22 <= DANGER)
    """

    return GameState(
        ball_position=Position(x=22, y=50),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=18, y=48),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=40, y=45),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=65, y=50),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="ATTACKER",
                position=Position(x=23, y=50),
            ),
            Player(
                player_id="opponent_2",
                role="ATTACKER",
                position=Position(x=30, y=42),
            ),
            Player(
                player_id="opponent_3",
                role="MIDFIELDER",
                position=Position(x=45, y=55),
            ),
        ],

        possession="OPPONENT_TEAM",
    )


def create_goalkeeper_emergency_scenario() -> GameState:
    """
    Opponent has possession and the ball is right on our goal. The keeper
    should come out and PRESS the ball carrier.

    keeper: (5, 50)   ball: (7, 50)   OUR_GOAL: (0, 50)
    ball -> goal distance 7  (<= EMERGENCY_RANGE)
    """

    return GameState(
        ball_position=Position(x=7, y=50),

        our_team=[
            Player(
                player_id="goalkeeper",
                role="GOALKEEPER",
                position=Position(x=5, y=50),
            ),
            Player(
                player_id="defender",
                role="DEFENDER",
                position=Position(x=12, y=46),
            ),
            Player(
                player_id="midfielder",
                role="MIDFIELDER",
                position=Position(x=35, y=48),
            ),
            Player(
                player_id="striker",
                role="STRIKER",
                position=Position(x=60, y=50),
            ),
        ],

        opponent_team=[
            Player(
                player_id="opponent_1",
                role="ATTACKER",
                position=Position(x=8, y=50),
            ),
            Player(
                player_id="opponent_2",
                role="ATTACKER",
                position=Position(x=15, y=55),
            ),
            Player(
                player_id="opponent_3",
                role="MIDFIELDER",
                position=Position(x=30, y=45),
            ),
        ],

        possession="OPPONENT_TEAM",
    )