from typing import Any, Dict, Literal

from openai import OpenAI
from pydantic import BaseModel

from guards import FailResult, PassResult, ValidationResult, Validator, register_validator

CLASSIFIER_PROMPT = """\
You are a classifier for a bank customer service chatbot.
Determine whether the user message below is related to banking services.

Banking topics include: accounts, savings, checking, deposits, withdrawals,
credit cards, debit cards, interest rates, APR, loans, transfers,
payments, fees, transaction limits, and general bank information.

User message: {message}"""

REJECTION_MESSAGE = (
    "I'm sorry, I can only assist with banking-related questions "
    "such as accounts, credit cards, interest rates, and payments. "
    "Please ask me something about Mehmet Bank's products or services."
)


class TopicClassification(BaseModel):
    label: Literal["BANKING", "OFF_TOPIC"]


@register_validator(name="banking_topic_filter", data_type="string")
class BankingTopicFilter(Validator):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.client = OpenAI()

    def _validate(self, value: Any, metadata: Dict[str, Any] = {}) -> ValidationResult:
        response = self.client.chat.completions.parse(
            model="gpt-4.1",
            messages=[{"role": "user", "content": CLASSIFIER_PROMPT.format(message=value)}],
            temperature=0.0,
            response_format=TopicClassification,
        )
        classification = response.choices[0].message.parsed
        if classification.label != "BANKING":
            return FailResult(
                error_message="Off-topic message detected.",
                fix_value=REJECTION_MESSAGE,
            )
        return PassResult()
