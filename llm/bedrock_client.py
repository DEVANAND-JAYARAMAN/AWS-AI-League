"""
Reusable Amazon Bedrock client (Converse API).

* Uses ``boto3.client("bedrock-runtime", region_name=...)`` and
  ``client.converse(...)``.
* Credentials come from boto3's **default credential provider chain**
  (environment, ``~/.aws/credentials``, SSO, IAM role, ...). This module
  never reads, accepts, or logs AWS keys / secrets / session tokens.
* Region and model id are configurable (env overrides ``AWS_REGION`` and
  ``BEDROCK_MODEL_ID``) and default to the values known to work for this
  project: ``ap-south-1`` and the APAC Amazon Nova Pro inference profile.
"""

import logging
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


# Optional overrides via environment (NOT credentials - just routing).
DEFAULT_REGION = (
    os.getenv("AWS_REGION")
    or os.getenv("AWS_DEFAULT_REGION")
    or "ap-south-1"
)

DEFAULT_MODEL_ID = os.getenv("BEDROCK_MODEL_ID") or "apac.amazon.nova-pro-v1:0"


class BedrockInvocationError(RuntimeError):
    """Raised when a Bedrock Converse call fails or returns no text."""


class BedrockClient:
    """Thin wrapper around ``bedrock-runtime`` ``converse``."""

    def __init__(
        self,
        region_name: str | None = None,
        model_id: str | None = None,
        *,
        client=None,
    ):
        self.region_name = region_name or DEFAULT_REGION
        self.model_id = model_id or DEFAULT_MODEL_ID
        # ``client`` injection is only for tests - production always builds
        # a real boto3 client that uses the default provider chain.
        self._client = client or boto3.client(
            "bedrock-runtime", region_name=self.region_name
        )

    # ------------------------------------------------------------------
    def invoke(
        self,
        messages: list[dict],
        *,
        system: str | list[dict] | None = None,
        max_tokens: int = 500,
        temperature: float = 0.2,
    ) -> str:
        """
        Send a Converse request to Bedrock and return the assistant text.

        ``messages`` uses the Bedrock Converse format::

            [{"role": "user", "content": [{"text": "..."}]}]

        ``system`` may be a plain string or a list of Converse system
        blocks (``[{"text": "..."}]``).
        """

        inference_config = {
            "maxTokens": max_tokens,
            "temperature": temperature,
        }

        kwargs: dict = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": inference_config,
        }
        if system:
            kwargs["system"] = (
                system if isinstance(system, list) else [{"text": system}]
            )

        logger.info(
            "Bedrock Converse -> model '%s' region '%s' "
            "(maxTokens=%s, temperature=%s)",
            self.model_id,
            self.region_name,
            max_tokens,
            temperature,
        )

        try:
            response = self._client.converse(**kwargs)
        except (BotoCoreError, ClientError) as exc:
            logger.error("Bedrock Converse call failed: %s", exc)
            raise BedrockInvocationError(
                f"Bedrock converse failed for '{self.model_id}': {exc}"
            ) from exc

        text = self._extract_text(response)
        logger.info(
            "Bedrock Converse response received (%d characters, stopReason=%s)",
            len(text),
            response.get("stopReason"),
        )
        return text

    # ------------------------------------------------------------------
    def invoke_text(self, prompt: str, **kwargs) -> str:
        """Convenience: single user-text prompt in, assistant text out."""

        return self.invoke(
            [{"role": "user", "content": [{"text": prompt}]}], **kwargs
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_text(response: dict) -> str:
        """Pull the concatenated text blocks out of a Converse response."""

        try:
            blocks = response["output"]["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise BedrockInvocationError(
                f"Unexpected Converse response shape: {response!r}"
            ) from exc

        parts = [
            block["text"]
            for block in blocks
            if isinstance(block, dict) and "text" in block
        ]
        text = "".join(parts).strip()

        if not text:
            raise BedrockInvocationError(
                f"Converse response contained no text content: {response!r}"
            )
        return text
