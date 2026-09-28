"""
Tests for the fine-tuning preparation layer (app/fine_tuning/).

Fully offline and deterministic - no AWS, no Bedrock, no network. Model
providers are exercised with an injected fake analyzer so nothing touches
boto3.

Run directly:

    python -m tests.test_finetuning
"""

import sys
import traceback


def _case_test_finetuning():
    import socket

    from app.core.game_state import GameState, Player, Position
    from app.fine_tuning.config import DatasetConfig, SplitConfig
    from app.fine_tuning.dataset_builder import (
        build_dataset,
        example_to_sagemaker_record,
        split_dataset,
    )
    from app.fine_tuning.dataset_schema import (
        ALLOWED_ACTIONS,
        ALLOWED_MODES,
        TrainingExample,
        TrainingInput,
        TrainingOutput,
    )
    from app.fine_tuning.example_generator import (
        build_base_examples,
        game_state_to_input,
        generate_examples,
        make_example,
    )
    from app.fine_tuning.validation import (
        compute_statistics,
        format_statistics,
        is_valid,
        validate_dataset,
        validate_example,
    )
    from app.fine_tuning.custom_model_client import (
        CustomModelUnavailableError,
        ModelProvider,
        TacticalModelClient,
    )
    from app.fine_tuning.evaluation import (
        NOT_RUN,
        evaluate_provider,
        format_comparison_report,
    )
    from app.ai.response_parser import TacticalRecommendation
    from app.agents.coordinator import AgentCoordinator

    def _no_network_guard():
        original = socket.socket.connect

        def blocked(self, *args, **kwargs):
            raise AssertionError("network call attempted during fine-tuning tests")

        socket.socket.connect = blocked
        return lambda: setattr(socket.socket, "connect", original)

    # ---- helpers --------------------------------------------------------

    def _valid_example() -> TrainingExample:
        return TrainingExample(
            input=TrainingInput(
                ball_position={"x": 82, "y": 50},
                possession="OUR_TEAM",
                our_team=[
                    {"player_id": "striker", "role": "STRIKER",
                     "position": {"x": 82, "y": 50}},
                ],
                opponent_team=[],
                tactical_context="Clear shot.",
            ),
            output=TrainingOutput(
                tactical_mode="ATTACK",
                recommended_agent="striker",
                recommended_action="SHOOT",
                confidence=0.9,
                reason="Striker is near goal.",
            ),
            metadata={"category": "ATTACK", "augmented": False},
        )

    class FakeAnalyzer:
        """Stand-in for LLMTacticalAnalyzer - never calls AWS."""

        def __init__(self, recommendation: TacticalRecommendation):
            self._rec = recommendation
            self.calls = 0

        def analyze(self, game_state):
            self.calls += 1
            return self._rec

    # ---- 1. schema ------------------------------------------------------

    def test_schema_roundtrip():
        ex = _valid_example()
        d = ex.to_dict()
        assert set(d.keys()) == {"input", "output", "metadata"}
        back = TrainingExample.from_dict(d)
        assert back.to_dict() == d
        assert "SHOOT" in ALLOWED_ACTIONS
        assert "ATTACK" in ALLOWED_MODES

    # ---- 2. gamestate -> example ---------------------------------------

    def test_gamestate_to_training_example():
        gs = GameState(
            ball_position=Position(x=82, y=50),
            our_team=[
                Player("goalkeeper", "GOALKEEPER", Position(5, 50)),
                Player("defender", "DEFENDER", Position(40, 45)),
                Player("midfielder", "MIDFIELDER", Position(70, 40)),
                Player("striker", "STRIKER", Position(82, 50)),
            ],
            opponent_team=[Player("opp1", "DEFENDER", Position(70, 40))],
            possession="OUR_TEAM",
        )
        inp = game_state_to_input(gs, "context")
        assert inp.possession == "OUR_TEAM"
        assert isinstance(inp.our_team, list) and len(inp.our_team) == 4
        assert inp.our_team[0]["player_id"] == "goalkeeper"

        ex = make_example(gs, AgentCoordinator(), tactical_context="context")
        # Label produced by the deterministic engine.
        assert ex.output.tactical_mode == "ATTACK"
        assert ex.output.recommended_action in ALLOWED_ACTIONS
        assert is_valid(ex)

    # ---- 3. generation from benchmark ----------------------------------

    def test_generation_uses_all_16_scenarios():
        base = build_base_examples()
        assert len(base) == 16
        # Every base example is valid and labelled by the real engine.
        for ex in base:
            assert is_valid(ex), validate_example(ex)
            assert ex.metadata["augmented"] is False

    def test_generate_examples_deterministic_and_augments():
        a = generate_examples(50, seed=42)
        b = generate_examples(50, seed=42)
        assert len(a) == 50
        # Deterministic: same seed -> identical dataset.
        assert [e.to_dict() for e in a] == [e.to_dict() for e in b]
        # First 16 are the base scenarios.
        assert sum(1 for e in a if not e.metadata.get("augmented")) == 16
        assert sum(1 for e in a if e.metadata.get("augmented")) == 34
        # Fewer than base -> just the first N base examples.
        small = generate_examples(5, seed=42)
        assert len(small) == 5
        assert all(not e.metadata.get("augmented") for e in small)

    # ---- 4. validation + malformed rejection ---------------------------

    def test_validation_accepts_valid_and_rejects_malformed():
        good = _valid_example()
        assert validate_example(good) == []

        # bad action
        bad_action = _valid_example()
        bad_action.output.recommended_action = "TELEPORT"
        assert any("recommended_action" in e for e in validate_example(bad_action))

        # bad mode
        bad_mode = _valid_example()
        bad_mode.output.tactical_mode = "PANIC"
        assert any("tactical_mode" in e for e in validate_example(bad_mode))

        # confidence out of range
        bad_conf = _valid_example()
        bad_conf.output.confidence = 1.7
        assert any("confidence" in e for e in validate_example(bad_conf))

        # empty reason
        bad_reason = _valid_example()
        bad_reason.output.reason = "   "
        assert any("reason" in e for e in validate_example(bad_reason))

        # recommended agent not in our_team
        bad_agent = _valid_example()
        bad_agent.output.recommended_agent = "ghost"
        assert any("recommended_agent" in e for e in validate_example(bad_agent))

        # invalid GameState (missing ball position axis)
        bad_gs = _valid_example()
        bad_gs.input.ball_position = {"x": 10}
        assert any("ball_position" in e for e in validate_example(bad_gs))

    def test_validate_dataset_drops_malformed():
        good = _valid_example()
        bad = _valid_example()
        bad.output.recommended_action = "NOPE"
        valid, report = validate_dataset([good, bad, good])
        assert report.total == 3
        assert report.valid == 2
        assert report.invalid == 1
        assert not report.all_valid
        assert len(valid) == 2

    # ---- 5. split -------------------------------------------------------

    def test_deterministic_split_and_isolation():
        examples = generate_examples(50, seed=42)
        split = SplitConfig(0.8, 0.1, 0.1, seed=42)
        s1 = split_dataset(examples, split)
        s2 = split_dataset(examples, split)
        # Reproducible.
        assert s1.counts() == s2.counts()
        assert [e.to_dict() for e in s1.test] == [e.to_dict() for e in s2.test]
        # Ratios (test = remainder).
        assert s1.counts() == {"train": 40, "validation": 5, "test": 5}
        # Test isolation from train.
        train_sigs = {id(e) for e in s1.train}
        assert all(id(e) not in train_sigs for e in s1.test)
        # No example lost.
        assert (
            len(s1.train) + len(s1.validation) + len(s1.test) == len(examples)
        )

    def test_split_ratio_validation():
        try:
            SplitConfig(0.8, 0.2, 0.2).validate()
        except ValueError:
            pass
        else:
            raise AssertionError("split ratios that don't sum to 1 must fail")

    # ---- 6. statistics --------------------------------------------------

    def test_statistics_report():
        examples = generate_examples(40, seed=42)
        split = split_dataset(examples, SplitConfig(seed=42))
        stats = compute_statistics(examples, split.counts())
        assert stats["total_examples"] == 40
        assert stats["base_examples"] == 16
        assert stats["augmented_examples"] == 24
        assert sum(stats["categories"].values()) == 40
        assert sum(stats["actions"].values()) == 40
        text = format_statistics(stats)
        assert "Dataset Statistics" in text
        assert "Total examples: 40" in text

    # ---- 7. dataset builder + sagemaker record -------------------------

    def test_build_dataset_in_memory_and_sagemaker_record():
        restore = _no_network_guard()
        try:
            cfg = DatasetConfig(dataset_size=30, seed=42)
            result = build_dataset(cfg, write=False)
        finally:
            restore()
        assert result.validation_report.all_valid
        assert (
            len(result.split.train)
            + len(result.split.validation)
            + len(result.split.test)
            == 30
        )
        rec = example_to_sagemaker_record(_valid_example())
        assert "system" in rec and "messages" in rec
        roles = [m["role"] for m in rec["messages"]]
        assert roles == ["user", "assistant"]

    # ---- 8. model evaluation logic (deterministic baseline) ------------

    def test_deterministic_baseline_is_16_16():
        restore = _no_network_guard()
        try:
            report = evaluate_provider(
                TacticalModelClient(ModelProvider.DETERMINISTIC)
            )
        finally:
            restore()
        assert report.ran is True
        assert report.total == 16
        assert report.full_agreements == 16
        assert report.invalid_responses == 0
        assert report.mode_accuracy == 100.0
        assert report.agent_accuracy == 100.0
        assert report.action_accuracy == 100.0

    # ---- 9. NOT RUN behavior when model unavailable --------------------

    def test_nova_custom_not_run_without_model_id():
        client = TacticalModelClient(ModelProvider.NOVA_CUSTOM)
        assert client.is_available() is False
        report = evaluate_provider(client)
        assert report.ran is False
        assert report.reason_not_run
        # And the formatted report shows NOT RUN, never a fabricated number.
        text = format_comparison_report([report])
        assert NOT_RUN in text
        # The customized-nova block must not contain a percentage metric.
        block = report and __import__(
            "app.fine_tuning.evaluation", fromlist=["format_provider_block"]
        ).format_provider_block(report)
        assert "%" not in block

    def test_nova_custom_raises_when_called_without_id():
        client = TacticalModelClient(ModelProvider.NOVA_CUSTOM)
        try:
            client.analyze(
                GameState(
                    ball_position=Position(0, 0),
                    our_team=[Player("striker", "STRIKER", Position(0, 0))],
                    opponent_team=[],
                    possession="OUR_TEAM",
                )
            )
        except CustomModelUnavailableError:
            pass
        else:
            raise AssertionError("NOVA_CUSTOM without id must raise")

    # ---- 10. model providers via injected fake analyzer ----------------

    def test_nova_provider_with_fake_analyzer():
        rec = TacticalRecommendation(
            tactical_mode="ATTACK",
            recommended_agent="striker",
            recommended_action="SHOOT",
            confidence=0.8,
            reason="fake",
        )
        fake = FakeAnalyzer(rec)
        client = TacticalModelClient(ModelProvider.NOVA_BASE, analyzer=fake)
        report = evaluate_provider(client)
        assert report.ran is True
        assert report.total == 16
        # The fake always says striker/SHOOT/ATTACK -> matches only some.
        assert fake.calls == 16
        assert report.invalid_responses == 0
        # Custom provider with an id also uses the injected analyzer.
        custom = TacticalModelClient(
            ModelProvider.NOVA_CUSTOM,
            custom_model_id="fake-model",
            analyzer=fake,
        )
        assert custom.is_available() is True
        crep = evaluate_provider(custom)
        assert crep.ran is True
        assert crep.total == 16

    def test_invalid_model_responses_are_counted_not_crashed():
        class ExplodingAnalyzer:
            def analyze(self, game_state):
                raise RuntimeError("model returned garbage")

        client = TacticalModelClient(
            ModelProvider.NOVA_BASE, analyzer=ExplodingAnalyzer()
        )
        report = evaluate_provider(client)
        assert report.ran is True
        assert report.invalid_responses == report.total
        # Accuracy is None (nothing scored) -> shown as NOT RUN in the report.
        assert report.mode_accuracy is None

    def main():
        test_schema_roundtrip()
        test_gamestate_to_training_example()
        test_generation_uses_all_16_scenarios()
        test_generate_examples_deterministic_and_augments()
        test_validation_accepts_valid_and_rejects_malformed()
        test_validate_dataset_drops_malformed()
        test_deterministic_split_and_isolation()
        test_split_ratio_validation()
        test_statistics_report()
        test_build_dataset_in_memory_and_sagemaker_record()
        test_deterministic_baseline_is_16_16()
        test_nova_custom_not_run_without_model_id()
        test_nova_custom_raises_when_called_without_id()
        test_nova_provider_with_fake_analyzer()
        test_invalid_model_responses_are_counted_not_crashed()
        print("All fine-tuning checks passed.")

    main()


_CASES = [
    ("test_finetuning", _case_test_finetuning),
]


def main():
    failures = []
    for label, fn in _CASES:
        print("\n" + "#" * 72)
        print("# " + label)
        print("#" * 72)
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - report and continue
            traceback.print_exc()
            failures.append((label, exc))
    print("\n" + "=" * 72)
    if failures:
        print(f"{len(failures)} case(s) FAILED: {[n for n, _ in failures]}")
        sys.exit(1)
    print(f"All {len(_CASES)} case(s) passed.")


if __name__ == "__main__":
    main()
