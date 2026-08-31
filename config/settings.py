from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

AGENTS_DIR = PROJECT_ROOT / "agents"
TOOLS_DIR = PROJECT_ROOT / "tools"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
SIMULATION_DIR = PROJECT_ROOT / "simulation"
LOGS_DIR = PROJECT_ROOT / "logs"

LOGS_DIR.mkdir(exist_ok=True)