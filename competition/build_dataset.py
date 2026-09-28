"""
Turn a simple, human-editable source file of question/answer pairs into a
validated Nova fine-tuning dataset (``dataset.jsonl``), ready to upload in
Module 1 of the workshop.

USAGE
-----
    # 1. Build + validate from a source file:
    python -m competition.build_dataset --source competition/data/qa_source.json

    # 2. Just validate an existing .jsonl (e.g. one you were handed):
    python -m competition.build_dataset --check competition/data/dataset.jsonl

SOURCE FILE FORMAT
------------------
A JSON file like this (see competition/data/qa_source.json for a live example)::

    {
      "system_prompt": "You are a concise, helpful assistant.",
      "pairs": [
        {"question": "…", "answer": "…"},
        {"question": "…", "answer": "…"}
      ]
    }

``system_prompt`` is optional. Remember: the leaderboard sends only the
question at scoring time, so the system prompt is NOT present during
evaluation. Keep it short or omit it, and make sure the behaviour you want
scored is demonstrated in the answers themselves.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from competition.format import QAPair, build_records, write_jsonl
from competition.validate import validate_file, validate_records

DEFAULT_SOURCE = Path("competition/data/qa_source.json")
DEFAULT_OUTPUT = Path("competition/data/dataset.jsonl")


def load_source(path: Path) -> tuple[str | None, List[QAPair]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    system_prompt = data.get("system_prompt") or None
    raw_pairs = data.get("pairs", [])
    pairs: List[QAPair] = []
    for i, item in enumerate(raw_pairs):
        q = (item.get("question") or "").strip()
        a = (item.get("answer") or "").strip()
        if not q or not a:
            raise ValueError(
                f"pairs[{i}] is missing a question or answer: {item!r}"
            )
        pairs.append(QAPair(question=q, answer=a))
    return system_prompt, pairs


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build + validate a Nova fine-tuning dataset from Q/A pairs."
    )
    parser.add_argument(
        "--source",
        type=str,
        default=str(DEFAULT_SOURCE),
        help=f"Q/A source JSON file (default: {DEFAULT_SOURCE}).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help=f"Output .jsonl path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--check",
        type=str,
        default=None,
        help="Validate an existing .jsonl file and exit (skips building).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    # --- check-only mode -------------------------------------------------
    if args.check:
        report = validate_file(args.check)
        print(report.summary())
        return 0 if report.ok else 1

    # --- build mode ------------------------------------------------------
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Source file not found: {source_path}", file=sys.stderr)
        print(
            "Create it (see competition/data/qa_source.json for the format), "
            "or pass --source <path>.",
            file=sys.stderr,
        )
        return 1

    system_prompt, pairs = load_source(source_path)
    records = build_records(pairs, system_prompt)

    out_path = write_jsonl(records, args.out)

    print("=" * 60)
    print("DATASET BUILT")
    print("=" * 60)
    print(f"Source:  {source_path}")
    print(f"Output:  {out_path}")
    print(f"Records: {len(records)}")
    print(f"System prompt: {'set' if system_prompt else '(none)'}")
    print("")

    # Validate what we just wrote, from disk, so the check is honest.
    report = validate_file(out_path)
    print(report.summary())

    # A non-zero exit if the dataset is not upload-ready (or below the
    # 100-record floor, which would fail training).
    blocking = (not report.ok) or bool(report.warnings and len(records) < 100)
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
