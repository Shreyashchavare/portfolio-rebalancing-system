"""Tests for automated policy document discovery, metadata extraction, and RAG ingestion."""

from datetime import date
from pathlib import Path
import subprocess
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.policy_document import PolicyChunk, PolicyDocument
from app.services.policy_rag.embedding_service import FakeEmbeddingService
from scripts.ingest_policies import (
    discover_policy_files,
    extract_document_metadata,
    ingest_policy_batch,
    main,
)
from scripts.seed_database import apply_migrations


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Return path to an isolated SQLite file database."""
    return tmp_path / "test_policy_rag.db"


@pytest.fixture
def temp_db_url(temp_db_path: Path) -> str:
    """Return connection URL for isolated testing."""
    return f"sqlite:///{temp_db_path.as_posix()}"


@pytest.fixture
def initialized_db(temp_db_url: str) -> str:
    """Initialize database schema with all 4 migrations."""
    engine = create_engine(temp_db_url)
    apply_migrations(engine, Path("docs/migrations"))
    engine.dispose()
    return temp_db_url


@pytest.fixture
def sample_policies_dir(tmp_path: Path) -> Path:
    """Create sample policy documents (Markdown, TXT) for testing."""
    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()

    # 1. Valid markdown with structured metadata block
    doc1 = policies_dir / "esg_exclusion_v1.md"
    doc1.write_text(
        "# ESG Exclusion Policy (Version 1.0)\n\n"
        "## Scope and Objectives\n"
        "- **Policy Family ID**: FAM-ESG-EXCLUSION\n"
        "- **Effective From**: 2026-01-01\n"
        "- **Effective To**: Ongoing (None)\n"
        "- **Status**: ACTIVE\n\n"
        "## Exclusion Criteria\n"
        "Zero tobacco and controversial weapons.\n",
        encoding="utf-8",
    )

    # 2. Valid plain text document
    doc2 = policies_dir / "liquidity_rule_v1.txt"
    doc2.write_text(
        "Standard liquidity policy requiring at least 5% cash reserves in all portfolios.\n",
        encoding="utf-8",
    )

    # 3. Invalid dates policy
    doc3 = policies_dir / "invalid_dates_policy.md"
    doc3.write_text(
        "# Invalid Bounds Policy\n\n"
        "- **Effective From**: 2026-12-31\n"
        "- **Effective To**: 2026-01-01\n"
        "- **Status**: ACTIVE\n\n"
        "Content.\n",
        encoding="utf-8",
    )

    # 4. Ignored file
    (policies_dir / ".gitkeep").write_text("", encoding="utf-8")

    return policies_dir


def test_cli_help():
    """Verify scripts/ingest_policies.py exposes standard CLI help flag."""
    cmd = [sys.executable, "scripts/ingest_policies.py", "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Policy document discovery and RAG ingestion automation" in result.stdout
    assert "--policies-dir" in result.stdout
    assert "--dry-run" in result.stdout


def test_discover_policy_files(sample_policies_dir: Path):
    """Verify supported policy files are discovered in deterministic alphabetical order."""
    files = discover_policy_files(sample_policies_dir)
    filenames = [f.name for f in files]
    assert "esg_exclusion_v1.md" in filenames
    assert "liquidity_rule_v1.txt" in filenames
    assert "invalid_dates_policy.md" in filenames
    assert ".gitkeep" not in filenames
    assert filenames == sorted(filenames)


def test_extract_metadata_from_markdown(sample_policies_dir: Path):
    """Verify structured metadata is parsed from document headings and bullet points."""
    file_path = sample_policies_dir / "esg_exclusion_v1.md"
    meta = extract_document_metadata(file_path)

    assert meta["title"] == "ESG Exclusion Policy"
    assert meta["version"] == "1.0"
    assert meta["policy_family_id"] == "FAM-ESG-EXCLUSION"
    assert meta["effective_from"] == date(2026, 1, 1)
    assert meta["effective_to"] is None
    assert meta["status"] == "ACTIVE"


def test_extract_metadata_from_plain_text(sample_policies_dir: Path):
    """Verify plain text files receive fallback metadata gracefully."""
    file_path = sample_policies_dir / "liquidity_rule_v1.txt"
    meta = extract_document_metadata(file_path)

    assert meta["title"] == "Liquidity Rule V1"
    assert meta["version"] == "1.0"
    assert meta["effective_from"] == date.today()
    assert meta["status"] == "ACTIVE"


def test_dry_run_mode(initialized_db: str, sample_policies_dir: Path):
    """Verify dry-run mode validates files without modifying the database."""
    exit_code = main([
        "--database-url", initialized_db,
        "--policies-dir", str(sample_policies_dir),
        "--dry-run",
        "--use-fake-embeddings",
    ])
    assert exit_code == 0

    engine = create_engine(initialized_db)
    with Session(engine) as session:
        doc_count = session.query(PolicyDocument).count()
        assert doc_count == 0
    engine.dispose()


def test_ingest_policy_batch_success_and_error_handling(initialized_db: str, sample_policies_dir: Path):
    """Verify valid policies ingest successfully and invalid dates are recorded as failed."""
    engine = create_engine(initialized_db)
    fake_embedding = FakeEmbeddingService(dimension=384)

    results = ingest_policy_batch(
        engine=engine,
        policies_dir=sample_policies_dir,
        embedding_service=fake_embedding,
    )

    # 2 succeeded (esg_exclusion, liquidity_rule), 1 failed (invalid_dates)
    succeeded = [r for r in results if r["status"] == "SUCCESS"]
    failed = [r for r in results if r["status"] == "FAILED"]
    skipped = [r for r in results if r["status"] == "SKIPPED"]

    assert len(succeeded) == 2
    assert len(failed) == 1
    assert "cannot be after effective_to" in failed[0]["error"]
    assert len(skipped) == 0

    with Session(engine) as session:
        doc_count = session.query(PolicyDocument).count()
        assert doc_count == 2
        chunk_count = session.query(PolicyChunk).count()
        assert chunk_count > 0
    engine.dispose()


def test_repeated_ingestion_skips_duplicates(initialized_db: str, sample_policies_dir: Path):
    """Verify repeated execution skips already-ingested documents safely without errors."""
    engine = create_engine(initialized_db)
    fake_embedding = FakeEmbeddingService(dimension=384)

    # First run
    ingest_policy_batch(
        engine=engine,
        policies_dir=sample_policies_dir,
        embedding_service=fake_embedding,
    )

    # Second run on same dataset
    results2 = ingest_policy_batch(
        engine=engine,
        policies_dir=sample_policies_dir,
        embedding_service=fake_embedding,
    )

    succeeded2 = [r for r in results2 if r["status"] == "SUCCESS"]
    skipped2 = [r for r in results2 if r["status"] == "SKIPPED"]
    failed2 = [r for r in results2 if r["status"] == "FAILED"]

    assert len(succeeded2) == 0
    assert len(skipped2) == 2
    assert len(failed2) == 1  # Invalid date document still fails validation
    engine.dispose()


def test_main_cli_end_to_end(initialized_db: str, sample_policies_dir: Path):
    """Verify main() CLI processes batch, outputs reports, and exits cleanly."""
    exit_code = main([
        "--database-url", initialized_db,
        "--policies-dir", str(sample_policies_dir),
        "--use-fake-embeddings",
    ])
    assert exit_code == 0

    engine = create_engine(initialized_db)
    with Session(engine) as session:
        doc_count = session.query(PolicyDocument).count()
        assert doc_count == 2
    engine.dispose()


def test_extract_metadata_disallows_companion_file_path_override(sample_policies_dir: Path):
    """Verify companion JSON metadata file_path cannot override discovered file's actual resolved path."""
    import json
    doc = sample_policies_dir / "secure_policy_v1.md"
    doc.write_text("# Secure Policy\n\n- **Effective From**: 2026-01-01\n", encoding="utf-8")

    # Companion metadata attempting path escape via file_path field
    meta_file = sample_policies_dir / "secure_policy_v1.md.json"
    meta_file.write_text(
        json.dumps({
            "title": "Overridden Title",
            "file_path": "C:\\Windows\\System32\\drivers\\etc\\hosts",
        }),
        encoding="utf-8",
    )

    metadata = extract_document_metadata(doc)
    assert metadata["title"] == "Overridden Title"
    # file_path MUST be the actual resolved path of doc, NOT the malicious path from companion JSON
    assert metadata["file_path"] == str(doc.resolve())


