# Phase 5 — Policy Family Identity, Version Conflicts and Safety Review

## Purpose
Ensure that policy versions are grouped only when their shared identity is established, and that historical retrieval remains unambiguous.

## Family identity rules
- Accept an explicit caller-provided `policy_family_id` when supplied.
- Derive a stable family identifier deterministically when omitted, using collision-resistant behavior.
- Preserve an established family ID across versions.
- Do not silently assign legacy records to the same family when identity is uncertain.
- Reject ambiguous requests spanning multiple established families or return a clear ambiguity finding.
- Detect overlapping effective periods within a policy family.

## Historical retrieval invariants
- Preserve the distinction between lifecycle state and effective-date validity.
- Retrieve the policy version applicable to the requested date.
- Surface overlapping/ambiguous legacy records.
- Keep explicit family identity and historical retrieval semantics consistent through migrations.

## Verification focus
The source review records eight edge-case groups: deterministic derivation, family reuse, ambiguous multi-family requests, collision resistance, legacy uncertainty, overlapping legacy versions, explicit family IDs with historical retrieval, and PostgreSQL migration safety.

## Safety boundary
Policy RAG supports explanation and evidence discovery. It does not decide trade eligibility, override hard constraints, approve proposals or execute orders.
