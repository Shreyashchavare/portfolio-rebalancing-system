"""Policy document discovery, metadata extraction, and RAG ingestion automation."""

import argparse
from datetime import date
import json
import logging
from pathlib import Path
import re
import sys

# Ensure repository root is in sys.path when script is executed directly
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from typing import Any, Dict, List, Optional, Sequence
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.schemas.policy_rag import PolicyIngestRequest
from app.services.policy_rag.document_extractor import (
    DocumentExtractor,
    PathTraversalError,
)
from app.services.policy_rag.embedding_service import (
    BaseEmbeddingService,
    FakeEmbeddingService,
)
from app.services.policy_rag.policy_rag_service import PolicyRAGService
from scripts.seed_database import resolve_database_url, validate_connectivity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest_policies")

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


def validate_path_within_root(path: Path, allowed_root: Path) -> Path:
    """Resolve path and verify it resides strictly within allowed_root.

    Raises:
        PathTraversalError: If path resolves outside allowed_root.
    """
    resolved_root = allowed_root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        raise PathTraversalError(
            f"Access denied: path '{path}' resolves to '{resolved_path}' outside allowed root '{resolved_root}'"
        )
    return resolved_path


def discover_policy_files(policies_dir: Path) -> List[Path]:
    """Discover all supported policy document files in deterministic alphabetical order.

    Args:
        policies_dir: Directory containing policy files.

    Returns:
        Sorted list of matching Path objects.
    """
    if not policies_dir.is_dir():
        raise FileNotFoundError(f"Policy directory '{policies_dir}' does not exist.")

    discovered: List[Path] = []
    # Recursively discover supported policy files in directory and any subdirectories
    for entry in policies_dir.rglob("*"):
        if entry.is_file() and not entry.name.startswith("."):
            if entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                discovered.append(entry)

    return sorted(discovered, key=lambda p: (p.name, str(p)))


