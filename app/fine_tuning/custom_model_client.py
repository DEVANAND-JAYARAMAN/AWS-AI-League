"""
Inference adapter for tactical recommendations across model providers.

Three providers share one clean interface:

    analyze(game_state) -> TacticalRecommendation

    DETERMINISTIC   the existing football brain, wrapped as a recommendation
    NOVA_BASE       the existing app/ai Nova Pro integration (unchanged)
    NOVA_CUSTOM     a customized Nova model produced by SageMaker AI

The point is to let the evaluation framework compare the three head-to-head
using the *same* call. The existing ``app/ai/bedrock_nova.py`` is not
modified - ``NOVA_BASE`` simply delegates to it, and ``NOVA_CUSTOM`` reuses
the same Converse pipeline pointed at a customized model id.

Nothing here launches AWS jobs. ``NOVA_CUSTOM`` only works once a real
customized model id / endpoint exists; until then it raises
:class:`CustomModelUnavailableError`, which the evaluation layer maps to
``NOT RUN`` rather than fabricating a result.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from app.ai.response_parser import TacticalRecommendation
from app.core.game_state import GameState


class ModelProvider(str, Enum):
    """Which tactical brain to consult."""

    DETERMINISTIC = "DETERMINISTIC"
    NOVA_BASE = "NOVA_BASE"
    NOVA_CUSTOM = "NOVA_CUSTOM"


class CustomModelUnavailableError(RuntimeError):
    """Raised when a NOVA_CUSTOM model has not been provisioned yet."""


# ----------------------------------------------------------------------
# Deterministic provider (wraps the existing brain as a recommendation)
# ----------------------------------------------------------------------

class DeterministicRecommender:
    """
    Adapts the existing deterministic TeamDecision into the same
    :class:`TacticalRecommendation` shape the model providers return, so the
    evaluation code can treat all three providers identically.

    This does NOT change the deterministic engine - it only reads its output.
    """

    def __init__(self, coordinator=None):
        # Imported lazily to keep this module import-light.
        from app.agents.coordinator import AgentCoordinator

        self.coordinator = coordinator or AgentCoordinator()

    def analyze(
        self,
        game_state: GameState,
        *,
        prefer_agent: Optional[str] = None,
    ) -> TacticalRecommendation:
        from app.fine_tuning.example_generator import team_decision_to_output

        team_decision = self.coordinator.get_coordinated_team_decision(game_state)
        out = team_decision_to_output(team_decision, prefer_agent=prefer_agent)
        return TacticalRecommendation(
            tactical_mode=out.tactical_mode,
            recommended_agent=out.recommended_agent,
            recommended_action=out.recommended_action,
            confidence=out.confidence,
            reason=out.reason,
        )


# ----------------------------------------------------------------------
# Unified client
# ----------------------------------------------------------------------

class TacticalModelClient:
    """
    One ``analyze(game_state) -> TacticalRecommendation`` entry point for all
    three providers.

    Parameters
    ----------
    provider:
        Which brain to use.
    custom_model_id:
        The customized-model id (or endpoint / inference-profile ARN) for
        ``NOVA_CUSTOM``. If ``None`` for the custom provider, calls raise
        :class:`CustomModelUnavailableError`.
    analyzer:
        Optional pre-built ``LLMTacticalAnalyzer`` (used for NOVA_* providers
        and dependency injection in tests).
    """

    def __init__(
        self,
        provider: ModelProvider = ModelProvider.DETERMINISTIC,
        *,
        custom_model_id: Optional[str] = None,
        analyzer=None,
        coordinator=None,
    ):
        self.provider = ModelProvider(provider)
        self.custom_model_id = custom_model_id
        self._analyzer = analyzer
        self._coordinator = coordinator
        self._deterministic: Optional[DeterministicRecommender] = None

    # -- capability check -------------------------------------------------

    def is_available(self) -> bool:
        """
        True when this provider can actually be called right now.

        DETERMINISTIC is always available. NOVA_BASE is treated as available
        (the real Bedrock call happens at analyze time and raises on its
        own if creds/access are missing). NOVA_CUSTOM is available only when
        a custom_model_id has been supplied.
        """

        if self.provider is ModelProvider.NOVA_CUSTOM:
            return bool(self.custom_model_id)
        return True

    # -- main call --------------------------------------------------------

    def analyze(
        self,
        game_state: GameState,
        *,
        prefer_agent: Optional[str] = None,
    ) -> TacticalRecommendation:
        """
        Return a tactical recommendation for ``game_state``.

        ``prefer_agent`` only affects the DETERMINISTIC provider: it lets the
        baseline report a specific agent's own decision (matching how the
        benchmark grades INDIVIDUAL scenarios). Model providers ignore it -
        the model is free to recommend any of our players.
        """

        if self.provider is ModelProvider.DETERMINISTIC:
            return self._analyze_deterministic(game_state, prefer_agent)

        if self.provider is ModelProvider.NOVA_BASE:
            return self._analyze_nova(game_state, model_id=None)

        if self.provider is ModelProvider.NOVA_CUSTOM:
            if not self.custom_model_id:
                raise CustomModelUnavailableError(
                    "NOVA_CUSTOM has no custom_model_id. A customized model "
                    "must be produced by a SageMaker AI training run and its "
                    "id supplied before this provider can be used."
                )
            return self._analyze_nova(game_state, model_id=self.custom_model_id)

        raise ValueError(f"Unknown provider {self.provider!r}")

    # -- provider implementations ----------------------------------------

    def _analyze_deterministic(
        self, game_state: GameState, prefer_agent: Optional[str]
    ) -> TacticalRecommendation:
        if self._deterministic is None:
            self._deterministic = DeterministicRecommender(self._coordinator)
        return self._deterministic.analyze(game_state, prefer_agent=prefer_agent)

    def _analyze_nova(
        self, game_state: GameState, model_id: Optional[str]
    ) -> TacticalRecommendation:
        analyzer = self._analyzer
        if analyzer is None:
            # Imported lazily so importing this module never requires boto3.
            from app.ai.bedrock_nova import LLMTacticalAnalyzer

            analyzer = LLMTacticalAnalyzer(model_id=model_id)
        return analyzer.analyze(game_state)
