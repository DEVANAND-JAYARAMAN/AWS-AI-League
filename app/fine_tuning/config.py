"""
Configuration for the fine-tuning dataset pipeline.

Everything competition-specific is configurable and defaults to safe,
inexpensive, reproducible values. Numbers here are *development defaults*
- the official competition instructions will supply the real model id,
dataset format, and hyperparameters.

Environment overrides (all optional):

    DATASET_SIZE                total examples to generate (default 100)
    DATASET_SEED                RNG seed for augmentation + split (default 42)
    DATASET_TRAIN_RATIO         default 0.8
    DATASET_VAL_RATIO           default 0.1
    DATASET_TEST_RATIO          default 0.1
    FINE_TUNING_OUTPUT_DIR      default data/fine_tuning
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Project root = two levels up from app/fine_tuning/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "fine_tuning"
EXAMPLE_OUTPUT_DIR = DEFAULT_OUTPUT_DIR / "example"


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# ----------------------------------------------------------------------
# Split configuration
# ----------------------------------------------------------------------

@dataclass
class SplitConfig:
    """Deterministic train / validation / test split ratios."""

    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1
    seed: int = 42

    def validate(self) -> None:
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Split ratios must sum to 1.0, got {total} "
                f"(train={self.train_ratio}, val={self.val_ratio}, "
                f"test={self.test_ratio})"
            )
        for name, value in (
            ("train_ratio", self.train_ratio),
            ("val_ratio", self.val_ratio),
            ("test_ratio", self.test_ratio),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value}")

    @classmethod
    def from_env(cls) -> "SplitConfig":
        cfg = cls(
            train_ratio=_float_env("DATASET_TRAIN_RATIO", 0.8),
            val_ratio=_float_env("DATASET_VAL_RATIO", 0.1),
            test_ratio=_float_env("DATASET_TEST_RATIO", 0.1),
            seed=_int_env("DATASET_SEED", 42),
        )
        return cfg


# ----------------------------------------------------------------------
# Dataset configuration
# ----------------------------------------------------------------------

@dataclass
class DatasetConfig:
    """
    Controls dataset generation.

    ``dataset_size`` is the target number of *total* examples. The 16 base
    scenarios are always included; the remainder are deterministic
    augmented variations around those base scenarios. The number stays
    modest by default so development never generates thousands of examples
    unintentionally.
    """

    dataset_size: int = 100
    seed: int = 42
    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)
    split: SplitConfig = field(default_factory=SplitConfig)

    # Positional jitter (in pitch units) applied to augmented variations.
    position_jitter: float = 6.0

    def validate(self) -> None:
        if self.dataset_size < 1:
            raise ValueError(f"dataset_size must be >= 1, got {self.dataset_size}")
        self.split.validate()

    @classmethod
    def from_env(cls) -> "DatasetConfig":
        out = os.getenv("FINE_TUNING_OUTPUT_DIR")
        output_dir = Path(out) if out else DEFAULT_OUTPUT_DIR
        seed = _int_env("DATASET_SEED", 42)
        split = SplitConfig.from_env()
        split.seed = seed
        cfg = cls(
            dataset_size=_int_env("DATASET_SIZE", 100),
            seed=seed,
            output_dir=output_dir,
            split=split,
        )
        return cfg


# ----------------------------------------------------------------------
# SageMaker preparation configuration (placeholders on purpose)
# ----------------------------------------------------------------------

# NOTE: These are intentionally PLACEHOLDERS. The official AWS AI League
# instructions (Workshop Studio environment) will specify the exact model
# id, training method, hyperparameters, and IO format. Do not treat any of
# these as final competition values.

PLACEHOLDER = "REPLACE_WITH_COMPETITION_VALUE"


@dataclass
class SageMakerConfig:
    """
    Fields needed to describe a SageMaker AI customization job template.

    Nothing here launches a job. This only produces a config file that a
    human (or a later script) fills in and submits inside the competition
    environment.
    """

    # The base model to customize. NOT assumed to be Nova Pro - the
    # competition may target a different Nova model.
    base_model_id: str = PLACEHOLDER
    customization_type: str = "FINE_TUNING"  # e.g. FINE_TUNING / DISTILLATION
    region: str = PLACEHOLDER
    role_arn: str = PLACEHOLDER
    output_s3_uri: str = PLACEHOLDER
    train_s3_uri: str = PLACEHOLDER
    validation_s3_uri: str = PLACEHOLDER

    # Hyperparameters are NOT assumed - left empty for the competition to fill.
    hyperparameters: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "base_model_id": self.base_model_id,
            "customization_type": self.customization_type,
            "region": self.region,
            "role_arn": self.role_arn,
            "output_s3_uri": self.output_s3_uri,
            "train_s3_uri": self.train_s3_uri,
            "validation_s3_uri": self.validation_s3_uri,
            "hyperparameters": self.hyperparameters,
        }
