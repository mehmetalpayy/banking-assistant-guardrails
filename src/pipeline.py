import time
from dataclasses import dataclass, field
from typing import List, Optional

import structlog
from guardrails import OnFailAction
from guardrails.validator_base import FailResult

from guards.competitor import CompetitorDetector
from guards.hallucination import HallucinationDetector
from guards.pii import PIIDetector
from guards.topic_filter import BankingTopicFilter

log = structlog.get_logger()


@dataclass
class PipelineResult:
    response: str
    blocked: bool = False
    block_reason: Optional[str] = None
    guard_log: List[dict] = field(default_factory=list)


class GuardrailPipeline:
    def __init__(self) -> None:
        self.topic_guard = BankingTopicFilter(on_fail=OnFailAction.FIX)
        self.output_guards = [
            ("hallucination", HallucinationDetector(on_fail=OnFailAction.FIX)),
            ("pii", PIIDetector(on_fail=OnFailAction.FIX)),
            ("competitor", CompetitorDetector(on_fail=OnFailAction.FIX)),
        ]

    def check_input(self, user_message: str) -> PipelineResult:
        log.info("guard.input", message=user_message[:80])
        start = time.time()
        result = self.topic_guard.validate(user_message, {})
        elapsed = int((time.time() - start) * 1000)

        if isinstance(result, FailResult):
            log.warning("guard.topic_filter", status="BLOCK", elapsed_ms=elapsed)
            return PipelineResult(
                response=result.fix_value or user_message,
                blocked=True,
                block_reason="off_topic",
            )
        log.info("guard.topic_filter", status="PASS", elapsed_ms=elapsed)
        return PipelineResult(response=user_message)

    def check_output(self, response: str, sources: List[str]) -> PipelineResult:
        current = response
        guard_log: List[dict] = []

        for name, validator in self.output_guards:
            start = time.time()
            metadata = {"sources": sources} if name == "hallucination" else {}
            try:
                result = validator.validate(current, metadata=metadata)
                elapsed = int((time.time() - start) * 1000)
                if isinstance(result, FailResult) and result.fix_value is not None:
                    current = result.fix_value
                status = "PASS" if not isinstance(result, FailResult) else "FIX"
                log.info(f"guard.{name}", status=status, elapsed_ms=elapsed)
                guard_log.append({"guard": name, "status": status, "elapsed_ms": elapsed})
            except Exception as exc:
                elapsed = int((time.time() - start) * 1000)
                log.error(f"guard.{name}", status="ERROR", error=str(exc), elapsed_ms=elapsed)
                guard_log.append({"guard": name, "status": "ERROR", "elapsed_ms": elapsed})

        return PipelineResult(response=current, guard_log=guard_log)
