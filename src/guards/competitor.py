import re
from typing import Any, Dict

from guards import FailResult, PassResult, ValidationResult, Validator, register_validator

COMPETITORS = [
    "Chase",
    "Bank of America",
    "Wells Fargo",
    "Citibank",
    "Citi Bank",
    "Goldman Sachs",
    "JPMorgan",
    "JP Morgan",
    "US Bank",
    "U.S. Bank",
    "Truist",
    "Capital One",
    "TD Bank",
    "PNC Bank",
    "HSBC",
    "Barclays",
    "Deutsche Bank",
    "BNP Paribas",
    "American Express",
    "Discover",
]

COMPETITOR_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in COMPETITORS) + r")\b",
    re.IGNORECASE,
)


@register_validator(name="competitor_detector", data_type="string")
class CompetitorDetector(Validator):
    def _validate(self, value: Any, metadata: Dict[str, Any] = {}) -> ValidationResult:
        matches = COMPETITOR_PATTERN.findall(str(value))
        if not matches:
            return PassResult()
        fixed = COMPETITOR_PATTERN.sub("[competitor bank]", str(value))
        unique = list({m.title() for m in matches})
        return FailResult(
            error_message=f"Competitor mention(s) detected: {unique}",
            fix_value=fixed,
        )
