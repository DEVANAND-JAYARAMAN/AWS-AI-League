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

from strands_agents.evaluation_agent import EvaluationAgentAdapter
from strands_agents.simulation_agent import SimulationAgentAdapter
from strands_agents.tactical_agent import TacticalAgentAdapter

__all__ = [
    "TacticalAgentAdapter",
    "SimulationAgentAdapter",
    "EvaluationAgentAdapter",
]
