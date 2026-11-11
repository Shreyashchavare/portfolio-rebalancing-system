# Final Test Hygiene — Remove Deprecation Warnings and Resolve Skipped Symlink Test

Repository: `E:\Yottaflex\portfolio-rebalancing-system`

Current baseline:
- 490 passed
- 1 skipped
- 7 warnings
- Python 3.12.10, Windows
- Branch main, baseline commit f322e8c
- Phase 7.2 changes are uncommitted. Preserve all existing work.

## Objective

Reduce avoidable pytest warnings to zero and investigate whether the skipped symlink security test can run successfully on this Windows environment without administrator privileges.

Do not suppress warnings globally, weaken tests, or make unrelated changes.

## 1. Fix deprecated HTTP 422 constants

The current test output reports six warnings for:

`HTTP_422_UNPROCESSABLE_ENTITY`

Search the entire repository for deprecated uses, including application code and tests.

Replace them with the supported equivalent for the installed FastAPI/Starlette versions, preserving HTTP status code 422 and existing API behavior.

Run focused tests for every affected API.

## 2. Resolve FastAPI / Starlette / httpx warning

The current test output reports one warning:

`Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

Inspect:
- requirements.txt
- Installed packages in `.venv`
- `tests/conftest.py`
- Usage of `TestClient` across tests

Determine whether installing or declaring `httpx2` cleanly resolves this warning without breaking API test execution or introducing new conflicts.

If supported, update `requirements.txt` and verify that `TestClient` works without the deprecation warning.

Do not disable warnings in `pytest.ini`.

## 3. Investigate and resolve skipped symlink security test

Inspect:
- `tests/test_policy_ingestion_and_vectors.py`
- The specific test currently being skipped
- The code under test: `app/services/policy_rag/document_extractor.py` or similar path-validation logic

Determine:
1. Exactly why the test is skipped.
2. What operating system permission or condition causes it.
3. Whether the test can be modified to run safely on Windows without administrator privileges while preserving its original security assertion: verifying that the path traversal defense blocks symlink / link-based directory escapes.

If Windows cannot create file symlinks without elevated privileges, determine whether:
- An alternative link creation technique is available in unprivileged mode (e.g. directory junction, if applicable).
- Or the test can verify path-resolution traversal defense directly using `resolve()` behavior against an existing path.

Do not remove the test.
Do not weaken the assertion.
If the test cannot run without administrator privileges on Windows, retain the explicit `pytest.skip` with clear explanation, but only after proving it cannot be solved.

## 4. Verification

Run:
1. Focused tests for affected areas.
2. Full test suite:
   Target: 491 passed (or 490 passed, 1 skipped if symlink is genuinely impossible), 0 warnings.
3. `git diff --check`.

## Deliverables

1. All deprecated HTTP 422 usages replaced with supported equivalents.
2. `httpx2` resolved and declared in `requirements.txt`.
3. Symlink security test either running and passing or documented with conclusive OS limitation evidence.
4. Pytest summary showing 0 warnings.
5. Save prompt and concise execution record in `prompts/phase-7/05-test-hygiene-deprecation-warnings.md`.
6. Do not commit or push.

---

## Execution Record

### 1. Root Cause Analysis

1. **HTTP 422 Constant Deprecation Warnings (6 warnings):**
   - Starlette 1.10.0 / FastAPI deprecated `status.HTTP_422_UNPROCESSABLE_ENTITY` in favor of RFC 9110 naming `status.HTTP_422_UNPROCESSABLE_CONTENT`.
   - Occurrences were present in:
     - `app/api/v1/analytics.py` (2 occurrences)
     - `app/api/v1/approvals.py` (2 occurrences)
     - `app/api/v1/policies.py` (1 occurrence)
     - `app/api/v1/rebalancing.py` (2 occurrences)
     - `app/api/v1/workflows.py` (2 occurrences)
     - `tests/test_approval_audit_api.py` (1 occurrence)
     - `tests/test_workflow_orchestration.py` (1 occurrence)

2. **Starlette TestClient Warning (1 warning):**
   - `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
   - Starlette 1.10.0's `starlette.testclient` checks for `httpx2` first and falls back to `httpx` with a deprecation warning.
   - Installing `httpx2>=2.16.0` satisfies this requirement cleanly without breaking `TestClient` or production `httpx` client logic.

3. **Skipped Symlink Security Test (1 skipped test):**
   - `test_document_extractor_symlink_defense` in `tests/test_policy_ingestion_and_vectors.py` called `Path.symlink_to()`.
   - On Windows without administrator privileges or Developer Mode enabled, creating file symlinks fails with `OSError: [WinError 1314] A required privilege is not held by the client`, causing the test to skip.
   - However, NTFS directory junctions (reparse points) can be created by unprivileged users on Windows via `_winapi.CreateJunction(src_dir, dst_junction)`.
   - When a junction is created inside `safe_dir` pointing to `outside_dir`, attempting to access `junction_dir / "outside_secret.txt"` causes `Path.resolve()` in `DocumentExtractor` to resolve to `outside_dir / "outside_secret.txt"` outside `allowed_root`, which triggers `PathTraversalError`.
   - Updating the test to fall back to an NTFS junction when file symlinks are unavailable exercises the exact same security boundary on Windows without requiring elevation or weakening any assertion.

### 2. Implementation Summary

1. **Replaced HTTP 422 constants:**
   - Updated `status.HTTP_422_UNPROCESSABLE_ENTITY` to `status.HTTP_422_UNPROCESSABLE_CONTENT` across all 7 affected files (11 total occurrences replaced).
   - Value remains 422, preserving all API contract responses.

2. **Added httpx2 dependency:**
   - Installed `httpx2==2.16.0` in the virtual environment.
   - Added `httpx2>=2.16.0` to `requirements.txt`.

3. **Resolved Symlink Defense Test on Windows:**
   - Modified `test_document_extractor_symlink_defense` in `tests/test_policy_ingestion_and_vectors.py`.
   - If `symlink_to` fails with `(OSError, NotImplementedError)` on `win32`, it creates an NTFS directory junction pointing to the external directory using `_winapi.CreateJunction`.
   - Verifies that extracting a file through the link raises `PathTraversalError`.
   - Retains `pytest.skip` only if neither file symlinks nor directory junctions can be created by the OS.

### 3. Verification Results

1. **Focused Symlink Test:**
   ```
   tests/test_policy_ingestion_and_vectors.py::TestVectorStore::test_document_extractor_symlink_defense PASSED [100%]
   1 passed in 0.85s (0 skipped)
   ```

2. **Focused API Tests:**
   - `tests/test_approval_audit_api.py`: 29 passed, 0 warnings
   - `tests/test_workflow_orchestration.py`: 32 passed, 0 warnings
   - `tests/test_portfolio_analytics_api.py`: 15 passed, 0 warnings

3. **Full Regression Test Suite:**
   ```
   ============================ 491 passed in 22.01s =============================
   ```
   - Total Tests: 491
   - Passed: 491
   - Failed: 0
   - Skipped: 0
   - Warnings: 0

4. **Git Diff Check:**
   `git diff --check` executed with code 0 (clean, no trailing whitespace or conflict markers).
