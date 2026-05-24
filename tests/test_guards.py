from unittest.mock import MagicMock, patch

import pytest
from guardrails import OnFailAction
from guardrails.validator_base import FailResult, PassResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def topic_filter():
    from guards.topic_filter import BankingTopicFilter

    return BankingTopicFilter(on_fail=OnFailAction.FIX)


@pytest.fixture(scope="module")
def hallucination_detector():
    from guards.hallucination import HallucinationDetector

    return HallucinationDetector(on_fail=OnFailAction.FIX)


@pytest.fixture(scope="module")
def pii_detector():
    from guards.pii import PIIDetector

    return PIIDetector(on_fail=OnFailAction.FIX)


@pytest.fixture(scope="module")
def competitor_detector():
    from guards.competitor import CompetitorDetector

    return CompetitorDetector(on_fail=OnFailAction.FIX)


# ---------------------------------------------------------------------------
# Topic Filter (mocked — requires OpenAI API)
# ---------------------------------------------------------------------------


class TestTopicFilter:
    def test_banking_question_passes(self, topic_filter):
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.label = "BANKING"
        with patch.object(
            topic_filter.client.chat.completions, "parse", return_value=mock_response
        ):
            result = topic_filter.validate("What is the APR on the Mehmet Gold card?", {})
        assert isinstance(result, PassResult)

    def test_off_topic_fails(self, topic_filter):
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.label = "OFF_TOPIC"
        with patch.object(
            topic_filter.client.chat.completions, "parse", return_value=mock_response
        ):
            result = topic_filter.validate("What is the capital of France?", {})
        assert isinstance(result, FailResult)

    def test_off_topic_fix_value_mentions_banking(self, topic_filter):
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.label = "OFF_TOPIC"
        with patch.object(
            topic_filter.client.chat.completions, "parse", return_value=mock_response
        ):
            result = topic_filter.validate("Tell me a joke.", {})
        assert isinstance(result, FailResult)
        assert "banking" in result.fix_value.lower()

    def test_fix_value_mentions_mehmet_bank(self, topic_filter):
        mock_response = MagicMock()
        mock_response.choices[0].message.parsed.label = "OFF_TOPIC"
        with patch.object(
            topic_filter.client.chat.completions, "parse", return_value=mock_response
        ):
            result = topic_filter.validate("Who will win the World Cup?", {})
        assert isinstance(result, FailResult)
        assert "Mehmet Bank" in result.fix_value


# ---------------------------------------------------------------------------
# Hallucination Detector
# ---------------------------------------------------------------------------


class TestHallucinationDetector:
    sources = ["The Mehmet Grow Savings account offers 4.50% APY as of Q2 2026."]

    def test_grounded_response_passes(self, hallucination_detector):
        result = hallucination_detector.validate(
            "The savings account offers 4.50% APY.",
            metadata={"sources": self.sources},
        )
        assert isinstance(result, PassResult)

    def test_hallucinated_rate_fails(self, hallucination_detector):
        result = hallucination_detector.validate(
            "The savings account offers 9.99% APY.",
            metadata={"sources": self.sources},
        )
        assert isinstance(result, FailResult)

    def test_no_sources_passes(self, hallucination_detector):
        result = hallucination_detector.validate("Some statement.", metadata={})
        assert isinstance(result, PassResult)

    def test_empty_sources_passes(self, hallucination_detector):
        result = hallucination_detector.validate("Some statement.", metadata={"sources": []})
        assert isinstance(result, PassResult)


# ---------------------------------------------------------------------------
# PII Detector
# ---------------------------------------------------------------------------


class TestPIIDetector:
    def test_clean_text_passes(self, pii_detector):
        result = pii_detector.validate("Mehmet Bank offers 4.50% APY on savings accounts.", {})
        assert isinstance(result, PassResult)

    def test_credit_card_number_fails(self, pii_detector):
        result = pii_detector.validate("Your card number is 4111 1111 1111 1111.", {})
        assert isinstance(result, FailResult)

    def test_credit_card_masked_in_fix_value(self, pii_detector):
        result = pii_detector.validate("Card: 4111 1111 1111 1111", {})
        assert isinstance(result, FailResult)
        assert "4111 1111 1111 1111" not in result.fix_value

    def test_ssn_fails(self, pii_detector):
        result = pii_detector.validate("SSN: 456-78-9012", {})
        assert isinstance(result, FailResult)

    def test_ssn_masked_in_fix_value(self, pii_detector):
        result = pii_detector.validate("My SSN is 456-78-9012.", {})
        assert isinstance(result, FailResult)
        assert "456-78-9012" not in result.fix_value


# ---------------------------------------------------------------------------
# Competitor Detector
# ---------------------------------------------------------------------------


class TestCompetitorDetector:
    def test_clean_text_passes(self, competitor_detector):
        result = competitor_detector.validate("Mehmet Bank charges no monthly fees.", {})
        assert isinstance(result, PassResult)

    def test_competitor_name_fails(self, competitor_detector):
        result = competitor_detector.validate("Unlike Chase, we have better rates.", {})
        assert isinstance(result, FailResult)

    def test_competitor_replaced_in_fix_value(self, competitor_detector):
        result = competitor_detector.validate("Chase and Wells Fargo charge higher fees.", {})
        assert isinstance(result, FailResult)
        assert "Chase" not in result.fix_value
        assert "Wells Fargo" not in result.fix_value
        assert "[competitor bank]" in result.fix_value

    def test_multiple_competitors_all_replaced(self, competitor_detector):
        result = competitor_detector.validate("Both Chase and Citibank offer similar products.", {})
        assert isinstance(result, FailResult)
        assert result.fix_value.count("[competitor bank]") == 2

    def test_case_insensitive_detection(self, competitor_detector):
        result = competitor_detector.validate("unlike chase, our fees are lower.", {})
        assert isinstance(result, FailResult)
