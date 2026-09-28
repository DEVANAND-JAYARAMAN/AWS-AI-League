"""
Format question/answer pairs into the exact JSONL record shape Amazon Nova
fine-tuning expects: the ``bedrock-conversation-2024`` schema.

One record looks like this (pretty-printed; on disk it is a single line)::

    {
      "schemaVersion": "bedrock-conversation-2024",
      "system": [{"text": "<optional system prompt>"}],
      "messages": [
        {"role": "user",      "content": [{"text": "<the question>"}]},
        {"role": "assistant", "content": [{"text": "<the answer>"}]}
      ]
    }

Reminders that come straight from the workshop guide:

* The leaderboard sends ONLY the question at scoring time - no system prompt.
  So do not rely on the system prompt to carry information the answer needs.
  Any behaviour you want scored must be learnable from the user turn alone.
* SFT teaches behaviour (format, tone, structure, length, refusals), not
  facts. Write answers that model *how* to respond, consistently.
* ``system`` is optional. Keep it short or leave it out.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

SCHEMA_VERSION = "bedrock-conversation-2024"


@dataclass
class QAPair:
    """One training example: a question and the answer we want the model to give."""

    question: str
    answer: str


def build_record(
    question: str,
    answer: str,
    system_prompt: Optional[str] = None,
) -> dict:
    """
    Build one ``bedrock-conversation-2024`` record from a Q/A pair.

    ``system_prompt`` is optional. When provided, the identical string should
    be used on every record in the dataset (the validator enforces this).
    """

    record: dict = {"schemaVersion": SCHEMA_VERSION}

    if system_prompt:
        record["system"] = [{"text": system_prompt}]

    record["messages"] = [
        {"role": "user", "content": [{"text": question}]},
        {"role": "assistant", "content": [{"text": answer}]},
    ]
    return record


def build_records(
    pairs: Iterable[QAPair],
    system_prompt: Optional[str] = None,
) -> List[dict]:
    """Build a list of records from an iterable of :class:`QAPair`."""

    return [build_record(p.question, p.answer, system_prompt) for p in pairs]


def write_jsonl(records: List[dict], path: str | Path) -> Path:
    """
    Write records to a ``.jsonl`` file: one compact JSON object per line, no
    wrapping array, no blank lines, UTF-8. This is the exact shape the
    workshop's upload step expects.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False))
            fh.write("\n")
    return path


def read_jsonl(path: str | Path) -> List[dict]:
    """Read a ``.jsonl`` file back into a list of dicts (skips blank lines)."""

    path = Path(path)
    records: List[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
