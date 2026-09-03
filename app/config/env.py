"""
Common environment loader.

One place that reads ``.env`` (via python-dotenv) and exposes the values
the rest of the project needs. Import from here instead of calling
``os.getenv`` in scattered modules.

The deterministic football system does not require any of these - they
only matter once ``USE_BEDROCK`` is turned on.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

# Load .env if present; real environment variables always win.
load_dotenv(dotenv_path=ENV_FILE, override=False)


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# -- Feature flag -----------------------------------------------------------
USE_BEDROCK = _flag("USE_BEDROCK")

# -- AWS ------------------------------------------------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", "")
AWS_REGION = (
    os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"
)

# -- Amazon Bedrock -----------------------------------------------------
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "apac.amazon.nova-pro-v1:0"
)
BEDROCK_AGENT_ID = os.getenv("BEDROCK_AGENT_ID", "")
BEDROCK_AGENT_ALIAS_ID = os.getenv("BEDROCK_AGENT_ALIAS_ID", "")


def aws_credentials_present() -> bool:
    """True when both a key id and secret are set (placeholders count)."""

    return bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)


__all__ = [
    "USE_BEDROCK",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_REGION",
    "BEDROCK_MODEL_ID",
    "BEDROCK_AGENT_ID",
    "BEDROCK_AGENT_ALIAS_ID",
    "aws_credentials_present",
]
