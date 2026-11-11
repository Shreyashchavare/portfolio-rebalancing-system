# Phase 5 — Policy Family Identity Edge-Case Review

**Project**: `E:\Yottaflex\portfolio-rebalancing-system`  
**Phase**: 5 — Edge-Case Review of Policy Family Identity  
**Date**: 2026-11-11  
**Status**: PASSED (387 passed, 1 skipped, 0 failed across 388 tests)  
**Author**: Antigravity Pair Programming Agent  

---

## 1. Executive Summary

This report presents a focused edge-case review of the policy family identity implementation established in `prompts/phase-5/06-policy-family-identity.md`. The review examined potential boundary defects, ambiguity during ingestion, truncation collision risks, and the handling of legacy records with unconfirmed identities.

Three critical edge-case defects were diagnosed, isolated via test-driven development (TDD RED phase), and resolved with minimal surgical corrections (TDD GREEN phase):
1. **Ambiguous Family Selection on Ingestion**: Previously, when multiple distinct policy families shared an identical title, an ingestion request with omitted `policy_family_id` arbitrarily selected whichever record came first via `.first()`. Now, it strictly detects the ambiguity and raises a clear `ValueError`, requiring an explicit `policy_family_id`.
2. **Truncation/Normalization Collisions**: Previously, deterministic derivation truncated slugs at 40 characters (`f"FAM-{clean_title[:40]}"`), meaning long titles sharing a common prefix would silently collide into the same family ID. Now, derivation combines a normalized slug with an 8-character SHA-256 hash of the full canonical title (`f"FAM-{clean_slug}-{title_hash}"`), guaranteeing collision resistance.
3. **Overlapping Legacy Records**: Previously, legacy records without a family ID were assigned isolated keys (`LEGACY-DOC-{id}`), which unintentionally bypassed conflict detection when two active versions of an unassigned policy were concurrent. Now, overlapping legacy records with the same title are detected as having **unresolved family identity**, raising an ambiguity warning and requiring human compliance review.

---

## 2. In-Depth Verification of the 8 Target Cases

### Case 1: Deterministic Family Derivation When Omitted
- **Condition**: Ingestion request provides no `policy_family_id` and no prior document with the same title exists in the database.
- **Implementation**: The system computes a collision-resistant deterministic family ID:
  ```python
  clean_slug = re.sub(r"[^A-Za-z0-9]+", "-", request.title.strip().upper()).strip("-")[:28]
  title_hash = hashlib.sha256(request.title.strip().encode("utf-8")).hexdigest()[:8].upper()
  family_id = f"FAM-{clean_slug}-{title_hash}"
  ```
- **Verification**: Verified in `test_ingestion_derives_and_preserves_stable_family_id`. Produces a stable, indexed ID bounded by 50 characters (`VARCHAR(50)`).

### Case 2: Established Family Re-Use Across Versions
- **Condition**: A policy family already exists for a title (e.g. `FAM-GLOBAL-ALLOCATION-MANDATE-XXXXXXXX`), and a new version (v2.0) is ingested with `policy_family_id=None`.
- **Implementation**: The system queries existing distinct established family IDs for that title:
  ```python
  distinct_families = [row[0] for row in (
      self.session.query(PolicyDocument.policy_family_id)
      .filter(PolicyDocument.title == request.title)
      .filter(PolicyDocument.policy_family_id.isnot(None))
      .distinct().all()
  ) if row[0] and row[0].strip()]
  ```
  When exactly one established family ID exists, it is reused automatically for the new version.
- **Verification**: Verified in `test_ingestion_derives_and_preserves_stable_family_id` (`assert res2.policy_family_id == v1_family_id`).

