import logging

from agents.first_agent import create_agent
from config.logging_config import setup_logging


def main():
    setup_logging()

    logger = logging.getLogger("aws-ai-league")

    logger.info("Starting AWS AI League project")

    agent = create_agent()

    print("\n⚽ AWS AI League - Agentic Football")
    print("First Strands agent created successfully!")
    print(f"Agent type: {type(agent)}")

    print("\nNext step: Connect a model provider on the personal laptop.\n")


if __name__ == "__main__":
    main()