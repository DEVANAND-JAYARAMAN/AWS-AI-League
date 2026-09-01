creating a Python virtual environment:

python -m venv .venv

Activate it using:

.venv\Scripts\Activate.ps1

Check the Python Version using this command: python --version
Upgrade the pip: python -m pip install --upgrade pip
Install the Strands: pip install strands-agents

## Strands Agent Architecture

The project keeps a fully deterministic football brain as the source of
truth, and layers a Strands-compatible agent interface on top of it.

```
Strands-Compatible Agent Layer      strands_agents/
        |                             (TacticalAgentAdapter,
        v                              SimulationAgentAdapter,
Tool Wrappers                          EvaluationAgentAdapter)
        |                            tools/tactical_tools.py
        v                            tools/simulation_tools.py
Deterministic Football Intelligence  tools/evaluation_tools.py
                                     -> AgentCoordinator / TeamCoordinator
                                     -> FootballSimulationEngine + dynamics
                                     -> MatchEvaluator
```

* The **agent layer** receives a `GameState` (object or serialized dict)
  and calls tools in a fixed order.
* The **tools** are thin wrappers - they add no football logic, they call
  the existing deterministic modules and return JSON-serializable dicts
  (see `utils/serialization.py`).
* The **deterministic system** is unchanged and remains authoritative.

### Step 36 status

```
Local
Deterministic
No Amazon Bedrock invocation
No AWS credentials required
No network calls
```

The adapters mirror the shape of a real `strands.Agent`
(receive input -> select/call tools -> structured result) but call the
tools directly instead of an LLM. Each adapter module contains a
commented `# Future integration point:` block.

### Future architecture

```
Strands Agent
        |
        v
Amazon Bedrock Model      <- added in a later step
        |
        v
Tool Selection            <- the LLM chooses which football tool to call
        |
        v
Existing Football Tools   <- tools/*_tools.py (unchanged)
        |
        v
Deterministic Simulation  <- still the source of truth
```

When Bedrock is connected, only the adapter classes change (swap the
fixed tool-call order for `strands.Agent(model=..., tools=[...])`); the
tools and the deterministic system stay exactly as they are.

