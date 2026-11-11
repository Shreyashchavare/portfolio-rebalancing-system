# Phase 5 — Final Policy Family Identity and Conflict Detection Correction

**Project**: `E:\Yottaflex\portfolio-rebalancing-system`  
**Phase**: 5.2 / Final Hardening — Policy Family Identity  
**Date**: 2026-11-11  
**Status**: PASSED (384 passed, 1 skipped, 0 failed across 385 tests)  
**Author**: Antigravity Pair Programming Agent  

---

## 1. Executive Summary

This report documents the architectural correction that replaces title-only policy family identification with an **explicit, stable policy family identifier** (`policy_family_id`). 

Previously, policy grouping and ambiguity detection relied on normalized document titles. This created two significant risks:
1. Two distinct, legitimate policies with identical or generic titles (e.g., *"Allocation Limits"*) would trigger false conflict warnings.
2. Incomplete or legacy records could be mistakenly merged if their titles coincided.

With this update:
- An explicit, indexed `policy_family_id` attribute has been added to the database models, schemas, and API contracts.
- Ingestion automatically derives and preserves a stable policy family identifier across versions when not supplied.
- Conflict detection evaluates `policy_family_id`, ensuring that distinct policy families with identical titles do not conflict, while concurrent active versions within the same family trigger an ambiguity warning.
- Legacy records without a family ID are safely isolated using a deterministic document-specific fallback (`LEGACY-DOC-{id}`), preventing silent merging of uncertain policies.
- A safe, backward-compatible SQL migration (`002_add_policy_family_id.sql`) has been prepared.
- All 385 test suite items were executed: **384 passed, 1 skipped** (Windows OS symlink defense), **0 failed**.

---

## 2. Architecture & Data Contracts

### 2.1 Database Model (`app/models/policy_document.py`)
`PolicyDocument` now includes `policy_family_id`:
```python
class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    policy_family_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    ...
```

To provide safe backwards compatibility without silent merging, an `effective_policy_family_id` property was added:
```python
@property
def effective_policy_family_id(self) -> str:
    """Return explicit policy_family_id if set, or documented unmerged fallback."""
    if self.policy_family_id and self.policy_family_id.strip():
        return self.policy_family_id.strip()
    return f"LEGACY-DOC-{self.id}"
```

### 2.2 Ingestion & API Schemas (`app/schemas/policy_rag.py`)
- `PolicyDocumentMetadata`: Added `policy_family_id: Optional[str] = Field(None, max_length=50)`.
- `PolicyIngestRequest`: Added `policy_family_id: Optional[str] = Field(None, max_length=50)`.
- `PolicyIngestResponse`: Added `policy_family_id: Optional[str] = None`.
- `PolicyDocumentResponse`: Added `policy_family_id: Optional[str] = None`.
- `PolicyDocumentDetailResponse`: Added `policy_family_id: Optional[str] = None`.
- `PolicySearchResult`: Added `policy_family_id: Optional[str] = None`.
- `PolicyCitation`: Added `policy_family_id: Optional[str] = None`.

---

## 3. Stable Family Derivation & Preservation

During document ingestion (`PolicyRAGService.ingest_document`), the system resolves `policy_family_id` using a three-tier resolution hierarchy:

```python
# 1. Explicit caller-provided family ID
if request.policy_family_id and request.policy_family_id.strip():
    family_id = request.policy_family_id.strip()
else:
    # 2. Re-use existing family ID from prior versions of the same policy title
    existing_family_doc = (
        self.session.query(PolicyDocument)
        .filter(PolicyDocument.title == request.title)
        .filter(PolicyDocument.policy_family_id.isnot(None))
        .first()
    )
    if existing_family_doc is not None and existing_family_doc.policy_family_id:
        family_id = existing_family_doc.policy_family_id
    else:
        # 3. Derive deterministic slug-based family ID from canonical title
        clean_title = re.sub(r"[^A-Za-z0-9]+", "-", request.title.strip().upper()).strip("-")
        family_id = f"FAM-{clean_title[:40]}"
```

