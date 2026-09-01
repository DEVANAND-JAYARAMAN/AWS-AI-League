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

## Evaluation Benchmark

A local, deterministic benchmark that measures the tactical intelligence
of the existing football system across a library of predefined
scenarios.

```
Predefined Football Scenarios   scenarios/
        |
        v
Agent Decisions                 AgentCoordinator -> coordinate_team_decision
        |                        (existing pipeline, unchanged)
        v
Expected vs Actual Comparison   evaluation/benchmark_runner.py
        |
        v
PASS / FAIL
        |
        v
Accuracy Metrics                overall + per-category (passed / total * 100)
```

The benchmark currently evaluates four categories:

* **Attack**     - shooting, forward passing, movement, holding under pressure
* **Defense**    - pressing, covering, defensive support
* **Goalkeeper** - holding the line, moving to cut the angle, emergency press
* **Transition** - the tactical mode derived from a change of possession

Each scenario (`scenarios/scenario_models.py`) is judged in one of two
modes:

* `PRIMARY`    - checks the team's primary agent / primary action.
* `INDIVIDUAL` - checks one specific agent's own decision. Used for the
  goalkeeper, which is rarely the team's *primary* decision because the
  TeamCoordinator uses tactical prioritization.

Scenarios can also assert the expected `tactical_mode`.

Run it:

```powershell
python -m evaluation.benchmark_runner   # prints the full report
python -m tests.test_benchmark          # runs the benchmark test suite
```

Expected outcomes describe what the current deterministic rules already
do - no agent behaviour was changed to make scenarios pass, and the
runner reuses the existing coordinator/agent pipeline rather than
duplicating any decision logic. The benchmark reports failures instead
of hiding them.

This creates a measurable, deterministic baseline **before** LLM-based
reasoning is introduced: once a Bedrock-backed agent layer is added, the
same scenario library can show whether it matches, beats, or regresses
against the deterministic system.

