# `app/fine_tuning/` — Model-customization / fine-tuning preparation layer

A **fine-tuning-ready** pipeline that turns the project's existing
deterministic football intelligence into a supervised fine-tuning dataset
for an **Amazon Nova** foundation model on **Amazon SageMaker AI**, plus an
evaluation framework to compare a customized model against the deterministic
baseline.

> **Status:** This is a *preparation* layer. **No model has been fine-tuned,
> no SageMaker training job has run, and no accuracy improvement is claimed.**
> The customized-model path reports `NOT RUN` until a real competition
> training run and evaluation are completed.

## Why this exists

The AWS AI League *"Customize a Foundational Model"* challenge is about
customizing/fine-tuning a Nova model with SageMaker AI for a domain-specific
task. This package makes the repository technically ready for that: it can
generate a dataset, validate it, split it, produce a SageMaker-ready
configuration template, and evaluate any model provider against the existing
16-scenario benchmark.

## Design rules (same invariants as the rest of the project)

1. **The deterministic engine is the source of truth.** Every training label
   is produced by the existing `AgentCoordinator` / `TeamCoordinator`
   pipeline. This package never re-implements or changes football logic and
   never invents labels by hand.
2. **Modular and independent.** Nothing in the deterministic core imports
   this package. Delete `app/fine_tuning/` and the existing system is
   untouched.
3. **No AWS money spent here.** This layer only prepares datasets and config.
   It never starts training, creates endpoints, or provisions infrastructure.
4. **No false claims.** Until a real training run + evaluation happen, the
   customized model reports `NOT RUN`.

## Architecture

```
GameState
   |
   v
Deterministic Football Intelligence   (AgentCoordinator -> TeamCoordinator)
   |
   v
Training Example Generator            example_generator.py
   |
   v
Fine-Tuning Dataset (train/val/test)  dataset_builder.py + validation.py
   |
   v
SageMaker AI Customization / Fine-Tuning   (prepare_sagemaker_job.py template)
   |
   v
Customized Foundation Model
   |
   v
Inference Adapter                     custom_model_client.py (ModelProvider)
   |
   v
Structured Tactical Recommendation
   |
   v
Existing Evaluation Benchmark         evaluation.py (reuses the 16 scenarios)
   |
   v
Comparison vs deterministic baseline
```

## Modules

| File | Responsibility |
|---|---|
| `dataset_schema.py` | `TrainingExample` / `TrainingInput` / `TrainingOutput`; allowed actions/modes pulled from the real enums. |
| `config.py` | `DatasetConfig`, `SplitConfig`, `SageMakerConfig` (placeholders); env overrides (`DATASET_SIZE`, `DATASET_SEED`, ...). |
| `example_generator.py` | `GameState -> deterministic decision -> TrainingExample`; deterministic seeded augmentation. |
| `validation.py` | Per-example validation, dataset validation, statistics report. |
| `dataset_builder.py` | Deterministic split, JSONL + SageMaker conversational serialization, file writing. |
| `custom_model_client.py` | `TacticalModelClient.analyze(game_state)` across `DETERMINISTIC` / `NOVA_BASE` / `NOVA_CUSTOM`. |
| `evaluation.py` | Runs the 16-scenario benchmark against any provider; `NOT RUN` when unavailable; multi-provider comparison report. |

## Commands

```powershell
# Generate a dataset (train/validation/test + dataset_stats.json)
python -m scripts.generate_finetuning_dataset --size 100

# Validate a generated dataset
python -m scripts.validate_finetuning_dataset

# Produce a SageMaker AI job config template (placeholders only, no AWS calls)
python -m scripts.prepare_sagemaker_job

# Evaluate providers against the benchmark (custom model reports NOT RUN
# until a real customized model id is supplied)
python -m scripts.evaluate_custom_model
```

Default output: `data/fine_tuning/{train,validation,test}.jsonl` +
`dataset_stats.json`. A small committed example lives in
`data/fine_tuning/example/`.

## What still depends on the official competition instructions

- The exact Nova base model id to customize (not assumed to be Nova Pro).
- The exact SageMaker AI training method and dataset IO format.
- Hyperparameters.
- The Workshop Studio environment specifics and IAM/role wiring.

All of these are configurable placeholders in `config.py` /
`prepare_sagemaker_job.py`.
