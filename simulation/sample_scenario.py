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