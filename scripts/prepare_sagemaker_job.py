"""
Prepare a SageMaker AI customization / fine-tuning job configuration.

    python -m scripts.prepare_sagemaker_job [--out PATH]

This writes a JSON *template* describing a SageMaker AI model-customization
job. It does NOT call AWS, does NOT start training, and does NOT create any
infrastructure. Every competition-specific field is a PLACEHOLDER to be
filled in inside the official Workshop Studio environment once the exact
model id, training method, IO format, and hyperparameters are published.

Why placeholders:
    * The base model to customize is NOT assumed to be Nova Pro.
    * Hyperparameters are NOT assumed.
    * The dataset format may be remapped to the competition's required shape.

Output default: infrastructure/sagemaker/finetuning-job-template.json
"""

import argparse
import json
import sys
from pathlib import Path

from app.fine_tuning.config import (
    DEFAULT_OUTPUT_DIR,
    PLACEHOLDER,
    PROJECT_ROOT,
    SageMakerConfig,
)

DEFAULT_TEMPLATE_PATH = (
    PROJECT_ROOT / "infrastructure" / "sagemaker" / "finetuning-job-template.json"
)


def build_template() -> dict:
    """Assemble the placeholder job template."""

    cfg = SageMakerConfig()
    data_dir = DEFAULT_OUTPUT_DIR

    return {
        "_comment": (
            "TEMPLATE ONLY. This does not launch a job. Fill in the "
            "REPLACE_WITH_COMPETITION_VALUE placeholders inside the official "
            "AWS AI League Workshop Studio environment. The base model, "
            "training method, hyperparameters, and dataset IO format are all "
            "competition-specific and are NOT assumed here."
        ),
        "status": "NOT SUBMITTED",
        "job": {
            "job_name": PLACEHOLDER,
            "base_model_id": cfg.base_model_id,
            "customization_type": cfg.customization_type,
            "region": cfg.region,
            "role_arn": cfg.role_arn,
        },
        "data": {
            "local_train": str(data_dir / "train.jsonl"),
            "local_validation": str(data_dir / "validation.jsonl"),
            "local_test": str(data_dir / "test.jsonl"),
            "train_s3_uri": cfg.train_s3_uri,
            "validation_s3_uri": cfg.validation_s3_uri,
            "output_s3_uri": cfg.output_s3_uri,
            "format_note": (
                "Records are generated in a Bedrock Converse-style "
                "conversational shape (system + user + assistant). Remap to "
                "the competition's required format if it differs."
            ),
        },
        "hyperparameters": cfg.hyperparameters or {
            "_note": "Competition-specific. Do not assume values.",
        },
        "next_steps": [
            "1. Generate + validate the dataset locally.",
            "2. Confirm the official Nova base model id and training method.",
            "3. Upload the JSONL splits to the S3 bucket the competition provides.",
            "4. Fill in the placeholders above.",
            "5. Submit the job from inside the Workshop Studio environment.",
            "6. After training, run 'python -m scripts.evaluate_custom_model' "
            "with the customized model id.",
        ],
    }


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Write a SageMaker AI fine-tuning job template (no AWS calls)."
    )
    parser.add_argument(
        "--out", type=str, default=None,
        help=f"Output path (default: {DEFAULT_TEMPLATE_PATH}).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    out_path = Path(args.out) if args.out else DEFAULT_TEMPLATE_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    template = build_template()
    out_path.write_text(
        json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("=" * 60)
    print("SAGEMAKER AI JOB TEMPLATE PREPARED")
    print("=" * 60)
    print(f"Written to: {out_path}")
    print("")
    print("This is a TEMPLATE. No AWS resources were created and no training")
    print("was started. Fill in the placeholders inside the official")
    print("competition environment before submitting a real job.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
