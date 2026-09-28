# Example / development fine-tuning dataset

> **This is a small EXAMPLE / development dataset — NOT the final
> competition dataset.** It exists for documentation, tests, and local
> development only. No model has been trained on it and no accuracy claim is
> attached to it.

## What this is

24 supervised fine-tuning examples generated from the project's real
football scenarios. Every label was produced by the existing deterministic
brain (`AgentCoordinator` / `TeamCoordinator`), not written by hand.

- `example_train.jsonl` (18) — training split
- `example_validation.jsonl` (3) — validation split
- `example_test.jsonl` (3) — held-out test split (isolated from train)
- `example_dataset_stats.json` — statistics report

Format: the generic `{"input", "output", "metadata"}` shape (human-readable).
The full pipeline can also emit a SageMaker-style conversational format —
see `app/fine_tuning/README.md`.

## Reproduce

```powershell
# The committed files here were generated deterministically with seed 42.
# A full development dataset (SageMaker format) goes to data/fine_tuning/:
python -m scripts.generate_finetuning_dataset --size 120
python -m scripts.validate_finetuning_dataset
```

## Record shape

```json
{
  "input": {
    "ball_position": {"x": 82, "y": 50},
    "possession": "OUR_TEAM",
    "our_team": [{"player_id": "striker", "role": "STRIKER", "position": {"x": 82, "y": 50}}],
    "opponent_team": [],
    "tactical_context": "Striker is close to the opponent goal, on the ball, and free of pressure."
  },
  "output": {
    "tactical_mode": "ATTACK",
    "recommended_agent": "striker",
    "recommended_action": "SHOOT",
    "confidence": 0.9,
    "reason": "..."
  },
  "metadata": {"source_scenario": "Clear Shooting Opportunity", "category": "ATTACK", "augmented": false}
}
```