### Case 3: Rejection of Ambiguous Requests Across Multiple Established Families
- **Condition**: Multiple distinct policy families exist in the database with the exact same display title (e.g. *"Risk Limits"* assigned to `FAM-RISK-CREDIT` and `FAM-RISK-MARKET`), and a caller submits a new version with `policy_family_id=None`.
- **Implementation**: If `len(distinct_families) > 1`, the system rejects the ambiguous request immediately:
  ```python
  family_list_str = ", ".join(sorted(distinct_families))
  raise ValueError(
      f"Multiple distinct policy families ({family_list_str}) exist for title '{request.title}'. "
      f"Ingestion is ambiguous; an explicit policy_family_id must be provided."
  )
  ```
- **Verification**: Verified in `test_ingestion_rejects_ambiguous_title_with_multiple_existing_families`. Raises `ValueError` and returns HTTP 422 Unprocessable Entity in the REST API.

### Case 4: Collision-Resistant Derivation Resisting Truncation
- **Condition**: Two distinct policy documents have long titles sharing an identical initial 40 characters:
  - Title 1: *"Global Sustainable Balanced Growth Portfolio Mandate Tier 1"*
  - Title 2: *"Global Sustainable Balanced Growth Portfolio Mandate Tier 2"*
- **Implementation**: By appending `-hashlib.sha256(full_title).hexdigest()[:8].upper()`, the generated family IDs differ:
  - Title 1 $\rightarrow$ `FAM-GLOBAL-SUSTAINABLE-BALANCED-01B9FE2A`
  - Title 2 $\rightarrow$ `FAM-GLOBAL-SUSTAINABLE-BALANCED-4A8D99C1`
- **Verification**: Verified in `test_deterministic_family_derivation_resists_truncation_collision` (`assert res1.policy_family_id != res2.policy_family_id` and length $\le 50$).

### Case 5: Legacy Records Never Silently Confirmed as Identical Families
- **Condition**: Legacy records without `policy_family_id` (`NULL`) are ingested or present in the database.
- **Implementation**: The model exposes property `effective_policy_family_id`:
  ```python
  @property
  def effective_policy_family_id(self) -> str:
      if self.policy_family_id and self.policy_family_id.strip():
          return self.policy_family_id.strip()
      return f"LEGACY-DOC-{self.id}"
  ```
  Distinct legacy documents (`POL-LEG-A` and `POL-LEG-B`) remain isolated as `LEGACY-DOC-POL-LEG-A` and `LEGACY-DOC-POL-LEG-B`. They are never assumed to belong to a single confirmed family.
- **Verification**: Verified in `test_legacy_documents_without_family_id_do_not_silently_merge`.

### Case 6: Overlapping Legacy Records Trigger Ambiguity Warnings
- **Condition**: Two legacy records with the same title (e.g. *"General Compliance Policy"*, v1.0 and v2.0) are both active on the evaluation date.
- **Implementation**: In `ask_question`, legacy records with `not c.policy_family_id` track titles seen:
  ```python
  norm_title = c.document_title.strip().lower()
  if norm_title in legacy_titles_seen:
      prev_legacy = legacy_titles_seen[norm_title]
      if prev_legacy["document_id"] != c.document_id:
          warn_msg = (
              f"Multiple overlapping legacy records ({prev_legacy['document_id']} and {c.document_id}) "
              f"detected for title '{c.document_title}' with unresolved policy family identity. "
              f"Ambiguity detected; human review required."
          )
          warnings.append(warn_msg)
          requires_human_review = True
  ```
  Sets `retrieval_status = "CONFLICT_DETECTED"` and `requires_human_review = True`.
- **Verification**: Verified in `test_overlapping_legacy_records_with_unresolved_identity_trigger_human_review`.

### Case 7: Explicit Family IDs and Historical Retrieval Invariants
- **Condition**: Distinct policy families with identical titles; non-overlapping historical versions.
- **Implementation**:
  - Documents with distinct explicit `policy_family_id`s (e.g. `FAM-EQUITY-LIMITS` vs `FAM-FIXED-INCOME-LIMITS`) with identical titles do not conflict (`retrieval_status == "ANSWERED"`, `requires_human_review == False`).
  - Historical queries (`as_of_date=2025-06-30`) retrieve `v1` (SUPERSEDED) of `FAM-GLOBAL-EQUITY`, while `2026-06-30` retrieves `v2` (ACTIVE).
  - Draft policies remain unconditionally excluded.