def test_ingest_policy_batch_rejects_external_symlink_or_junction(initialized_db: str, tmp_path: Path):
    """Verify DocumentExtractor in ingest_policy_batch blocks symlinks/junctions pointing outside policies_dir."""
    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_doc = outside_dir / "external_policy.md"
    outside_doc.write_text("# External Leaked Policy\n\nContent.\n", encoding="utf-8")

    link_created = False
    link_path = policies_dir / "linked_policy.md"
    try:
        link_path.symlink_to(outside_doc)
        link_created = True
    except (OSError, NotImplementedError):
        if sys.platform == "win32":
            try:
                import _winapi
                junction_dir = policies_dir / "junction_dir"
                _winapi.CreateJunction(str(outside_dir), str(junction_dir))
                # Now a file inside junction_dir is discovered by discover_policy_files
                link_created = True
            except Exception:
                pass

    if not link_created:
        pytest.skip("Neither symlink nor junction supported in current environment")

    engine = create_engine(initialized_db)
    fake_embedding = FakeEmbeddingService(dimension=384)

    results = ingest_policy_batch(
        engine=engine,
        policies_dir=policies_dir,
        embedding_service=fake_embedding,
    )
    engine.dispose()

    assert len(results) > 0
    # Must fail on the external file with path traversal error
    failed = [r for r in results if r["status"] == "FAILED"]
    assert len(failed) >= 1
    assert any("resolves outside allowed root" in f["error"].lower() or "access denied" in f["error"].lower() for f in failed)


