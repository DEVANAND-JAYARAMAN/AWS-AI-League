"""
Entry point for the Agentic Football system.

Runs the fully deterministic evaluation benchmark (no AWS / Bedrock
required) and prints the report.
"""

from app.config.logging_config import setup_logging
from app.evaluation import format_report, run_benchmark


def main():
    setup_logging()
    report = run_benchmark()
    print(format_report(report))


if __name__ == "__main__":
    main()
