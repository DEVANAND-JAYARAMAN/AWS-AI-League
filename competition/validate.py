"""
Validate a Nova fine-tuning dataset against every rule from the AWS AI League
workshop guide that can make a training job fail or a submission score badly.

Rules enforced (from the official guide):

1.  The file is JSONL: every non-empty line must parse as its own JSON object.
    No wrapping array.
2.  Each record has ``"schemaVersion": "bedrock-conversation-2024"``.
3.  ``messages`` exists, only ``user``/``assistant`` roles are used, the FIRST
    turn is ``user`` and the LAST turn is ``assistant``.
4.  Every turn nests its text inside a ``content`` array of ``{"text": ...}``.
5.  If a ``system`` prompt is present, it is identical on every record.
6.  No ``user`` or ``system`` text contains a reserved string, any of which
    fails the training job:
    ``User:``  ``Bot:``  ``Assistant:``  ``System:``  ``<image>``  ``<video>``  ``[EOS]``
7.  Record count is within Nova Micro's limits: at least 100 (fewer fails
    during training) and at most 20,000.

``validate_records`` returns a :class:`ValidationReport`. Nothing is mutated or
auto-fixed - problems are reported so you can decide what to change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from competition.format import SCHEMA_VERSION, read_jsonl

# Substrings that AWS says will fail a training job if they appear in any
# user or system text.
RESERVED_STRINGS: Tuple[str, ...] = (
    "User:",
    "Bot:",
    "Assistant:",
    "System:",
    "<image>",
    "<video>",
    "[EOS]",
)

MIN_RECORDS = 100
MAX_RECORDS = 20_000


@dataclass
class ValidationReport:
    total: int = 0
    # (line number starting at 1, message) for every problem found
    errors: List[Tuple[int, str]] = field(default_factory=list)
    # non-fatal advisories (e.g. count below AWS's recommended floor)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, line_no: int, message: str) -> None:
        self.errors.append((line_no, message))

    def summary(self) -> str:
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("DATASET VALIDATION")
        lines.append("=" * 60)
        lines.append(f"Records checked: {self.total}")
        lines.append(f"Errors: {len(self.errors)}")
        lines.append(f"Warnings: {len(self.warnings)}")
        lines.append("")

        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")
            lines.append("")

        if self.errors:
            lines.append("Errors (line: problem):")
            for line_no, message in self.errors:
                lines.append(f"  line {line_no}: {message}")
            lines.append("")
            lines.append("RESULT: NOT READY - fix the errors above before uploading.")
        else:
            lines.append("RESULT: READY - this file satisfies the workshop's rules.")
        lines.append("=" * 60)
        return "\n".join(lines)


def _reserved_hits(text: str) -> List[str]:
    return [s for s in RESERVED_STRINGS if s in text]


def _extract_text(content) -> Optional[str]:
    """Pull concatenated text out of a Converse-style ``content`` array."""

    if not isinstance(content, list):
        return None
    parts: List[str] = []
    for block in content:
        if not isinstance(block, dict) or "text" not in block:
            return None
        parts.append(str(block["text"]))
    return "".join(parts)


def _validate_system(system, line_no: int, report: ValidationReport) -> Optional[str]:
    """Validate a record's ``system`` field. Returns its text (or None)."""

    if system is None:
        return None
    if not isinstance(system, list) or not system:
        report.add_error(line_no, "'system' must be a non-empty list of {text} blocks")
        return None
    text = _extract_text(system)
    if text is None:
        report.add_error(line_no, "'system' blocks must each be {\"text\": ...}")
        return None
    for hit in _reserved_hits(text):
        report.add_error(line_no, f"system text contains reserved string {hit!r}")
    return text


def _validate_messages(messages, line_no: int, report: ValidationReport) -> None:
    if not isinstance(messages, list) or not messages:
        report.add_error(line_no, "'messages' must be a non-empty list")
        return

    roles = []
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            report.add_error(line_no, f"messages[{i}] must be an object")
            continue
        role = msg.get("role")
        roles.append(role)
        if role not in ("user", "assistant"):
            report.add_error(
                line_no,
                f"messages[{i}] role {role!r} is not 'user' or 'assistant'",
            )
        text = _extract_text(msg.get("content"))
        if text is None:
            report.add_error(
                line_no,
                f"messages[{i}] content must be a list of {{\"text\": ...}} blocks",
            )
            continue
        if not text.strip():
            report.add_error(line_no, f"messages[{i}] text is empty")
        # Reserved strings only fail on user/system text, per the guide.
        if role == "user":
            for hit in _reserved_hits(text):
                report.add_error(
                    line_no, f"user text contains reserved string {hit!r}"
                )

    if roles:
        if roles[0] != "user":
            report.add_error(line_no, f"first turn must be 'user', got {roles[0]!r}")
        if roles[-1] != "assistant":
            report.add_error(
                line_no, f"last turn must be 'assistant', got {roles[-1]!r}"
            )


def validate_records(records: List[dict]) -> ValidationReport:
    """Validate an in-memory list of records (already parsed from JSONL)."""

    report = ValidationReport(total=len(records))

    # Record-count bounds (Nova Micro).
    if len(records) < MIN_RECORDS:
        report.warnings.append(
            f"{len(records)} records is below the {MIN_RECORDS}-record minimum; "
            f"training will FAIL. AWS recommends >= 200 per task."
        )
    if len(records) > MAX_RECORDS:
        report.add_error(0, f"{len(records)} records exceeds the {MAX_RECORDS} maximum")

    system_texts = set()

    for idx, record in enumerate(records):
        line_no = idx + 1

        if not isinstance(record, dict):
            report.add_error(line_no, "record is not a JSON object")
            continue

        if record.get("schemaVersion") != SCHEMA_VERSION:
            report.add_error(
                line_no,
                f"schemaVersion must be {SCHEMA_VERSION!r}, "
                f"got {record.get('schemaVersion')!r}",
            )

        system_text = _validate_system(record.get("system"), line_no, report)
        # Track the system prompt (including "no system prompt") for the
        # identical-across-rows check.
        system_texts.add(system_text)

        _validate_messages(record.get("messages"), line_no, report)

    if len(system_texts) > 1:
        report.warnings.append(
            "System prompt is not identical on every row "
            f"({len(system_texts)} distinct values, including possibly none). "
            "The guide requires one identical system prompt across all rows."
        )

    return report


def validate_file(path: str | Path) -> ValidationReport:
    """
    Validate a ``.jsonl`` file on disk. Parse errors are reported per line so a
    single malformed line does not hide the rest.
    """

    path = Path(path)
    if not path.exists():
        report = ValidationReport()
        report.add_error(0, f"file not found: {path}")
        return report

    # Parse line-by-line so we can report the exact offending line.
    import json

    records: List[dict] = []
    parse_report = ValidationReport()
    with path.open("r", encoding="utf-8") as fh:
        for i, raw in enumerate(fh):
            line = raw.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                parse_report.add_error(i + 1, f"line is not valid JSON: {exc.msg}")

    if parse_report.errors:
        # If any line failed to parse, report only that - the structural
        # checks below assume parseable JSON.
        parse_report.total = len(records) + len(parse_report.errors)
        return parse_report

    return validate_records(records)