def test_ingest_policy_batch_dry_run_rejects_external_symlink_or_junction(initialized_db: str, tmp_path: Path):
    """Verify dry_run mode in ingest_policy_batch enforces the same allowed_root boundary."""
    policies_dir = tmp_path / "policies_dry"
    policies_dir.mkdir()
    outside_dir = tmp_path / "outside_dry"
    outside_dir.mkdir()
    outside_doc = outside_dir / "external_policy_dry.md"
    outside_doc.write_text("# External Leaked Policy\n\nContent.\n", encoding="utf-8")

    link_created = False
    link_path = policies_dir / "linked_policy.md"
    try:
        link_path.symlink_to(outside_doc)
        link_created = True
    except (OSError, NotImplementedError):
        if sys.platform == "win32":
            try:
                import _winapi
                junction_dir = policies_dir / "junction_dir"
                _winapi.CreateJunction(str(outside_dir), str(junction_dir))
                link_created = True
            except Exception:
                pass

    if not link_created:
        pytest.skip("Neither symlink nor junction supported in current environment")

    engine = create_engine(initialized_db)
    fake_embedding = FakeEmbeddingService(dimension=384)

    results = ingest_policy_batch(
        engine=engine,
        policies_dir=policies_dir,
        embedding_service=fake_embedding,
        dry_run=True,
    )
    engine.dispose()

    assert len(results) > 0
    failed = [r for r in results if r["status"] == "FAILED"]
    assert len(failed) >= 1
    assert any("resolves outside allowed root" in f["error"].lower() or "access denied" in f["error"].lower() for f in failed)


def test_extract_metadata_rejects_external_file_before_reading(tmp_path: Path):
    """Verify extract_document_metadata rejects external paths before reading content when allowed_root is set."""
    from app.services.policy_rag.document_extractor import PathTraversalError

    safe_dir = tmp_path / "safe_dir"
    safe_dir.mkdir()
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.md"
    outside_file.write_text("# Secret Leaked\n", encoding="utf-8")

    with pytest.raises(PathTraversalError):
        extract_document_metadata(outside_file, allowed_root=safe_dir)


def test_extract_metadata_rejects_external_companion_json(tmp_path: Path):
    """Verify companion JSON resolving outside allowed_root is rejected before reading."""
    from app.services.policy_rag.document_extractor import PathTraversalError
    import json

    safe_dir = tmp_path / "safe_dir"
    safe_dir.mkdir()
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()

    # Document is in safe_dir
    safe_doc = safe_dir / "policy1.md"
    safe_doc.write_text("# Safe Policy\n", encoding="utf-8")

    # Companion JSON is an external symlink or points outside
    outside_meta = outside_dir / "external_meta.json"
    outside_meta.write_text(json.dumps({"title": "External Title"}), encoding="utf-8")

    companion_link = safe_dir / "policy1.md.json"
    link_created = False
    try:
        companion_link.symlink_to(outside_meta)
        link_created = True
    except (OSError, NotImplementedError):
        pass

    if link_created:
        with pytest.raises(PathTraversalError):
            extract_document_metadata(safe_doc, allowed_root=safe_dir)
    else:
        # On unprivileged Windows where file symlinks are restricted, verify validate_path_within_root directly blocks companion path
        from scripts.ingest_policies import validate_path_within_root
        with pytest.raises(PathTraversalError):
            validate_path_within_root(outside_meta, allowed_root=safe_dir)


