"""
Build, split, and write fine-tuning datasets.

Responsibilities:

    * deterministic train / validation / test split (fixed seed; the test
      set is always isolated from training)
    * serialize examples to JSONL, both in
        - a generic ``{"input": ..., "output": ...}`` form (our own tooling)
        - a SageMaker-style *conversational* form
          (``{"system", "messages": [user, assistant]}``) that mirrors the
          Bedrock Converse shape the project already uses
    * write ``train.jsonl`` / ``validation.jsonl`` / ``test.jsonl`` plus a
      ``dataset_stats.json`` report to an output directory

No AWS calls. No training. Just files on disk.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.ai.tactical_prompt import SYSTEM_PROMPT, build_football_context
from app.core.game_state import GameState, Player, Position

from app.fine_tuning.config import DatasetConfig, SplitConfig
from app.fine_tuning.dataset_schema import TrainingExample
from app.fine_tuning.example_generator import generate_examples
from app.fine_tuning.validation import (
    ValidationReport,
    compute_statistics,
    validate_dataset,
)


# ----------------------------------------------------------------------
# Split
# ----------------------------------------------------------------------

@dataclass
class DatasetSplit:
    train: List[TrainingExample]
    validation: List[TrainingExample]
    test: List[TrainingExample]

    def counts(self) -> Dict[str, int]:
        return {
            "train": len(self.train),
            "validation": len(self.validation),
            "test": len(self.test),
        }


def split_dataset(
    examples: List[TrainingExample],
    split: Optional[SplitConfig] = None,
) -> DatasetSplit:
    """
    Deterministically shuffle (fixed seed) and partition into
    train / validation / test.

    The split is reproducible for a given seed and input order, and the
    test set never overlaps with train or validation.
    """

    split = split or SplitConfig()
    split.validate()

    ordered = list(examples)
    rng = random.Random(split.seed)
    rng.shuffle(ordered)

    total = len(ordered)
    n_train = int(total * split.train_ratio)
    n_val = int(total * split.val_ratio)
    # test gets the remainder so the three always sum to total
    train = ordered[:n_train]
    validation = ordered[n_train : n_train + n_val]
    test = ordered[n_train + n_val :]

    return DatasetSplit(train=train, validation=validation, test=test)


# ----------------------------------------------------------------------
# Serialization: generic + SageMaker conversational
# ----------------------------------------------------------------------

def _input_to_game_state(training_input) -> GameState:
    """Rebuild a GameState from a TrainingInput so we can reuse the project's
    own prompt/context builder for the SageMaker record."""

    def _players(team: List[Dict[str, Any]]) -> List[Player]:
        players = []
        for p in team:
            pos = p.get("position") or {}
            players.append(
                Player(
                    player_id=p.get("player_id", ""),
                    role=p.get("role", ""),
                    position=Position(x=pos.get("x", 0.0), y=pos.get("y", 0.0)),
                )
            )
        return players

    ball = training_input.ball_position or {}
    return GameState(
        ball_position=Position(x=ball.get("x", 0.0), y=ball.get("y", 0.0)),
        our_team=_players(training_input.our_team),
        opponent_team=_players(training_input.opponent_team),
        possession=training_input.possession,
    )


def example_to_sagemaker_record(example: TrainingExample) -> Dict[str, Any]:
    """
    Convert one example into a SageMaker-style conversational record that
    matches the Bedrock Converse shape the project already speaks:

        {
          "system":   [{"text": <SYSTEM_PROMPT>}],
          "messages": [
            {"role": "user",      "content": [{"text": <situation prompt>}]},
            {"role": "assistant", "content": [{"text": <JSON label>}]}
          ]
        }

    The exact required schema is competition-specific; this mirrors the
    existing Converse format and is easy to remap when the official format
    is published.
    """

    game_state = _input_to_game_state(example.input)
    context = build_football_context(game_state)
    our_players = ", ".join(p["player_id"] for p in example.input.our_team) or "(none)"

    user_text = (
        "Current game state:\n\n"
        f"{context}\n\n"
        f"Tactical context: {example.input.tactical_context}\n\n"
        f"Our players you may recommend: {our_players}\n\n"
        "Give your single tactical recommendation as JSON only."
    )

    assistant_text = json.dumps(example.output.to_dict())

    return {
        "system": [{"text": SYSTEM_PROMPT}],
        "messages": [
            {"role": "user", "content": [{"text": user_text}]},
            {"role": "assistant", "content": [{"text": assistant_text}]},
        ],
    }


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False))
            fh.write("\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ----------------------------------------------------------------------
# End-to-end build
# ----------------------------------------------------------------------

@dataclass
class BuildResult:
    output_dir: Path
    split: DatasetSplit
    validation_report: ValidationReport
    stats: Dict[str, Any]
    files: Dict[str, Path]


def build_dataset(
    config: Optional[DatasetConfig] = None,
    *,
    fmt: str = "sagemaker",
    write: bool = True,
) -> BuildResult:
    """
    Generate -> validate -> split -> (optionally) write a dataset.

    ``fmt``:
        "sagemaker"  conversational records (default; SageMaker-ready)
        "generic"    the raw {"input", "output", "metadata"} form

    Returns a :class:`BuildResult` describing everything produced.
    """

    config = config or DatasetConfig()
    config.validate()

    examples = generate_examples(
        config.dataset_size,
        seed=config.seed,
        position_jitter=config.position_jitter,
        coordinator=None,
    )

    valid_examples, validation_report = validate_dataset(examples)

    split = split_dataset(valid_examples, config.split)
    stats = compute_statistics(valid_examples, split.counts())

    output_dir = Path(config.output_dir)
    files: Dict[str, Path] = {}

    if write:
        for name, subset in (
            ("train", split.train),
            ("validation", split.validation),
            ("test", split.test),
        ):
            rows = [_render(ex, fmt) for ex in subset]
            path = output_dir / f"{name}.jsonl"
            _write_jsonl(path, rows)
            files[name] = path

        stats_path = output_dir / "dataset_stats.json"
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(
            json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        files["stats"] = stats_path

    return BuildResult(
        output_dir=output_dir,
        split=split,
        validation_report=validation_report,
        stats=stats,
        files=files,
    )


def _render(example: TrainingExample, fmt: str) -> Dict[str, Any]:
    if fmt == "sagemaker":
        return example_to_sagemaker_record(example)
    if fmt == "generic":
        return example.to_dict()
    raise ValueError(f"Unknown format '{fmt}'. Use 'sagemaker' or 'generic'.")