### Key Behavioral Invariants:
1. **Never generates a different family ID for each document version**: When version 1.0 of *"Global Allocation Mandate"* is ingested, it derives `FAM-GLOBAL-ALLOCATION-MANDATE`. When version 2.0 is ingested later (even if `policy_family_id` is omitted in the request), it looks up existing records by title and reuses `FAM-GLOBAL-ALLOCATION-MANDATE`.
2. **Explicit overrides permitted**: Callers managing separate departmental mandates (e.g., *"Allocation Limits"* for Equity vs. *"Allocation Limits"* for Fixed Income) can pass explicit identifiers `FAM-EQUITY-LIMITS` and `FAM-FIXED-INCOME-LIMITS`.

---

## 4. Conflict Detection Using `policy_family_id`

In `PolicyRAGService.ask_question`, conflict detection now groups retrieved policy chunks by their stable policy family identifier rather than title alone:

```python
warnings: List[str] = []
requires_human_review = False
families_seen: Dict[str, Dict[str, str]] = {}

for c in retrieved_chunks:
    if c.policy_family_id and c.policy_family_id.strip():
        family_key = c.policy_family_id.strip()
    else:
        # Documented legacy fallback: isolate by document_id to avoid silently merging uncertain families
        family_key = f"LEGACY-DOC-{c.document_id}"

    if family_key in families_seen:
        prev = families_seen[family_key]
        if prev["version"] != c.document_version and prev["document_id"] != c.document_id:
            warn_msg = (
                f"Multiple active versions ({prev['version']} and {c.document_version}) "
                f"detected for policy family '{family_key}' ('{c.document_title}'). "
                f"Conflict or ambiguity detected."
            )
            if warn_msg not in warnings:
                warnings.append(warn_msg)
            requires_human_review = True
    else:
        families_seen[family_key] = {
            "version": c.document_version,
            "document_id": c.document_id,
            "title": c.document_title,
        }
```

### Verified Properties:
- **Identical Titles, Distinct Families**: Two policies with identical title *"Allocation Limits"* but distinct `policy_family_id` values (`FAM-EQUITY-LIMITS` vs `FAM-FIXED-INCOME-LIMITS`) do not conflict (`retrieval_status == "ANSWERED"`, `warnings == []`).
- **Overlapping Active Versions**: Two concurrent active documents with the same `policy_family_id` (`FAM-GLOBAL-GROWTH`) and different versions (v1.0 vs v2.0) produce an ambiguity warning and flag `requires_human_review = True`.
- **Non-Overlapping Historical Versions**: v1.0 (SUPERSEDED, 2025-01-01 to 2025-12-31) and v2.0 (ACTIVE, 2026-01-01 onwards) remain retrievable on their respective dates without false conflict.
- **Legacy Records Without Family ID**: Distinct legacy documents without `policy_family_id` receive unique `LEGACY-DOC-{id}` keys, preventing accidental merging.

---

## 5. Seed Documents Updated

The synthetic policy seed files in `policy_documents/` have been updated with explicit policy family identifiers:

1. **`policy_documents/global_equity_mandate_v1.md`**:
   - `Policy Family ID`: `FAM-GLOBAL-EQUITY`
   - `Version`: 1.0 (SUPERSEDED)
2. **`policy_documents/global_equity_mandate_v2.md`**:
   - `Policy Family ID`: `FAM-GLOBAL-EQUITY`
   - `Version`: 2.0 (ACTIVE)
3. **`policy_documents/esg_exclusion_policy_v1.md`**:
   - `Policy Family ID`: `FAM-ESG-EXCLUSION`
   - `Version`: 1.0 (ACTIVE)
