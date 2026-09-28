"""
AWS AI League - competition toolkit.

Standalone, topic-agnostic tooling to turn plain question/answer pairs into a
valid Amazon Nova Micro fine-tuning dataset (the `bedrock-conversation-2024`
JSONL format) and to validate that dataset against every rule the official
workshop says can fail a training job.

This package does NOT import or depend on the football project under `app/`.
It exists purely to produce and check the `.jsonl` file you upload in
Module 1 of the workshop.
"""
