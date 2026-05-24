<h1 align="center"><strong>Banking Assistant with Guardrails</strong></h1>

## Overview

A production-style bank customer service chatbot with integrated guardrails at every layer — input filtering, RAG-grounded responses, and multi-stage output validation.

Built as a hands-on implementation of safe and reliable AI patterns using the Guardrails AI framework, Microsoft Presidio, and HuggingFace NLI models.

## Architecture

```
User Input
    │
    ▼
┌─────────────────────┐
│   Topic Filter      │  LLM classifier — blocks off-topic messages
│   (Input Guard)     │  before they reach the LLM
└────────┬────────────┘
         │ PASS
         ▼
┌─────────────────────┐
│   RAG Retrieval     │  Semantic search over Mehmet Bank docs
│   (SimpleVectorDB)  │  Top-k chunks added as context
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   LLM (gpt-4.1)    │  Generates response grounded in context
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Output Guards     │  Applied sequentially, each fixes the text
│                     │  before passing to the next
│  1. Hallucination   │  NLI model verifies claims against sources
│  2. PII Detection   │  Presidio masks sensitive data
│  3. Competitor      │  Regex replaces competitor bank names
└────────┬────────────┘
         │
         ▼
    Final Response
```

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI `gpt-4.1` |
| Guardrails framework | Guardrails AI v0.5.3 |
| Topic filter | OpenAI structured outputs + Pydantic |
| Hallucination detection | `GuardrailsAI/finetuned_nli_provenance` (HuggingFace) |
| PII detection & masking | Microsoft Presidio |
| Competitor detection | Regex |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Logging | structlog |
| Package manager | uv |

## Repository Structure

```
src/
├── app.py              # CLI entry point
├── chatbot.py          # Orchestrates RAG + pipeline + OpenAI
├── pipeline.py         # Runs guardrails in sequence, logs results
├── rag.py              # Markdown chunking, embeddings, vector search
├── log_setup.py        # structlog configuration
└── guards/
    ├── __init__.py     # Re-exports Guardrails base types
    ├── topic_filter.py # Input guard — LLM classifier
    ├── hallucination.py# Output guard — NLI grounding check
    ├── pii.py          # Output guard — Presidio anonymization
    └── competitor.py   # Output guard — regex replacement

data/                   # Mehmet Bank knowledge base (Markdown)
├── accounts.md
├── credit_cards.md
├── interest_rates.md
└── company.md

tests/
├── test_guards.py      # Unit tests for each validator
└── test_pipeline.py    # Integration tests for the full pipeline
```

## Guardrails in Detail

### Input Guard — Topic Filter

Classifies every user message before it reaches the LLM. Uses `gpt-4.1` with structured output (Pydantic) to return a strict `BANKING | OFF_TOPIC` label. Off-topic messages are rejected immediately — no LLM call, no RAG lookup.

### Output Guard 1 — Hallucination Detection

Each sentence in the LLM response is checked against the RAG sources:
1. **Semantic search** finds the top-3 most relevant source chunks per sentence (cosine similarity).
2. **NLI model** checks whether each source *entails* the sentence.

Sentences not supported by any source are flagged.

### Output Guard 2 — PII Detection

Microsoft Presidio scans the response for sensitive entities:
`CREDIT_CARD`, `IBAN_CODE`, `EMAIL_ADDRESS`, `PERSON`, `US_SSN`, `US_BANK_NUMBER`, `US_PASSPORT`, `US_DRIVER_LICENSE`

Detected entities are replaced with typed placeholders (e.g. `<CREDIT_CARD>`).

### Output Guard 3 — Competitor Detection

Regex pattern matching against a list of 20 major competitor banks. Any mention is replaced with `[competitor bank]`.

## Installation and Setup

### Prerequisites

- Python 3.11
- [`uv`](https://github.com/astral-sh/uv) package manager
- [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone the Repository

```bash
git clone https://github.com/mehmetalpayy/banking-assistant-guardrails.git
cd banking-assistant-guardrails
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your key:

```env
OPENAI_API_KEY=sk-...
```

### 3. Install Dependencies

```bash
make install
```

This will install all Python dependencies and download the spaCy model required by Presidio.

## Running

```bash
make run
```

**Example session:**

```
Mehmet Bank Assistant — type 'exit' or 'quit' to stop, 'reset' to clear history.

You: What is the APR on the Mehmet Gold card?
Assistant: The purchase APR on the Mehmet Gold card is 17.99%–24.99% variable,
and the cash advance APR is 26.99%.

You: What is the weather in Istanbul?
Assistant: I'm sorry, I can only assist with banking-related questions such as
accounts, credit cards, interest rates, and payments.
```

Type `reset` to clear conversation history, `exit` or `quit` to stop.

## Testing

```bash
make test
```

26 tests covering all four validators and the full pipeline. Tests are fully mocked — no OpenAI API key required.

## Resources

- [Guardrails AI Documentation](https://www.guardrailsai.com/docs)
- [Microsoft Presidio](https://microsoft.github.io/presidio)
- [Sentence Transformers](https://www.sbert.net)
- [structlog](https://www.structlog.org)

## Troubleshooting

### `OPENAI_API_KEY` not found

Ensure `.env` exists and contains a valid key. The app loads it automatically at startup via `python-dotenv`.

### Models downloading on first run

`all-MiniLM-L6-v2` and `GuardrailsAI/finetuned_nli_provenance` are downloaded from HuggingFace on first use and cached locally. Subsequent starts load from cache in seconds.

### spaCy model not found

Run `uv run python -m spacy download en_core_web_lg` or simply `make install` again.

### Hallucination guard too aggressive

The NLI model flags sentences it cannot verify against the retrieved chunks. If legitimate responses are being flagged, lower the retrieval threshold in `chatbot.py`:

```python
results = self.db.query(user_message, k=3, threshold=0.9)  # increase threshold
```

## Contributing

1. Create a branch.
2. Make changes inside the relevant `src/` module.
3. Run `make lint` and `make test` before opening a PR.
4. Open a PR describing what changed and how it was tested.
