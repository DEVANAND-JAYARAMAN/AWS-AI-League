"""
Generate a fine-tuning dataset from the deterministic football brain.

    python -m scripts.generate_finetuning_dataset [--size N] [--seed S]
                                                   [--format sagemaker|generic]
                                                   [--out DIR]

Produces (under data/fine_tuning/ by default):

    train.jsonl
    validation.jsonl
    test.jsonl
    dataset_stats.json

Every label is produced by the existing AgentCoordinator / TeamCoordinator
pipeline. No AWS calls, no training - just files on disk. Fully
deterministic for a given --size and --seed.
"""

import argparse
import sys

from app.fine_tuning.config import DatasetConfig
from app.fine_tuning.dataset_builder import build_dataset
from app.fine_tuning.validation import format_statistics


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a football tactical fine-tuning dataset."
    )
    parser.add_argument(
        "--size", type=int, default=None,
        help="Total number of examples (default: DATASET_SIZE env or 100).",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="RNG seed for augmentation + split (default: DATASET_SEED env or 42).",
    )
    parser.add_argument(
        "--format", choices=["sagemaker", "generic"], default="sagemaker",
        help="Output record format (default: sagemaker conversational).",
    )
    parser.add_argument(
        "--out", type=str, default=None,
        help="Output directory (default: data/fine_tuning).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    config = DatasetConfig.from_env()
    if args.size is not None:
        config.dataset_size = args.size
    if args.seed is not None:
        config.seed = args.seed
        config.split.seed = args.seed
    if args.out is not None:
        from pathlib import Path
        config.output_dir = Path(args.out)

    try:
        config.validate()
    except ValueError as exc:
        print(f"Invalid configuration: {exc}", file=sys.stderr)
        return 2

    result = build_dataset(config, fmt=args.format, write=True)

    report = result.validation_report
    print("=" * 60)
    print("FINE-TUNING DATASET GENERATION")
    print("=" * 60)
    print(f"Requested size : {config.dataset_size}")
    print(f"Seed           : {config.seed}")
    print(f"Format         : {args.format}")
    print(f"Output dir     : {result.output_dir}")
    print("")
    print(f"Validation     : {report.valid} valid / {report.invalid} invalid "
          f"of {report.total}")
    if report.invalid:
        print("  Rejected examples:")
        for idx, errors in report.rejected[:10]:
            print(f"    [{idx}] {errors}")
    print("")
    print(format_statistics(result.stats))
    print("Files written:")
    for name, path in result.files.items():
        print(f"  {name}: {path}")
    print("")
    print("Reminder: this is a fine-tuning-READY dataset. No model has been "
          "trained and no accuracy improvement is claimed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