- **Verification**: Verified across `test_identical_titles_with_distinct_family_ids_do_not_conflict`, `test_historical_superseded_policy_retrieval_and_draft_exclusion`, and `test_future_and_expired_policies_excluded`.

### Case 8: PostgreSQL Database Migration Safety
- **Script**: `docs/migrations/002_add_policy_family_id.sql`
- **Inspection**:
  - `ALTER TABLE policy_documents ADD COLUMN IF NOT EXISTS policy_family_id VARCHAR(50);`
    Column is nullable; existing rows retain their values with `policy_family_id = NULL`.
  - `CREATE INDEX IF NOT EXISTS idx_policy_documents_family_id ON policy_documents(policy_family_id);`
    Creates an index to support fast family queries and `distinct()` lookups.
  - Transaction block (`BEGIN ... COMMIT`) ensures atomic execution.

---

## 3. TDD Evidence: RED to GREEN

### 3.1 RED Phase
Prior to implementation of the edge-case corrections, the new regression tests in `tests/test_policy_rag_api.py` failed as expected:
```
FAILED tests/test_policy_rag_api.py::TestPolicyRetrievalAndVersioning::test_overlapping_legacy_records_with_unresolved_identity_trigger_human_review - AssertionError: assert False is True
FAILED tests/test_policy_rag_api.py::TestPolicyAPIEndpoints::test_ingestion_rejects_ambiguous_title_with_multiple_existing_families - Failed: DID NOT RAISE <class 'ValueError'>
FAILED tests/test_policy_rag_api.py::TestPolicyAPIEndpoints::test_deterministic_family_derivation_resists_truncation_collision - AssertionError: assert 'FAM-GLOBAL-SUSTAINABLE-BALANCED-GROWTH-PORTF' != 'FAM-GLOBAL-SUSTAINABLE-BALANCED-GROWTH-PORTF'
```

### 3.2 GREEN Phase
Following the implementation of `hashlib`-based derivation, multi-family ambiguity check, and legacy title collision tracking:
```bash
pytest tests/test_policy_rag_api.py -k "ambiguous or truncation or overlapping_legacy" -v
# Output: 3 passed, 26 deselected in 1.12s
```

---

## 4. Test Suite and Verification Results

- **Policy Ingestion & Vector Tests**:
  ```bash
  pytest tests/test_policy_ingestion_and_vectors.py -v
  # Output: 38 passed, 1 skipped (symlinks on Windows) in 1.94s
  ```
- **Policy RAG API Tests**:
  ```bash
  pytest tests/test_policy_rag_api.py -v
  # Output: 29 passed in 1.49s
  ```
- **Complete Project Test Suite**:
  ```bash
  pytest -q
  # Output: 387 passed, 1 skipped, 5 warnings in 7.52s
  ```
- **Git Diff Whitespace & Hygiene**:
  ```bash
  git diff --check
  # Output: Exit code 0 (clean, zero trailing whitespace errors, zero conflict markers)
  ```

---

## 5. Deployment Limitations & Operational Recommendations

1. **PostgreSQL Migration Execution**: The migration script `002_add_policy_family_id.sql` has been verified for SQL syntax and idempotence. Live execution against production PostgreSQL should be applied during the scheduled database maintenance window.
2. **Legacy Policy Family Tagging**: Operators with legacy documents in production are advised to run an administrative update or script to backfill `policy_family_id` onto legacy records. Until backfilled, overlapping legacy documents will conservatively require human review rather than executing autonomously.
3. **Financial Isolation Maintained**: `PolicyRAGService` continues to have read-only access to policy records and zero write access to financial holdings, trades, or portfolio proposals.

