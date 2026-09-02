# AWS AI League – Agentic Football

A small, **fully deterministic** multi-agent system that decides what a
football (soccer) team should do in any given moment of a match, then
simulates and scores the result.

The project is built so that a real LLM-driven agent layer (AWS Strands +
Amazon Bedrock) can be added *later* without rewriting the football
logic. Today everything runs **locally** with:

* no AWS account or credentials
* no Amazon Bedrock calls
* no API keys
* no network calls
* no randomness

Run it twice with the same input and you get exactly the same output.

---

## 1. The big picture

```
GameState  (where every player and the ball are, who has possession)
    |
    v
Specialized Agents        one decision per role
    |  GoalkeeperAgent / DefenderAgent / MidfielderAgent / StrikerAgent
    v
AgentCoordinator          collects all four decisions
    |
    v
TeamCoordinator           scores the decisions and picks ONE team action
    |  (tactical-mode aware: ATTACK / DEFENSE / TRANSITION)
    v
Simulation Engine         applies the action, advances all players one tick
    |
    v
Match History             the list of every tick
    |
    v
Match Evaluator           turns the history into readable metrics
```

On top of that sits a **local agent pipeline** (`strands_agents/`) that
mirrors the shape of a real Strands agent but calls the tools directly
instead of asking an LLM.

And on top of *that* sits the **Evaluation Benchmark** (`scenarios/` +
`evaluation/`) which checks the football brain against a library of
hand-designed situations.

---

## 2. Core concepts (read this first)

| Term | What it means |
|---|---|
| **`Position`** | An `(x, y)` point on the pitch. `x` runs 0–100 from our goal to the opponent goal; `y` runs 0–100 across the width. Defined in `simulation/game_state.py`. |
| **`Player`** | `player_id`, `role` (`GOALKEEPER` / `DEFENDER` / `MIDFIELDER` / `STRIKER`), and a `Position`. |
| **`GameState`** | The whole world at one instant: `ball_position`, `our_team` (list of `Player`), `opponent_team`, and `possession` (`"OUR_TEAM"` or `"OPPONENT_TEAM"`). |
| **`FootballAction`** | The five things an agent can decide to do: `PASS`, `SHOOT`, `PRESS`, `MOVE`, `HOLD_POSITION`. |
| **`FootballDecision`** | One agent's answer: an `action`, an optional `target_player_id`, an optional `target_position`, a `confidence` (0–1), and a plain-English `reason`. |
| **Tactical mode** | Derived from possession by the `TeamCoordinator`: we have the ball → `ATTACK`; opponent has the ball → `DEFENSE`; anything else → `TRANSITION`. |
| **`TeamDecision`** | The team-level result: the chosen `primary_agent`, `primary_action`, the `tactical_mode`, every individual `agent_decisions`, and any detected `conflicts`. |

### How the team picks ONE action

Each agent proposes a decision. The `TeamCoordinator`
(`simulation/team_coordinator.py`) gives every proposal a score:

```
final_score = action_priority(mode) + role_relevance_bonus + confidence * 10
```

* **`action_priority`** depends on the tactical mode. In `ATTACK`,
  `SHOOT` (100) beats `PASS` (80) beats `MOVE` (60)… In `DEFENSE`,
  `PRESS` (100) comes first. This term dominates, so a confident
  goalkeeper wanting to `HOLD_POSITION` can never outrank a striker
  `SHOOT` in attack.
* **`role_relevance_bonus`** is a small nudge (max 15) when a role does
  its natural job (striker shooting, defender pressing).
* **`confidence * 10`** only separates decisions that are otherwise
  equal – it can never jump a whole priority tier.

Ties are broken by a fixed per-mode role order, so the result is 100%
deterministic.

---

## 3. Project layout

