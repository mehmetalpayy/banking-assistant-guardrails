import time
from typing import List

import structlog
from openai import OpenAI

from pipeline import GuardrailPipeline
from rag import SimpleVectorDB

log = structlog.get_logger()

SYSTEM_PROMPT = """\
You are a helpful customer service assistant for Mehmet Bank.
Answer questions based solely on the context provided.

Rules:
- Only answer questions about Mehmet Bank products and services.
- If the context does not contain the answer, say: "I don't have that information. \
Please contact our support team at 1-800-668-2265."
- Never mention competitor banks.
- Never reveal personal account details or invent figures not in the context.
- Be concise and professional."""


class BankingChatbot:
    def __init__(self, data_dir: str = "data/") -> None:
        self.client = OpenAI()
        self.db = SimpleVectorDB.from_files(data_dir)
        self.pipeline = GuardrailPipeline()
        self.history: List[dict] = []

    def chat(self, user_message: str) -> str:
        input_result = self.pipeline.check_input(user_message)
        if input_result.blocked:
            return input_result.response

        t0 = time.time()
        results = self.db.query(user_message, k=3, threshold=0.9)
        context = self.db.format_context(results)
        sources = [text for text, _ in results]
        log.info("rag.retrieved", chunks=len(results), elapsed_ms=int((time.time() - t0) * 1000))

        augmented = (
            f"Context:\n{context}\n\nUser question: {user_message}" if context else user_message
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.history,
            {"role": "user", "content": augmented},
        ]

        t0 = time.time()
        completion = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            temperature=0.0,
        )
        elapsed = int((time.time() - t0) * 1000)
        raw = completion.choices[0].message.content
        tokens = completion.usage.total_tokens
        log.info("llm.response", tokens=tokens, elapsed_ms=elapsed)

        output_result = self.pipeline.check_output(raw, sources)
        final = output_result.response

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": final})

        return final

    def reset(self) -> None:
        self.history = []
