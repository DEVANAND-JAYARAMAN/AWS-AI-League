import logging

from agents.first_agent import create_agent
from config.logging_config import setup_logging


def main():

    run_test(
        "Striker - Attacking Pressure",
        create_attacking_scenario,
    )

    run_test(
        "Striker - Defensive Situation",
        create_defensive_scenario,
    )

    run_test(
        "Striker - Clear Shooting Opportunity",
        create_shooting_scenario,
    )