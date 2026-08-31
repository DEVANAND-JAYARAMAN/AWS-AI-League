import logging
from config.settings import LOGS_DIR


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOGS_DIR / "aws_ai_league.log")
        ]
    )