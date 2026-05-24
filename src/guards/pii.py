from typing import Any, Dict

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from guards import FailResult, PassResult, ValidationResult, Validator, register_validator

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

PII_ENTITIES = [
    "CREDIT_CARD",
    "IBAN_CODE",
    "EMAIL_ADDRESS",
    "PERSON",
    "US_SSN",
    "US_BANK_NUMBER",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
]


@register_validator(name="pii_detector", data_type="string")
class PIIDetector(Validator):
    def _validate(self, value: Any, metadata: Dict[str, Any] = {}) -> ValidationResult:
        results = analyzer.analyze(
            text=str(value),
            entities=PII_ENTITIES,
            language="en",
        )
        if not results:
            return PassResult()

        anonymized = anonymizer.anonymize(text=str(value), analyzer_results=results)
        detected = list({r.entity_type for r in results})
        return FailResult(
            error_message=f"PII detected and masked: {detected}",
            fix_value=anonymized.text,
        )
