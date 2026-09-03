from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

APP_DIR = PROJECT_ROOT / "app"
AGENTS_DIR = APP_DIR / "agents"
CORE_DIR = APP_DIR / "core"
AI_DIR = APP_DIR / "ai"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DATA_DIR = PROJECT_ROOT / "data"
MATCH_RESULTS_DIR = DATA_DIR / "match_results"
LOGS_DIR = PROJECT_ROOT / "logs"

LOGS_DIR.mkdir(exist_ok=True)
MATCH_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