4. **`policy_documents/temporary_cash_buffer_policy_2026.md`**:
   - `Policy Family ID`: `FAM-TEMPORARY-CASH-BUFFER`
   - `Version`: 1.0 (ACTIVE)

---

## 6. PostgreSQL Database Migration

The follow-up migration script was created at:  
`docs/migrations/002_add_policy_family_id.sql`

```sql
-- Migration 002: Add policy_family_id to policy_documents
-- Database: PostgreSQL
-- Description: Add policy_family_id column and index for stable policy family identity and conflict detection.

BEGIN;

-- 1. Add policy_family_id column (nullable to safely preserve existing legacy records)
ALTER TABLE policy_documents 
ADD COLUMN IF NOT EXISTS policy_family_id VARCHAR(50);

-- 2. Create index on policy_family_id for fast family lookups and conflict detection
CREATE INDEX IF NOT EXISTS idx_policy_documents_family_id 
ON policy_documents(policy_family_id);

COMMIT;
```

> [!NOTE]
> In accordance with our verification standard, this SQL script is verified syntactically and idempotently for PostgreSQL. Migration application is not claimed against a live production PostgreSQL cluster since the test suite executes in local SQLite/in-memory environments.

---

## 7. TDD Verification Evidence

### 7.1 RED Phase
Before updating the model and schemas, new tests were authored in `tests/test_policy_rag_api.py`. Running pytest demonstrated failures across 4 new assertions:
```
FAILED tests/test_policy_rag_api.py::TestPolicyRetrievalAndVersioning::test_identical_titles_with_distinct_family_ids_do_not_conflict - TypeError: 'policy_family_id' is an invalid keyword argument for PolicyDocument
FAILED tests/test_policy_rag_api.py::TestPolicyRetrievalAndVersioning::test_overlapping_active_versions_of_same_family_id_trigger_conflict - TypeError: 'policy_family_id' is an invalid keyword argument for PolicyDocument
FAILED tests/test_policy_rag_api.py::TestPolicyRetrievalAndVersioning::test_legacy_documents_without_family_id_do_not_silently_merge - TypeError: 'policy_family_id' is an invalid keyword argument for PolicyDocument
FAILED tests/test_policy_rag_api.py::TestPolicyAPIEndpoints::test_ingestion_derives_and_preserves_stable_family_id - AttributeError: 'PolicyIngestResponse' object has no attribute 'policy_family_id'
```

### 7.2 GREEN Phase
Following the implementation of `policy_family_id` across model, schemas, vector store, and service:
```bash
pytest tests/test_policy_rag_api.py -k "family" -v
# Output: 4 passed, 22 deselected in 1.08s
```

### 7.3 Full Regression Suite
- **Policy Ingestion & Vector Tests**:
  ```bash
  pytest tests/test_policy_ingestion_and_vectors.py -v
  # Output: 38 passed, 1 skipped in 1.89s
  ```
- **Policy RAG API Tests**:
  ```bash
  pytest tests/test_policy_rag_api.py -v
  # Output: 26 passed, 3 warnings in 1.40s
  ```
- **Repository Full Test Suite**:
  ```bash
  pytest -q
  # Output: 384 passed, 1 skipped, 5 warnings in 7.44s
  ```
- **Git Diff Hygiene**:
  ```bash
  git diff --check
  # Output: Exit code 0 (clean, zero trailing whitespaces, zero merge conflict markers)
  ```

---

## 8. Remaining Limitations & Honest Disclosure

1. **Live PostgreSQL Verification**: Migration `002_add_policy_family_id.sql` was verified by static analysis and SQLite DDL compatibility; live execution on a production PostgreSQL database will occur during infrastructure deployment.
2. **Legacy Backfill Strategy**: Existing records in legacy systems with `policy_family_id = NULL` are assigned safe isolated keys (`LEGACY-DOC-{id}`). If operators wish to join existing historical records into a single family retroactively, an administrative data migration script to populate `policy_family_id` should be run prior to production cutover.