def extract_document_metadata(file_path: Path, allowed_root: Optional[Path] = None) -> Dict[str, Any]:
    """Extract or derive ingestion metadata from document headers, companion JSON, or filename.

    Args:
        file_path: Path to target policy document.
        allowed_root: Optional directory root to enforce path containment before reading.

    Returns:
        Dictionary containing metadata fields required by PolicyIngestRequest.

    Raises:
        PathTraversalError: If file_path or companion metadata resolves outside allowed_root.
    """
    if allowed_root is not None:
        validate_path_within_root(file_path, allowed_root)

    stem = file_path.stem
    clean_stem_title = re.sub(r"[_\-]+", " ", stem).title()

    # 1. Check for companion JSON metadata file (<filename>.meta.json or <filename>.json)
    companion_meta = file_path.with_suffix(file_path.suffix + ".json")
    if not companion_meta.is_file():
        companion_meta = file_path.with_name(f"{stem}.meta.json")

    if companion_meta.is_file():
        if allowed_root is not None:
            validate_path_within_root(companion_meta, allowed_root)
        try:
            with open(companion_meta, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if not isinstance(meta, dict):
                raise ValueError(f"Companion metadata '{companion_meta}' must be a JSON object")
            if "effective_from" in meta and isinstance(meta["effective_from"], str):
                meta["effective_from"] = date.fromisoformat(meta["effective_from"])
            if "effective_to" in meta and isinstance(meta["effective_to"], str):
                meta["effective_to"] = date.fromisoformat(meta["effective_to"])

            # Security Rule: Never allow companion JSON to override the actual discovered file path
            if "file_path" in meta and Path(meta["file_path"]).resolve() != file_path.resolve():
                logger.warning(
                    "Companion metadata for '%s' specified file_path '%s' conflicting with actual resolved path '%s'; overriding with actual resolved path.",
                    file_path.name,
                    meta["file_path"],
                    file_path.resolve(),
                )
            meta["file_path"] = str(file_path.resolve())
            return meta
        except PathTraversalError:
            raise
        except Exception as exc:
            logger.warning("Failed to parse companion metadata '%s': %s", companion_meta, exc)

    # Defaults
    title = clean_stem_title
    version = "1.0"
    policy_family_id: Optional[str] = None
    document_type = "INVESTMENT_POLICY"
    effective_from = date.today()
    effective_to: Optional[date] = None
    status = "ACTIVE"

    # Version deduction from filename (e.g. name_v2 -> 2.0)
    ver_match = re.search(r"_v(\d+(?:\.\d+)?)$", stem, re.IGNORECASE)
    if ver_match:
        raw_v = ver_match.group(1)
        version = f"{raw_v}.0" if "." not in raw_v else raw_v

    # 2. Extract structured Markdown/TXT header metadata if text file
    if file_path.suffix.lower() in (".md", ".txt"):
        try:
            text = file_path.read_text(encoding="utf-8")
            lines = text.splitlines()

            # Parse Top Heading: # Title (Version X.Y)
            for line in lines[:15]:
                h_match = re.match(r"^#\s+(.+)$", line.strip())
                if h_match:
                    full_heading = h_match.group(1).strip()
                    ver_in_heading = re.search(r"\(Version\s+([0-9.]+)\)", full_heading, re.IGNORECASE)
                    if ver_in_heading:
                        version = ver_in_heading.group(1)
                        title = re.sub(r"\(Version\s+[0-9.]+\)", "", full_heading).strip()
                    else:
                        title = full_heading
                    break

            # Parse structured bullet fields
            fam_match = re.search(r"-\s+\*?\*?Policy Family ID\*?\*?:\s*([^\n\r]+)", text, re.IGNORECASE)
            if fam_match:
                policy_family_id = fam_match.group(1).strip()

            from_match = re.search(r"-\s+\*?\*?Effective From\*?\*?:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text, re.IGNORECASE)
            if from_match:
                effective_from = date.fromisoformat(from_match.group(1).strip())

            to_match = re.search(r"-\s+\*?\*?Effective To\*?\*?:\s*([^\n\r]+)", text, re.IGNORECASE)
            if to_match:
                val = to_match.group(1).strip().lower()
                if any(k in val for k in ("ongoing", "none", "null", "inf", "n/a")):
                    effective_to = None
                else:
                    date_match = re.search(r"([0-9]{4}-[0-9]{2}-[0-9]{2})", val)
                    if date_match:
                        effective_to = date.fromisoformat(date_match.group(1))

            status_match = re.search(r"-\s+\*?\*?Status\*?\*?:\s*([A-Za-z]+)", text, re.IGNORECASE)
            if status_match:
                status = status_match.group(1).strip().upper()

            type_match = re.search(r"-\s+\*?\*?Document Type\*?\*?:\s*([A-Za-z_]+)", text, re.IGNORECASE)
            if type_match:
                document_type = type_match.group(1).strip().upper()

        except Exception as exc:
            logger.warning("Error scanning text for metadata in '%s': %s", file_path, exc)

    return {
        "title": title,
        "version": version,
        "policy_family_id": policy_family_id,
        "document_type": document_type,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "status": status,
        "file_path": str(file_path.resolve()),
    }


def ingest_policy_batch(
    engine: Engine,
    policies_dir: Path,
    embedding_service: Optional[BaseEmbeddingService] = None,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """Process policy documents deterministically through PolicyRAGService.

    Args:
        engine: Connected SQLAlchemy Engine.
        policies_dir: Path to directory containing policy documents.
        embedding_service: Optional custom embedding service (defaults to standard or fake).
        dry_run: If True, validate metadata and extraction without database persistence.

    Returns:
        List of result dictionaries recording status, document ID, and errors.
    """
    discovered_files = discover_policy_files(policies_dir)
    logger.info("Found %d policy files in '%s'.", len(discovered_files), policies_dir)

    results: List[Dict[str, Any]] = []
    resolved_policies_dir = policies_dir.resolve()
    extractor = DocumentExtractor(allowed_root=resolved_policies_dir)

    with Session(engine) as session:
        rag_service = PolicyRAGService(
            session=session,
            embedding_service=embedding_service,
            extractor=extractor,
        )

        for file_path in discovered_files:
            logger.info("Processing policy file: %s", file_path.name)

            # Security Pre-flight Check: Validate document path against allowed root BEFORE reading content or metadata
            try:
                validate_path_within_root(file_path, resolved_policies_dir)
            except PathTraversalError as pte:
                logger.error("Security violation: document '%s' escapes allowed root: %s", file_path.name, pte)
                results.append({"filename": file_path.name, "status": "FAILED", "error": str(pte)})
                continue

            # Metadata extraction with allowed_root enforcement (validates companion JSON before opening)
            try:
                meta = extract_document_metadata(file_path, allowed_root=resolved_policies_dir)
            except PathTraversalError as pte:
                logger.error("Security violation: metadata extraction for '%s' escapes allowed root: %s", file_path.name, pte)
                results.append({"filename": file_path.name, "status": "FAILED", "error": str(pte)})
                continue
            except Exception as meta_exc:
                logger.warning("Failed to extract metadata for '%s': %s", file_path.name, meta_exc)
                results.append({"filename": file_path.name, "status": "FAILED", "error": str(meta_exc)})
                continue

            if dry_run:
                try:
                    # Validate extraction capability and date consistency
                    if meta.get("effective_to") and meta["effective_from"] > meta["effective_to"]:
                        raise ValueError(
                            f"effective_from ({meta['effective_from']}) cannot be after effective_to ({meta['effective_to']})"
                        )
                    extractor.extract(file_path)
                    logger.info("[DRY-RUN] '%s' parsed and validated successfully.", file_path.name)
                    results.append({"filename": file_path.name, "status": "DRY_RUN", "title": meta["title"]})
                except Exception as exc:
                    logger.warning("[DRY-RUN] Validation failure for '%s': %s", file_path.name, exc)
                    results.append({"filename": file_path.name, "status": "FAILED", "error": str(exc)})
                continue

            try:
                request = PolicyIngestRequest(**meta)
                response = rag_service.ingest_document(request)
                session.commit()
                logger.info(
                    "Successfully ingested '%s' as doc_id=%s, version=%s (%d chunks).",
                    file_path.name,
                    response.id,
                    response.version,
                    response.chunk_count,
                )
                results.append({
                    "filename": file_path.name,
                    "status": "SUCCESS",
                    "doc_id": response.id,
                    "version": response.version,
                    "chunks": response.chunk_count,
                })
            except ValueError as val_err:
                session.rollback()
                msg = str(val_err)
                if "already ingested" in msg.lower():
                    logger.info("Skipping '%s': %s", file_path.name, msg)
                    results.append({
                        "filename": file_path.name,
                        "status": "SKIPPED",
                        "reason": msg,
                    })
                else:
                    logger.warning("Validation error ingesting '%s': %s", file_path.name, msg)
                    results.append({
                        "filename": file_path.name,
                        "status": "FAILED",
                        "error": msg,
                    })
            except Exception as exc:
                session.rollback()
                logger.error("Error ingesting '%s': %s", file_path.name, exc)
                results.append({
                    "filename": file_path.name,
                    "status": "FAILED",
                    "error": str(exc),
                })

    return results


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint for policy document ingestion automation."""
    parser = argparse.ArgumentParser(
        description="Policy document discovery and RAG ingestion automation for Portfolio Rebalancing System.",
    )
    parser.add_argument(
        "--policies-dir",
        type=Path,
        default=Path("policy_documents"),
        help="Path to directory containing policy files (default: policy_documents).",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Explicit database connection URI (overrides DATABASE_URL environment variable).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate metadata and document parsing without embedding or persisting to database.",
    )
    parser.add_argument(
        "--use-fake-embeddings",
        action="store_true",
        help="Use deterministic FakeEmbeddingService (offline testing without downloading models).",
    )

    args = parser.parse_args(argv)

    try:
        db_url = resolve_database_url(args.database_url)
    except Exception as err:
        logger.error("Configuration error: %s", err)
        return 1

    engine = create_engine(db_url)
    if not validate_connectivity(engine):
        logger.error("Database connectivity check failed. Verify database target is reachable.")
        engine.dispose()
        return 1

    embedding_service: Optional[BaseEmbeddingService] = None
    if args.use_fake_embeddings:
        logger.info("Using FakeEmbeddingService as requested via --use-fake-embeddings.")
        embedding_service = FakeEmbeddingService(dimension=384)

    try:
        results = ingest_policy_batch(
            engine=engine,
            policies_dir=args.policies_dir,
            embedding_service=embedding_service,
            dry_run=args.dry_run,
        )

        succeeded = sum(1 for r in results if r["status"] == "SUCCESS")
        skipped = sum(1 for r in results if r["status"] == "SKIPPED")
        failed = sum(1 for r in results if r["status"] == "FAILED")
        dry_runs = sum(1 for r in results if r["status"] == "DRY_RUN")

        logger.info("================ Policy Ingestion Summary ================")
        logger.info("Total Files Evaluated: %d", len(results))
        if args.dry_run:
            logger.info("Dry-Run Validated:     %d", dry_runs)
        else:
            logger.info("Successfully Ingested: %d", succeeded)
            logger.info("Skipped (Duplicates):  %d", skipped)
        logger.info("Failed Ingestion:      %d", failed)
        logger.info("==========================================================")

        return 0
    except Exception as exc:
        logger.error("Policy batch ingestion encountered fatal error: %s", exc)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