def test_ingest_policy_batch_per_document_atomic_rollback(initialized_db: str, tmp_path: Path, monkeypatch):
    """Verify failure on one document rolls back only that document and its chunks, without aborting subsequent docs."""
    from app.services.policy_rag.vector_store import VectorStore

    policies_dir = tmp_path / "batch_test"
    policies_dir.mkdir()

    # 1. Valid document 1
    doc1 = policies_dir / "doc1.md"
    doc1.write_text("# Policy One (Version 1.0)\n\n- **Effective From**: 2026-01-01\n\nContent one.\n", encoding="utf-8")

    # 2. Document 2 that will fail after partial persistence (e.g. during store_document_chunks)
    doc2 = policies_dir / "doc2.md"
    doc2.write_text("# Policy Two (Version 1.0)\n\n- **Effective From**: 2026-01-01\n\nContent two.\n", encoding="utf-8")

    # 3. Valid document 3
    doc3 = policies_dir / "doc3.md"
    doc3.write_text("# Policy Three (Version 1.0)\n\n- **Effective From**: 2026-01-01\n\nContent three.\n", encoding="utf-8")

    original_store = VectorStore.store_document_chunks
    captured_failed_doc_id = None

    def faulty_store(self, document, chunks):
        nonlocal captured_failed_doc_id
        if "Policy Two" in document.title:
            captured_failed_doc_id = document.id
            # Simulate failure after document record has been flushed
            raise RuntimeError("Injected database failure during chunk persistence for doc2!")
        return original_store(self, document, chunks)

    monkeypatch.setattr(VectorStore, "store_document_chunks", faulty_store)

    engine = create_engine(initialized_db)
    fake_embedding = FakeEmbeddingService(dimension=384)

    results = ingest_policy_batch(
        engine=engine,
        policies_dir=policies_dir,
        embedding_service=fake_embedding,
    )

    # doc1: SUCCESS, doc2: FAILED, doc3: SUCCESS
    assert len(results) == 3
    succeeded = [r for r in results if r["status"] == "SUCCESS"]
    failed = [r for r in results if r["status"] == "FAILED"]
    assert len(succeeded) == 2
    assert len(failed) == 1
    assert failed[0]["filename"] == "doc2.md"

    doc1_res = next(r for r in succeeded if r["filename"] == "doc1.md")
    doc3_res = next(r for r in succeeded if r["filename"] == "doc3.md")

    # Critical Database Assertion: doc1 and doc3 exist; doc2 must have ZERO records in policy_documents or policy_chunks!
    with Session(engine) as session:
        all_docs = session.query(PolicyDocument).all()
        persisted_doc_ids = {d.id for d in all_docs}
        titles = {d.title for d in all_docs}

        # 1. Prove successful earlier and later documents remain persisted
        assert "Policy One" in titles
        assert "Policy Three" in titles
        assert doc1_res["doc_id"] in persisted_doc_ids
        assert doc3_res["doc_id"] in persisted_doc_ids
        assert len(all_docs) == 2

        # 2. Prove failed document was completely rolled back
        assert "Policy Two" not in titles
        assert captured_failed_doc_id is not None
        assert captured_failed_doc_id not in persisted_doc_ids

        # 3. Prove all persisted chunks belong strictly to doc1 and doc3
        all_chunks = session.query(PolicyChunk).all()
        assert len(all_chunks) > 0
        chunk_doc_ids = {c.document_id for c in all_chunks}
        assert chunk_doc_ids == {doc1_res["doc_id"], doc3_res["doc_id"]}
        assert captured_failed_doc_id not in chunk_doc_ids

        # 4. Prove zero chunks exist referencing the failed document id
        failed_chunks = session.query(PolicyChunk).filter(PolicyChunk.document_id == captured_failed_doc_id).all()
        assert len(failed_chunks) == 0
    engine.dispose()
