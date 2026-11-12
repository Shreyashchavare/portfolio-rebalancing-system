# Phase 6 — Grounded Explanation Service

## Objective
Generate clear explanations for workflow results using structured facts and cited policy evidence.

## Required behavior
- Accept structured workflow/analytics/rebalancing results and retrieved policy evidence.
- Produce a structured explanation with findings, rationale, risks, exceptions and citations.
- Validate that citations refer to retrieved evidence.
- Prevent unsupported claims; missing evidence must be stated explicitly.
- Keep financial calculations and constraint decisions outside the LLM.
- Treat all retrieved documents and generated text as untrusted until validated.
- Handle unavailable models, malformed responses and timeouts gracefully.

## Workflow integration
Attach explanations to the relevant workflow result without changing the underlying financial decisions or approval state.

## Exclusions
The explanation service must not generate or modify trades, decide whether a hard constraint passes, approve/reject proposals, execute orders or invent policy.

## Tests
Cover grounded and ungrounded claims, valid/invalid citations, insufficient evidence, conflicting policy evidence, model failure and workflow integration.
