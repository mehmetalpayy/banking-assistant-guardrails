from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def pipeline():
    from pipeline import GuardrailPipeline

    return GuardrailPipeline()


# ---------------------------------------------------------------------------
# Input checks
# ---------------------------------------------------------------------------


class TestPipelineInput:
    def test_banking_input_not_blocked(self, pipeline):
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.label = "BANKING"
        with patch.object(
            pipeline.topic_guard.client.chat.completions, "parse", return_value=mock_response
        ):
            result = pipeline.check_input("What is the APR on the Mehmet Gold card?")
        assert not result.blocked

    def test_off_topic_input_is_blocked(self, pipeline):
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.label = "OFF_TOPIC"
        with patch.object(
            pipeline.topic_guard.client.chat.completions, "parse", return_value=mock_response
        ):
            result = pipeline.check_input("What is the weather in Paris?")
        assert result.blocked
        assert result.block_reason == "off_topic"

    def test_blocked_response_is_non_empty(self, pipeline):
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.label = "OFF_TOPIC"
        with patch.object(
            pipeline.topic_guard.client.chat.completions, "parse", return_value=mock_response
        ):
            result = pipeline.check_input("Tell me about football.")
        assert result.blocked
        assert len(result.response) > 0


# ---------------------------------------------------------------------------
# Output checks
# ---------------------------------------------------------------------------


class TestPipelineOutput:
    sources = [
        "The Mehmet Grow Savings account offers 4.50% APY.",
        "Mehmet Gold Card APR is 17.99%–24.99%.",
    ]

    def test_clean_response_passes_unchanged(self, pipeline):
        response = "The savings account offers 4.50% APY."
        result = pipeline.check_output(response, self.sources)
        assert not result.blocked
        assert result.response == response

    def test_competitor_mention_replaced(self, pipeline):
        response = "Unlike Chase, Mehmet Bank offers competitive rates."
        result = pipeline.check_output(response, self.sources)
        assert "Chase" not in result.response
        assert "[competitor bank]" in result.response

    def test_pii_masked(self, pipeline):
        response = "Your card 4111 1111 1111 1111 is linked to your account."
        result = pipeline.check_output(response, self.sources)
        assert "4111 1111 1111 1111" not in result.response

    def test_guard_log_contains_all_three_guards(self, pipeline):
        result = pipeline.check_output("Mehmet Bank offers great rates.", self.sources)
        guard_names = [entry["guard"] for entry in result.guard_log]
        assert "hallucination" in guard_names
        assert "pii" in guard_names
        assert "competitor" in guard_names

    def test_guard_log_has_elapsed_ms(self, pipeline):
        result = pipeline.check_output("Some response.", self.sources)
        for entry in result.guard_log:
            assert "elapsed_ms" in entry
            assert entry["elapsed_ms"] >= 0
