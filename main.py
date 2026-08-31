import logging

from config.logging_config import setup_logging
from config.settings import PROJECT_ROOT


def main():
    setup_logging()

    logger = logging.getLogger("aws-ai-league")

    logger.info("AWS AI League infrastructure initialized")
    logger.info(f"Project root: {PROJECT_ROOT}")

    print("\n⚽ AWS AI League - Agentic Football")
    print("Infrastructure ready!")
    print("Next: Building our first agent.\n")


if __name__ == "__main__":
    main()