```
agents/                  the football "brain"
  base_agent.py          BaseFootballAgent (abstract: .decide(game_state))
  goalkeeper_agent.py    one file per role, pure if/else rules
  defender_agent.py
  midfielder_agent.py
  striker_agent.py
  coordinator.py         AgentCoordinator: runs all four, then TeamCoordinator

simulation/              the deterministic world
  game_state.py          Position / Player / GameState
  decision.py            FootballAction / FootballDecision
  field.py               OUR_GOAL / OPPONENT_GOAL constants
  team_coordinator.py    the scoring model above -> TeamDecision
  tactical_analyzer.py   structured read of a GameState
  engine.py              FootballSimulationEngine: advance the state one tick
  dynamics.py            how non-deciding players drift each tick
  evaluator.py           MatchEvaluator: history -> metrics + report
  match_runner.py        convenience: scenario -> engine -> evaluate
  sample_scenario.py     hand-built GameStates used by tests & the benchmark

tools/                   thin JSON-friendly wrappers around the modules above
  tactical_tools.py      (no football logic of their own)
  simulation_tools.py
  evaluation_tools.py
  decision_tools.py      shared geometry helpers (distance, closest player…)

strands_agents/          local, LLM-free agent adapters
  tactical_agent.py      TacticalAgentAdapter
  simulation_agent.py    SimulationAgentAdapter
  evaluation_agent.py    EvaluationAgentAdapter

utils/
  serialization.py       domain objects <-> plain dicts

scenarios/               the benchmark scenario library  (see section 6)
evaluation/              the benchmark runner            (see section 6)
tests/                   one runnable file per area      (see section 7)
```

---

## 4. Setup

You need **Python 3.10+** (3.12 is used here).

```powershell
# 1. create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell on Windows

# 2. upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> The `strands-agents` package is only needed for the *future* Bedrock
> integration. Nothing in the current code imports it at runtime – the
> adapters in `strands_agents/` are plain Python.

### Environment file

```powershell
Copy-Item .env.example .env          # then edit .env
```

`.env` holds the AWS / Bedrock settings and is **git-ignored – never
commit it**. `config/env.py` is the single place that loads it (via
`python-dotenv`) and exposes the values:

```python
from config import env
env.USE_BEDROCK          # False by default -> pure local, no AWS calls
env.AWS_REGION
env.BEDROCK_MODEL_ID
```

The current deterministic system needs none of these; they only take
effect once `USE_BEDROCK=true` and the Bedrock agent layer is added.

### A note on emoji output on Windows

Some scripts print `⚽` / `📊`. If your console raises
`UnicodeEncodeError`, force UTF-8 first:

```powershell
$env:PYTHONIOENCODING = "utf-8"
```

---

## 5. Running things

Every module is runnable with `python -m <package>.<module>`.

```powershell
# See the team decision for a few sample situations
python -m tests.test_team_coordinator

# Run a full multi-tick simulation and print the evaluation report
python -m tests.test_simulation_engine

# Run the local Strands-style pipeline end to end
python -m tests.test_strands_pipeline

# Run the evaluation benchmark and print the full report
python -m evaluation.benchmark_runner
```

### Using the brain in your own code

```python
from agents.coordinator import AgentCoordinator
from simulation.sample_scenario import create_shooting_scenario

game_state = create_shooting_scenario()
team_decision = AgentCoordinator().get_coordinated_team_decision(game_state)

