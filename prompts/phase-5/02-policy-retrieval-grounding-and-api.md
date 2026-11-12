# Phase 5 — Policy Retrieval, Grounded Answers and API

## Objective
Provide policy-grounded answers with citations while preserving temporal validity and clear LLM boundaries.

## Retrieval and temporal semantics
- Retrieve relevant policy chunks using embeddings and similarity search.
- Respect document version, effective dates and lifecycle status.
- Distinguish current policies from historical versions.
- Do not treat a document's lifecycle status as a substitute for its temporal validity.
- Detect overlapping or ambiguous policy versions rather than silently choosing one.

## Grounded answers
- Answers must be supported by retrieved policy passages.
- Return source citations that identify the originating document/chunk.
- Validate that claims are grounded in retrieved evidence.
- If evidence is insufficient or conflicting, say so rather than inventing a policy answer.
- LLM output is explanatory; it must not override deterministic financial rules or approval controls.

## Security
- Treat retrieved documents and user-provided content as untrusted input.
- Defend against prompt injection in policy documents.
- Keep system instructions separate from retrieved content.
- Handle model unavailability and malformed model output gracefully.
- Do not leak secrets, internal errors or unrelated documents.

## API and tests
Expose policy ingestion/retrieval/answer operations through the existing FastAPI conventions. Test temporal retrieval, citations, grounding, conflicting policies, prompt injection, model failure and safe API error behavior.
