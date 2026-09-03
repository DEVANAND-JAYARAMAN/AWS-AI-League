"""
Strands-compatible agent layer (Step 36).

LOCAL and DETERMINISTIC. These adapters expose the same shape a real
``strands.Agent`` would (receive input -> select/call tools -> return a
structured result), but they call the deterministic football tools
directly instead of an LLM.

No Amazon Bedrock. No AWS credentials. No network calls.

Future integration point:
    # from strands import Agent
    # tactical_agent = Agent(model=<bedrock model>, tools=[analyze_tactical_state, get_team_decision])
"""

from app.strands.evaluation_agent import EvaluationAgentAdapter
from app.strands.simulation_agent import SimulationAgentAdapter
from app.strands.tactical_agent import TacticalAgentAdapter

__all__ = [
    "TacticalAgentAdapter",
    "SimulationAgentAdapter",
    "EvaluationAgentAdapter",
]
