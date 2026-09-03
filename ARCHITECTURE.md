# Architecture

One-page overview of the Agentic Football Tactical AI. For the deep dive
on any component, follow the section links into [`README.md`](README.md).

> The diagrams below are [Mermaid](https://mermaid.js.org/) and render
> automatically on GitHub. The same picture is available live inside the
> Streamlit dashboard under **System architecture**.

---

## 1. System at a glance

```mermaid
flowchart LR
    GS[["GameState<br/>ball · possession · players"]]

    subgraph CORE["Deterministic core — no AWS, no network, no randomness"]
        direction TB
        GK[Goalkeeper]:::agent
        DF[Defender]:::agent
        MF[Midfielder]:::agent
        ST[Striker]:::agent
        COORD["AgentCoordinator<br/>+ TeamCoordinator<br/><i>mode-aware scoring</i>"]:::core
        GK --> COORD
        DF --> COORD
        MF --> COORD
        ST --> COORD
    end

    subgraph HYBRID["Optional hybrid layer — app/ai/ (opt-in)"]
        direction TB
        NOVA["Amazon Nova Pro<br/>via Amazon Bedrock (Converse)"]:::nova
        RES["Hybrid Decision Resolver<br/>AGREEMENT · HYBRID_RESOLUTION<br/>· DETERMINISTIC_FALLBACK"]:::resolver
        NOVA --> RES
    end

    SIM["FootballSimulationEngine<br/><i>apply action + dynamics → next tick</i>"]:::core
    EVAL[MatchEvaluator]:::out
    AN["Analytics<br/>event log · timeline · report"]:::out
    UI["Streamlit dashboard<br/>pitch + panels + charts"]:::ui

    GS --> GK & DF & MF & ST
    COORD -->|deterministic decision| RES
    COORD -.->|"DETERMINISTIC_ONLY<br/>(resolver + Nova skipped)"| SIM
    RES -->|one final TeamDecision| SIM
    SIM --> EVAL
    SIM --> AN --> UI

    classDef agent fill:#e8eef9,stroke:#8aa0c8;
    classDef core fill:#dbe5f6,stroke:#6f8ec7;
    classDef nova fill:#fde8cf,stroke:#e0a060;
    classDef resolver fill:#e4f1e4,stroke:#8ac08a;
    classDef out fill:#eee,stroke:#aaa;
    classDef ui fill:#f1e4f1,stroke:#c08ac0;
```

Two things sit beside the runtime rather than inside it:

* **`app/strands/`** – LLM-free adapters shaped like `strands.Agent`
  (input → tool calls → structured result). A future Bedrock agent swaps
  only the adapter classes; the tools and the deterministic brain do not
  change. (README §8–9)
* **`app/evaluation/`** – a 16-scenario benchmark that calls the real
  `AgentCoordinator` and reports PASS/FAIL + per-category accuracy. It is
  the yardstick a future LLM layer is measured against. (README §6)

---

## 2. One hybrid tick, step by step

```mermaid
sequenceDiagram
    autonumber
    participant Sim as HybridMatchSimulator
    participant Coord as AgentCoordinator
    participant Nova as Amazon Nova Pro (Bedrock)
    participant Cmp as compare()
    participant Res as HybridDecisionResolver
    participant Eng as FootballSimulationEngine

    Sim->>Coord: get_coordinated_team_decision(GameState_t)
    Coord-->>Sim: deterministic TeamDecision
    alt HYBRID / NOVA_ONLY mode
        Sim->>Nova: analyze(GameState_t)
        Nova-->>Sim: TacticalRecommendation (validated JSON)
        Note over Sim,Nova: on failure/invalid → skip, record nova_skip_reason
    end
    Sim->>Cmp: compare(TeamDecision, Recommendation)
    Cmp-->>Sim: DecisionComparison (agreement level)
    Sim->>Res: resolve(deterministic, nova, comparison)
    Res-->>Sim: HybridDecision (final mode / agent / action + source)
    Sim->>Eng: step(final TeamDecision)
    Eng-->>Sim: SimulationStepResult → GameState_t+1
```

`DETERMINISTIC_ONLY` mode skips steps 3–8 entirely and lets
`FootballSimulationEngine.step()` pick the decision itself.

---

## 3. How the final decision is chosen

```mermaid
flowchart TD
    A{Simulation mode} -->|DETERMINISTIC_ONLY| D1[engine executes<br/>TeamCoordinator decision]
    A -->|HYBRID / NOVA_ONLY| B{Nova call<br/>succeeded & valid?}
    B -->|no| D2["DETERMINISTIC_FALLBACK<br/>keep deterministic decision"]
    B -->|yes| C{Agreement level}
    C -->|FULL_AGREEMENT| E1["AGREEMENT<br/>shared decision, confidence nudged up"]
    C -->|PARTIAL_AGREEMENT| E2["HYBRID_RESOLUTION<br/>higher tactical-action priority wins<br/>(TeamCoordinator priority tables)"]
    C -->|DISAGREEMENT| E3["DETERMINISTIC_FALLBACK<br/>modes conflict → deterministic baseline,<br/>Nova view kept in reason"]
    E1 --> V{Passes defensive<br/>re-validation?}
    E2 --> V
    V -->|no| D2
    V -->|yes| F[execute final decision]
    D1 --> F
    E3 --> F
    D2 --> F
```

Deterministic and reproducible: identical inputs always give an identical
`HybridDecision`. Only the live Nova Pro response itself varies run to run.

---

## 4. Components

| Package | Responsibility | AWS? | README |
|---|---|---|---|
| `app/core/game_state.py`, `decisions.py`, `field.py` | domain model: `Position` / `Player` / `GameState` / `FootballAction` / `FootballDecision` | no | §2 |
| `app/agents/` | one deterministic if/else agent per role + `AgentCoordinator` | no | §3 |
| `app/core/team_coordinator.py` | scoring model → single `TeamDecision` (`action_priority + role_bonus + confidence*10`) | no | §2 |
| `app/core/simulation.py`, `dynamics.py` | advance the world one tick; `step(team_decision=None)` executes an external decision when given one | no | §11 |
| `app/core/evaluator.py`, `match_runner.py` | match history → readable metrics | no | §1 |
| `app/ai/bedrock_client.py`, `tactical_prompt.py`, `response_parser.py`, `bedrock_nova.py` | GameState → Converse prompt → Nova Pro → **validated** `TacticalRecommendation` | **yes** | §10 |
| `app/ai/decision_comparator.py`, `hybrid_analyzer.py` | deterministic vs Nova agreement metrics (read-only) | yes | §11 |
| `app/ai/decision_resolver.py` | merge deterministic + Nova → one `HybridDecision`; deterministic + reproducible | no | §11 |
| `app/ai/match_simulator.py` | `HybridMatchSimulator`: tick-by-tick match in a `SimulationMode`; per-tick fallback; `statistics` | mode-dependent | §11 |
| `app/analytics/` | `build_event_log` / `format_timeline` / `analyze` / `format_analytics` – read-only, deterministic | no | §12 |
| `app/strands/` | LLM-free Strands-style adapters + tool wrappers | no | §8 |
| `app/evaluation/` | benchmark runner + scenario library | no | §6 |
| `ui/app.py`, `ui/pitch.py` | Streamlit dashboard + pure-SVG pitch renderer; thin presentation layer over the packages above | UI opt-in | §5 |

---

## 5. Design invariants

1. **The deterministic core is the source of truth.** Nova Pro is
   advisory. Agent rules, benchmark scenarios, and their expected
   outputs are never changed to accommodate the LLM.
2. **Opt-in AWS.** Nothing calls Bedrock unless a hybrid `SimulationMode`
   (or a live-Nova test) is explicitly selected. Every hybrid path has a
   deterministic fallback (`decision_source = DETERMINISTIC_FALLBACK`).
3. **No duplicated logic.** The benchmark, the analytics, the Strands
   adapters, and the UI all *call* the existing modules; they never
   re-implement tactical, simulation, or scoring behaviour.
4. **Determinism.** Same input → byte-identical output for the whole
   core, the benchmark, and the analytics. Only live Nova Pro responses
   vary.
5. **Validation before use.** Nova output outside the real
   `FootballAction` enum / tactical modes, or naming a player absent from
   the current `GameState`, is rejected by the parser.
6. **The UI only reads results.** Running a match is the one action that
   executes the pipeline; tick navigation replays stored `GameState`
   snapshots and never triggers a simulation or an AWS call.
