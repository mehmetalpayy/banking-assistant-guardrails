from typing import Any, Dict, List

import nltk
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import pipeline as hf_pipeline

from guards import FailResult, PassResult, ValidationResult, Validator, register_validator

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)

NLI_PIPELINE = hf_pipeline("text-classification", model="GuardrailsAI/finetuned_nli_provenance")
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


@register_validator(name="hallucination_detector", data_type="string")
class HallucinationDetector(Validator):
    def _validate(self, value: Any, metadata: Dict[str, Any] = {}) -> ValidationResult:
        sources: List[str] = metadata.get("sources", [])
        if not sources:
            return PassResult()

        sentences = nltk.sent_tokenize(str(value))
        hallucinated: List[str] = []

        for sentence in sentences:
            if not self.is_grounded(sentence, sources):
                hallucinated.append(sentence)

        if hallucinated:
            return FailResult(
                error_message=(
                    f"Hallucination detected in {len(hallucinated)} sentence(s). "
                    f"First: '{hallucinated[0][:80]}'"
                ),
                fix_value=value,
            )
        return PassResult()

    def find_top_sources(self, sentence: str, sources: List[str], k: int = 3) -> List[str]:
        s_emb = EMBEDDING_MODEL.encode([sentence])[0]
        src_embs = EMBEDDING_MODEL.encode(sources)
        sims = np.dot(src_embs, s_emb) / (np.linalg.norm(src_embs, axis=1) * np.linalg.norm(s_emb))
        top_k = min(k, len(sources))
        top_indices = np.argsort(sims)[-top_k:][::-1]
        return [sources[i] for i in top_indices]

    def entails(self, premise: str, hypothesis: str) -> bool:
        result = NLI_PIPELINE({"text": premise, "text_pair": hypothesis})
        return result["label"] == "entailment"

    def is_grounded(self, sentence: str, sources: List[str]) -> bool:
        top = self.find_top_sources(sentence, sources)
        return any(self.entails(src, sentence) for src in top)
