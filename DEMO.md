# Demo walk-through

A ~5-minute guided tour for a reviewer, a hackathon judge, or a first
read of the repo. Every step here is **offline and deterministic** unless
it explicitly says "needs AWS".

```powershell
# one-time setup
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

$env:PYTHONIOENCODING = "utf-8"   # Windows: lets the console print ⚽ / 📊
```

---

## 1. The deterministic brain works and is measured (~30s)

```powershell
python -m tests.test_core
python -m tests.test_agents
python -m tests.test_benchmark
```

`test_benchmark` runs 16 hand-designed tactical situations through the
**real** `AgentCoordinator` and prints:

```
Total Scenarios: 16
Passed: 16
Overall Accuracy: 100.0%

ATTACK      Passed: 5 / 5   Accuracy: 100.0%
DEFENSE     Passed: 5 / 5   Accuracy: 100.0%
GOALKEEPER  Passed: 3 / 3   Accuracy: 100.0%
TRANSITION  Passed: 3 / 3   Accuracy: 100.0%
```

This is the baseline a future LLM layer is scored against.

---

## 2. Run one full match (~15s)

```powershell
python -m scripts.run_hybrid_match create_midfielder_pass_scenario 8
```

Prints a replayable timeline …

```
MATCH START

Tick 1
Midfielder -> PASS
Ball: (60, 40) -> (82, 50)

Tick 2
Striker -> SHOOT
Ball: (82, 50) -> (100, 50)
...
MATCH END
```

… then an aggregated analytics report (actions, tactical modes, AI usage,
agreement, ball/'team distance moved), and saves the full event log JSON
under `data/match_results/`.

Try other scenarios: `create_shooting_scenario`,
`create_defensive_scenario`, `create_goalkeeper_emergency_scenario`
(all factories in `app/core/sample_scenario.py`).

---

## 3. Everything, in one command (~30s)

```powershell
python -m scripts.run_full_demo
```

Runs the four offline test suites, the benchmark, and a deterministic
match for several scenarios, then writes a single consolidated
[`RESULTS.md`](RESULTS.md) (committed in the repo as a reference of the
exact expected output). Exit code is non-zero if anything fails.

---

## 4. Do it visually — the dashboard (~2 min)

```powershell
streamlit run ui/app.py
```

0. Expand **System architecture** at the top for the live pipeline
   diagram (deterministic path + the opt-in Amazon Nova Pro branch).
1. Sidebar → **Scenario: Midfielder Pass**, **Mode: DETERMINISTIC_ONLY**,
   **Ticks: 8** → **Run simulation**.
2. **Match status** cards show the final tactical mode / agent / action /
   confidence.
3. **Football pitch** – drag the **Tick** slider from `0` (initial state)
   to `8`. Players (blue `GK/DF/MF/ST`), opponents (grey), and the ball
   (white dot) move between the stored snapshots; a dashed yellow arrow
   shows the ball movement for the selected tick.
4. **Selected-tick panel** updates: mode, `agent → action`, confidence,
   decision source, agreement.
5. **Agent status**, **timeline**, and **analytics** update alongside.

### Hybrid mode (needs AWS credentials + Amazon Nova Pro access)

Switch **Mode** to **HYBRID** and re-run. Now each tick also shows:

* **Deterministic engine** vs **Amazon Nova Pro** vs **Hybrid final
  decision**, side by side
* **Agreement** (`FULL` / `PARTIAL` / `DISAGREEMENT`) and
  **decision source** for that tick
* if Nova was skipped for a tick, the reason why

Tick navigation still never calls AWS — the Nova calls happen once, only
while the simulation is running.

---

## What to look at in the code

| You want to see… | Open |
|---|---|
| how one role decides | `app/agents/striker.py` |
| how four decisions become one | `app/core/team_coordinator.py` |
| how a tick is simulated | `app/core/simulation.py` |
| how Nova Pro is prompted + validated | `app/ai/tactical_prompt.py`, `app/ai/response_parser.py` |
| how deterministic + Nova are merged | `app/ai/decision_resolver.py` |
| how a whole hybrid match runs | `app/ai/match_simulator.py` |
| the pitch rendering | `ui/pitch.py` |

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the one-page system diagram.
