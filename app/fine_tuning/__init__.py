"""
Model-customization / fine-tuning preparation layer.

This package is a *fine-tuning-ready* pipeline that turns the project's
existing deterministic football intelligence into a supervised
fine-tuning dataset for an Amazon Nova foundation model on Amazon
SageMaker AI.

Design rules (mirroring the rest of the project):

* **The deterministic engine is the source of truth.** Every training
  label is produced by the *existing* ``AgentCoordinator`` /
  ``TeamCoordinator`` pipeline - this package never re-implements or
  changes football decision logic, and it never invents labels by hand.
* **Modular and independent.** Nothing in the deterministic core imports
  this package. Removing ``app/fine_tuning/`` leaves the existing system
  untouched.
* **No AWS money is spent here.** This layer only *prepares* datasets and
  SageMaker configuration. It never starts a training job, creates an
  endpoint, or provisions infrastructure.
* **No false claims.** Nothing here asserts that a model has been
  fine-tuned or that accuracy improved. Until a real competition training
  run and evaluation happen, the model paths report ``NOT RUN``.

Terminology used throughout: *fine-tuning-ready*, *model-customization
pipeline*, *baseline*, *evaluation framework*.
"""

from app.fine_tuning.dataset_schema import (
    ALLOWED_ACTIONS,
    ALLOWED_MODES,
    TrainingExample,
    TrainingInput,
    TrainingOutput,
)
from app.fine_tuning.config import DatasetConfig, SplitConfig

__all__ = [
    "ALLOWED_ACTIONS",
    "ALLOWED_MODES",
    "TrainingExample",
    "TrainingInput",
    "TrainingOutput",
    "DatasetConfig",
    "SplitConfig",
]