print(team_decision.tactical_mode)      # "ATTACK"
print(team_decision.primary_agent)      # "striker"
print(team_decision.primary_action)     # FootballAction.SHOOT
print(team_decision.reason)             # human-readable explanation
```

---

## 6. Evaluation Benchmark

**Goal:** automatically measure how tactically sensible the football
system is, across many predefined situations, deterministically.

```
Scenario Library         scenarios/*.py
      |
      v
Initial GameState        reuses simulation/sample_scenario.py
      |
      v
Expected Behaviour       what the CURRENT deterministic rules already do
      |
      v
Existing Pipeline        AgentCoordinator -> coordinate_team_decision
      |                  (NOT re-implemented – the real code is called)
      v
Actual Decision
      |
      v
Scenario Result          expected vs actual  ->  PASS / FAIL + reason
      |
      v
Benchmark Report         overall + per-category accuracy
```

### What a scenario looks like

`scenarios/scenario_models.py` defines a small, readable dataclass:

```python
Scenario(
    scenario_name="Clear Shooting Opportunity",
    category="ATTACK",                       # ATTACK / DEFENSE / GOALKEEPER / TRANSITION
    description="Striker is on the ball, close to goal, unmarked.",
    initial_game_state=create_shooting_scenario(),
    expected_primary_agent="striker",
    expected_primary_action="SHOOT",
    expected_tactical_mode="ATTACK",         # optional extra check
)
```

### Two ways a scenario is judged

| `evaluation_mode` | What it checks | Why it exists |
|---|---|---|
| `PRIMARY` (default) | the team's `primary_agent` + `primary_action` | the normal case |
| `INDIVIDUAL` | one named agent's *own* decision (`expected_individual_agent` / `expected_individual_action`) | the goalkeeper is **rarely** the team's primary decision now that the `TeamCoordinator` prioritises outfield actions – but the keeper can still be individually correct (e.g. `PRESS` in an emergency). We check it directly instead of weakening the coordinator. |

Any scenario may also assert `expected_tactical_mode` – this is the main
point of the **Transition** category.

### The four categories (16 scenarios total)

| Category | Count | Examples |
|---|---|---|
| **ATTACK** | 5 | Clear Shooting Opportunity, Open Forward Pass, Attacking Under Pressure, Striker Movement Opportunity, Build-Up Play |
| **DEFENSE** | 5 | Close Opponent Possession, Opponent Possession Far Away, Defensive Covering, Midfield Defensive Support, High Defensive Pressure |
| **GOALKEEPER** | 3 | Safe Ball Far From Goal, Opponent Attack Near Goal, Emergency Near Goal |
| **TRANSITION** | 3 | Our Team Regains Possession (→ ATTACK), Opponent Takes Possession (→ DEFENSE), Opponent Threat Near Goal (→ DEFENSE) |

### The report

`python -m evaluation.benchmark_runner` prints one block per scenario:

```
Scenario: Clear Shooting Opportunity
Category: ATTACK
Mode: PRIMARY

Expected:
  mode=ATTACK, agent=striker, action=SHOOT

Actual:
  mode=ATTACK, agent=striker, action=SHOOT

Result: PASS ✅
------------------------------------------------------------
```

…followed by a summary:

```
Total Scenarios: 16
Passed: 16
Failed: 0
Overall Accuracy: 100.0%

Category Results:
ATTACK      Passed: 5 / 5   Accuracy: 100.0%
DEFENSE     Passed: 5 / 5   Accuracy: 100.0%
GOALKEEPER  Passed: 3 / 3   Accuracy: 100.0%
TRANSITION  Passed: 3 / 3   Accuracy: 100.0%
```

Accuracy is always `passed / total * 100`, with a guard so an empty run
reports `0.0%` instead of crashing.

### Design rules the benchmark follows

* **Expected outcomes describe the existing rules.** No agent was
  changed to make a scenario pass. Where a situation turned out to
  behave differently than first guessed, the *expectation* was corrected
  to match the deterministic reality.
* **No duplicated logic.** The runner calls
  `AgentCoordinator.get_coordinated_team_decision` – the same code the
  simulation uses.
* **Failures are reported, not hidden.** `test_benchmark.py` includes a
  test that feeds a deliberately wrong expectation and confirms the
  runner marks it `FAIL`.
* **Deterministic.** Running the benchmark repeatedly produces byte-for-
  byte identical reports.

### Why this matters

This is a **measurable baseline taken before any LLM reasoning is
added**. Once a Bedrock-backed agent layer replaces the fixed rules, the
same 16 scenarios immediately show whether the LLM matches, beats, or
regresses against the deterministic system.

### Adding your own scenario

1. Open the file for the category, e.g. `scenarios/attacking_scenarios.py`.
2. Append a `Scenario(...)` to the list returned by `build_*_scenarios()`.
   Reuse a `GameState` from `simulation/sample_scenario.py` or build one
   inline with `GameState` / `Player` / `Position`.
3. Set the expectation to whatever the current rules actually produce
   (run the benchmark once to see).
4. `python -m tests.test_benchmark`.

---

## 7. Tests

There is no pytest requirement – each test file is a plain script with a
`main()` and can be run directly:

```powershell
python -m tests.test_team_prioritization    # TeamCoordinator scoring model
python -m tests.test_team_coordinator       # full agent -> team decision
python -m tests.test_goalkeeper_agent       # individual agent rules
python -m tests.test_defender_agent
python -m tests.test_midfielder_agent
python -m tests.test_striker_agent
python -m tests.test_simulation_engine      # multi-tick simulation
python -m tests.test_match_evaluator        # history -> metrics
python -m tests.test_strands_pipeline       # local Strands-style pipeline
python -m tests.test_benchmark              # the evaluation benchmark
```

One test is **not** in the deterministic suite because it makes a real
network call:

```powershell
python -m tests.test_bedrock_tactical_analyzer   # REAL Amazon Bedrock call
```

`test_benchmark.py` specifically verifies: at least 16 scenarios exist,
all four categories are present, every scenario yields a valid result,
the accuracy maths is correct, division-by-zero is handled, the output
is deterministic, and wrong expectations are caught as failures.

---

## 8. The local Strands agent pipeline

`strands_agents/` mimics a real `strands.Agent` (receive input → select
and call tools → return a structured result) but with a **fixed tool
call order** instead of an LLM.

```
Strands-Compatible Agent Layer      strands_agents/
        |                             TacticalAgentAdapter
        v                             SimulationAgentAdapter
Tool Wrappers                         EvaluationAgentAdapter
        |                            tools/tactical_tools.py
        v                            tools/simulation_tools.py
Deterministic Football Intelligence  tools/evaluation_tools.py
                                     -> AgentCoordinator / TeamCoordinator
                                     -> FootballSimulationEngine + dynamics
                                     -> MatchEvaluator
```

* The **adapters** accept a `GameState` (object *or* serialized dict).
* The **tools** add no football logic – they call the deterministic
  modules and return JSON-serializable dicts (`utils/serialization.py`).
* The **deterministic system** is authoritative and unchanged.

Each adapter has a commented `# Future integration point:` block showing
exactly where a Bedrock model would plug in.

---

## 9. Roadmap – where Bedrock fits later

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
Existing Football Tools   <- tools/*_tools.py  (unchanged)
        |
        v
Deterministic Simulation  <- still the source of truth
```

When Bedrock is connected, **only the adapter classes change** (swap the
fixed tool-call order for `strands.Agent(model=..., tools=[...])`). The
tools, the deterministic brain, and the benchmark stay exactly as they
are – and the benchmark becomes the yardstick for the new agent.

---

## 10. Amazon Nova Pro Integration (advisory)

The `llm/` package adds a **first, real** LLM tactical analysis on top of
the deterministic system, using **Amazon Nova Pro** through the Bedrock
**Converse API**. It is **advisory only** – it never mutates a
`GameState` and never replaces the deterministic engine.

```
GameState
    |
    v
Tactical Context Builder   llm/tactical_prompt.py  (reuses GameState, no new model)
    |
    v
Amazon Bedrock Converse    llm/bedrock_client.py   (boto3 "bedrock-runtime".converse)
    |
    v
Amazon Nova Pro            apac.amazon.nova-pro-v1:0  (APAC inference profile)
    |
    v
Structured Recommendation  strict JSON: tactical_mode / recommended_agent /
    |                       recommended_action / confidence / reason
    v
Validation Layer           llm/response_parser.py  -> TacticalRecommendation
    |
    v
Deterministic Football     unchanged – still the source of truth
Engine                     (the recommendation stops here for now)
```

### Package

| File | Role |
|---|---|
| `llm/bedrock_client.py` | `BedrockClient` – reusable `converse` wrapper. `invoke(messages, system=, max_tokens=500, temperature=0.2)` builds `inferenceConfig` (`maxTokens` / `temperature`), calls `client.converse(...)`, and returns the assistant text. Region + model id configurable via `AWS_REGION` / `BEDROCK_MODEL_ID`; defaults `ap-south-1` / `apac.amazon.nova-pro-v1:0`. Raises `BedrockInvocationError` with a clear message on failure. Logs model id, region, and success – never credentials. |
| `llm/tactical_prompt.py` | Turns a `GameState` into a compact football context (ball, possession, our/opponent players with role + position) plus a strict system instruction. Emits **Converse-format** messages. Allowed actions/modes are derived from the real `FootballAction` enum, not hardcoded. |
| `llm/response_parser.py` | `parse_recommendation(text, valid_agents=...)` – extracts JSON (tolerates code fences), validates every field: `tactical_mode` in `ATTACK/DEFENSE/TRANSITION`, `recommended_action` against the real `FootballAction` enum, `recommended_agent` against the **players in the current GameState**, `confidence` in `[0, 1]`, non-empty `reason`. Returns a `TacticalRecommendation` dataclass or raises `TacticalValidationError`. Never guesses a fallback. |
| `llm/llm_tactical_analyzer.py` | `LLMTacticalAnalyzer.analyze(game_state)` – ties the three together and passes the live player ids to the parser. Reusable from a future Strands agent. |
| `tests/test_bedrock_tactical_analyzer.py` | Runs the full pipeline against the *Clear Shooting Opportunity* scenario with a **real Bedrock Converse call**. Not in the regression suite. Fails clearly if AWS / Bedrock / Nova Pro access is unavailable. |

### Credentials & configuration

* **AWS credentials are never hardcoded and never stored in source.**
  `boto3` uses the **default credential provider chain** (`aws configure`
  / `aws sso login` / `~/.aws/credentials` / IAM role).
* No `.env` file is required. `.env` holds **no secrets** – only optional
  non-secret routing overrides, and the defaults already match:

  ```
  AWS_REGION=ap-south-1
  BEDROCK_MODEL_ID=apac.amazon.nova-pro-v1:0
  ```

* The Nova Pro inference profile must be enabled for your account in the
  Bedrock console for the region you use.

### Guarantees

* Nova Pro is **advisory**, not authoritative.
* The **deterministic engine remains the trusted baseline / source of
  truth** – agent behaviour, the benchmark scenarios, and their expected
  outputs are all unchanged.
* Nova recommendations are **validated before use** – anything outside
  the real `FootballAction` enum / tactical modes, or an agent not in the
  current GameState, is rejected by the parser.
* Future work will **score Nova recommendations against the evaluation
  benchmark** to see whether they match, beat, or regress against the
  deterministic system.

### Run it

```powershell
python -m tests.test_bedrock_tactical_analyzer   # real Nova Pro call
python -m tests.test_benchmark                   # deterministic baseline (unchanged)
```

---

## 11. Hybrid AI Decision Evaluation

The `hybrid/` package runs **both tactical brains on the same
GameState** and measures how much they agree. It changes nothing – it
only observes.

```
GameState
   │
   ├── Deterministic Multi-Agent System   AgentCoordinator -> TeamCoordinator
   │        └─> TeamDecision (mode / primary agent / primary action)
   │
   └── Amazon Nova Pro via Bedrock         llm/ (Converse API)
            │
            ▼
      Tactical Recommendation (mode / recommended agent / recommended action)
            │
            ▼
      Decision Comparison        hybrid/decision_comparator.py
            │
            ▼
      Agreement Metrics          full / partial / disagreement + %s
```

The project now compares three things head-to-head:

* **rule-based tactical intelligence** (per-role if/else agents)
* **agent coordination** (the mode-aware scoring in `TeamCoordinator`)
* **foundation-model reasoning** (Amazon Nova Pro)

### Agreement levels

| Level | Condition |
|---|---|
| `FULL_AGREEMENT` | tactical mode **and** agent **and** action all match |
| `PARTIAL_AGREEMENT` | tactical mode matches, but agent or action differs |
| `DISAGREEMENT` | tactical mode differs |

### Package

| File | Role |
|---|---|
| `hybrid/decision_comparator.py` | `compare(team_decision, recommendation) -> DecisionComparison` (read-only: mode / agent / action matches, confidences, `AgreementLevel`, `.differences()`). `summarize([...]) -> HybridEvaluationMetrics` with safe division. |
| `hybrid/hybrid_tactical_analyzer.py` | `HybridTacticalAnalyzer.analyze(game_state) -> DecisionComparison` and `.analyze_scenarios([(name, state), ...]) -> (results, metrics)`. Both brains get the same GameState; the GameState is never mutated. |
| `tests/test_hybrid_tactical_analyzer.py` | Real end-to-end run over *Clear Shooting Opportunity*, *Open Forward Pass*, *Defensive Pressure* with live Nova Pro calls, printing each comparison plus the summary. |

### Guarantees

* Nova Pro stays **advisory** – its recommendation is compared, never
  executed, and never used to overwrite a deterministic decision or
  mutate a GameState.
* If the Bedrock call fails, the error is raised – the comparator never
  fabricates an LLM answer or pretends the systems agree.
* The deterministic path is independent: `AgentCoordinator` and
  `tests/test_benchmark.py` still work with **no AWS credentials**.
* All agreement numbers are computed from real runs, not assumed.

### Run it

```powershell
python -m tests.test_hybrid_tactical_analyzer   # real Nova Pro calls (3 scenarios)
python -m tests.test_benchmark                  # deterministic baseline, no AWS
```

Example (numbers vary run to run – Nova Pro is not deterministic):

```
Total Scenarios: 3
Full Agreement: 1
Partial Agreement: 2
Disagreement: 0
Mode Agreement: 100.0%
Agent Agreement: 66.67%
Action Agreement: 33.33%
```

Mode agreement is consistently high (both systems read possession the
same way); action agreement is lower, which is exactly the kind of
signal this layer exists to surface. Future work will score these
comparisons against the evaluation benchmark.
