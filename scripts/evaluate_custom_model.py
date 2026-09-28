"""
Evaluate tactical model providers against the existing 16-scenario benchmark.

    python -m scripts.evaluate_custom_model [--providers ...]
                                            [--custom-model-id ID]
                                            [--test-set PATH]

Compares up to three providers head-to-head:

    DETERMINISTIC   the existing football brain (always available)
    NOVA_BASE       the existing Amazon Nova Pro integration (needs AWS)
    NOVA_CUSTOM     a customized Nova model (needs --custom-model-id)

Metrics come from real calls only. Any provider that is not executed
(no credentials, no customized model yet, or a call failure) is reported
as 'NOT RUN' - numbers are never fabricated.

By default NOVA_BASE and NOVA_CUSTOM are only included if they can run
without AWS surprises: NOVA_BASE runs only when explicitly requested (it
makes real Bedrock calls), and NOVA_CUSTOM runs only when a model id is
supplied. This keeps the default invocation fully offline.
"""

import argparse
import sys
from pathlib import Path

from app.fine_tuning.custom_model_client import ModelProvider, TacticalModelClient
from app.fine_tuning.evaluation import (
    evaluate_provider,
    format_comparison_report,
)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate model providers against the football benchmark."
    )
    parser.add_argument(
        "--providers", nargs="+",
        default=["DETERMINISTIC", "NOVA_CUSTOM"],
        choices=["DETERMINISTIC", "NOVA_BASE", "NOVA_CUSTOM"],
        help=(
            "Providers to evaluate. Default: DETERMINISTIC NOVA_CUSTOM "
            "(fully offline; NOVA_CUSTOM reports NOT RUN without a model id). "
            "Add NOVA_BASE to make real Bedrock calls."
        ),
    )
    parser.add_argument(
        "--custom-model-id", type=str, default=None,
        help="Customized Nova model id / endpoint for the NOVA_CUSTOM provider.",
    )
    parser.add_argument(
        "--out", type=str, default=None,
        help="Optional path to also write the report as markdown.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    reports = []
    for name in args.providers:
        provider = ModelProvider(name)
        client = TacticalModelClient(
            provider,
            custom_model_id=args.custom_model_id,
        )
        reports.append(evaluate_provider(client))

    text = format_comparison_report(reports)
    print(text)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"\nReport written to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
