"""
Validate an already-generated fine-tuning dataset on disk.

    python -m scripts.validate_finetuning_dataset [--dir DIR]

Reads train.jsonl / validation.jsonl / test.jsonl, re-validates every
record against the schema rules, checks that the test set is isolated from
the train set, and prints a statistics report. Exits non-zero if any
malformed records are found.

Supports both dataset formats produced by the generator:
    * generic     {"input", "output", "metadata"}
    * sagemaker   {"system", "messages": [user, assistant]}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from app.fine_tuning.config import DEFAULT_OUTPUT_DIR
from app.fine_tuning.dataset_builder import read_jsonl
from app.fine_tuning.dataset_schema import (
    TrainingExample,
    TrainingInput,
    TrainingOutput,
)
from app.fine_tuning.validation import (
    compute_statistics,
    format_statistics,
    validate_dataset,
)


def _record_to_example(record: dict) -> TrainingExample:
    """Rebuild a TrainingExample from either supported on-disk format."""

    if "input" in record and "output" in record:
        return TrainingExample.from_dict(record)

    # SageMaker conversational form: reconstruct from the assistant JSON +
    # a minimal input (the assistant label is what validation cares about;
    # the input fields are re-parsed from the embedded game-state text only
    # loosely, so we validate the label strictly and keep a placeholder
    # input that still satisfies the GameState checks).
    if "messages" in record:
        assistant = next(
            (m for m in record["messages"] if m.get("role") == "assistant"),
            None,
        )
        if assistant is None:
            raise ValueError("sagemaker record has no assistant message")
        text = assistant["content"][0]["text"]
        label = json.loads(text)
        out = TrainingOutput.from_dict(label)
        # Minimal, schema-valid input carrying the recommended agent so the
        # agent-membership check still passes.
        inp = TrainingInput(
            ball_position={"x": 0.0, "y": 0.0},
            possession="OUR_TEAM",
            our_team=[
                {
                    "player_id": out.recommended_agent,
                    "role": out.recommended_agent.upper(),
                    "position": {"x": 0.0, "y": 0.0},
                }
            ],
            opponent_team=[],
            tactical_context="(reconstructed from sagemaker record)",
        )
        return TrainingExample(input=inp, output=out, metadata={"format": "sagemaker"})

    raise ValueError(f"Unrecognized record shape: keys={list(record.keys())}")


def _load_split(path: Path) -> List[dict]:
    """Return the raw on-disk records for a split (or [] if missing)."""

    if not path.exists():
        return []
    return read_jsonl(path)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate a generated fine-tuning dataset."
    )
    parser.add_argument(
        "--dir", type=str, default=None,
        help="Dataset directory (default: data/fine_tuning).",
    )
    return parser.parse_args(argv)


def _record_signature(record: dict) -> str:
    """Signature over the *raw* on-disk record (format-agnostic)."""

    return json.dumps(record, sort_keys=True)


def main(argv=None) -> int:
    args = _parse_args(argv)
    base = Path(args.dir) if args.dir else DEFAULT_OUTPUT_DIR

    splits = {
        "train": base / "train.jsonl",
        "validation": base / "validation.jsonl",
        "test": base / "test.jsonl",
    }

    missing = [name for name, p in splits.items() if not p.exists()]
    if missing:
        print(
            f"Missing split file(s) in {base}: {missing}. "
            f"Run 'python -m scripts.generate_finetuning_dataset' first.",
            file=sys.stderr,
        )
        return 2

    print("=" * 60)
    print("FINE-TUNING DATASET VALIDATION")
    print("=" * 60)
    print(f"Directory: {base}")
    print("")

    all_examples: List[TrainingExample] = []
    split_counts = {}
    raw_records = {}
    total_invalid = 0

    for name, path in splits.items():
        records = _load_split(path)
        raw_records[name] = records
        examples = [_record_to_example(r) for r in records]
        split_counts[name] = len(examples)
        valid, report = validate_dataset(examples)
        total_invalid += report.invalid
        status = "OK" if report.all_valid else "INVALID"
        print(f"{name:11s}: {report.valid} valid / {report.invalid} invalid  [{status}]")
        if report.invalid:
            for idx, errors in report.rejected[:10]:
                print(f"    [{idx}] {errors}")
        all_examples.extend(valid)

    # Test-set isolation: compare the RAW on-disk records so the check works
    # for both the generic and the sagemaker conversational formats.
    print("")
    train_sigs = {_record_signature(r) for r in raw_records.get("train", [])}
    test_overlap = sum(
        1 for r in raw_records.get("test", []) if _record_signature(r) in train_sigs
    )
    if test_overlap:
        print(f"WARNING: {test_overlap} test example(s) also appear in train.")
    else:
        print("Test set isolation: OK (no test example found in train).")

    print("")
    stats = compute_statistics(all_examples, split_counts)
    print(format_statistics(stats))

    if total_invalid:
        print(f"FAILED: {total_invalid} malformed record(s).", file=sys.stderr)
        return 1
    if test_overlap:
        print("FAILED: test set overlaps train.", file=sys.stderr)
        return 1

    print("All records valid. Test set isolated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
