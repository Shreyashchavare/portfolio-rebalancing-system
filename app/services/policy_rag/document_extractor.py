"""Service for extracting normalized text and metadata from policy documents."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Optional, Union
import pypdf


class DocumentExtractionError(Exception):
    """Base exception for document extraction failures."""

    pass


class DocumentNotFoundError(DocumentExtractionError):
    """Raised when the specified file path does not exist."""

    pass


class PathTraversalError(DocumentExtractionError):
    """Raised when an unsafe path traversal attempt is detected."""

    pass


class UnsupportedFileTypeError(DocumentExtractionError):
    """Raised when an unsupported file extension is provided."""

    pass


class EmptyDocumentError(DocumentExtractionError):
    """Raised when a document contains zero extractable text."""

    pass


class DocumentSizeLimitExceededError(DocumentExtractionError):
    """Raised when a document exceeds the configured maximum byte size."""

    pass


class CorruptDocumentError(DocumentExtractionError):
    """Raised when a document structure is corrupted or unreadable."""

    pass


@dataclass(frozen=True)
class ExtractedDocument:
    """Normalized output produced by DocumentExtractor."""

    filename: str
    file_path: str
    file_type: str
    text: str
    sha256_checksum: str
    char_count: int
    page_count: int


class DocumentExtractor:
    """Extracts text and structural metadata from PDF, TXT, and Markdown files."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}
    DEFAULT_MAX_BYTES = 20 * 1024 * 1024  # 20 MB

    def __init__(
        self,
        allowed_root: Optional[Union[str, Path]] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        self.allowed_root = Path(allowed_root).resolve() if allowed_root is not None else None
        self.max_bytes = max_bytes

    def extract(self, file_path: Union[str, Path]) -> ExtractedDocument:
        """Extract text content and metadata from a local document.

        Args:
            file_path: Path to the target document.

        Returns:
            ExtractedDocument containing normalized text, file attributes, and SHA-256 hash.

        Raises:
            PathTraversalError: If path resolves outside allowed_root.
            DocumentNotFoundError: If the file does not exist.
            UnsupportedFileTypeError: If file extension is not supported.
            DocumentSizeLimitExceededError: If file exceeds maximum byte size.
            EmptyDocumentError: If file contains no extractable text.
            CorruptDocumentError: If document is unreadable or malformed.
        """
        raw_path = Path(file_path)
        resolved_path = raw_path.resolve()

        # Path traversal guard
        if self.allowed_root is not None:
            try:
                resolved_path.relative_to(self.allowed_root)
            except ValueError:
                raise PathTraversalError(
                    f"Access denied: path '{raw_path}' resolves outside allowed root '{self.allowed_root}'"
                )

        # File existence check
        if not resolved_path.is_file():
            raise DocumentNotFoundError(f"File not found: {raw_path}")

        # File size check
        file_size = resolved_path.stat().st_size
        if file_size > self.max_bytes:
            raise DocumentSizeLimitExceededError(
                f"File size {file_size} bytes exceeds maximum limit of {self.max_bytes} bytes"
            )

        # Extension check
        extension = resolved_path.suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"File extension '{extension}' is not supported. Allowed: {sorted(self.SUPPORTED_EXTENSIONS)}"
            )

        # Compute SHA-256 hash
        hasher = hashlib.sha256()
        with open(resolved_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_checksum = hasher.hexdigest()

        # Check empty file (0 bytes)
        if file_size == 0:
            raise EmptyDocumentError(f"Document '{resolved_path.name}' is empty (0 bytes).")

        # Format-specific extraction
        clean_ext = extension.lstrip(".")
        if extension in {".txt", ".md"}:
            try:
                raw_text = resolved_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    raw_text = resolved_path.read_text(encoding="utf-8", errors="replace")
                except Exception as err:
                    raise CorruptDocumentError(f"Failed to decode text file '{resolved_path.name}': {err}")

            if not raw_text.strip():
                raise EmptyDocumentError(f"Text document '{resolved_path.name}' contains no extractable text.")

            return ExtractedDocument(
                filename=resolved_path.name,
                file_path=str(resolved_path),
                file_type=clean_ext,
                text=raw_text,
                sha256_checksum=sha256_checksum,
                char_count=len(raw_text),
                page_count=1,
            )

        elif extension == ".pdf":
            try:
                reader = pypdf.PdfReader(str(resolved_path))
                if reader.is_encrypted:
                    raise CorruptDocumentError(f"PDF document '{resolved_path.name}' is encrypted.")

                extracted_pages = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        extracted_pages.append(page_text.strip())

                full_text = "\n\n".join(extracted_pages).strip()
                if not full_text:
                    raise EmptyDocumentError(f"PDF document '{resolved_path.name}' contains no extractable text.")

                return ExtractedDocument(
                    filename=resolved_path.name,
                    file_path=str(resolved_path),
                    file_type="pdf",
                    text=full_text,
                    sha256_checksum=sha256_checksum,
                    char_count=len(full_text),
                    page_count=len(reader.pages),
                )
            except (EmptyDocumentError, CorruptDocumentError):
                raise
            except Exception as err:
                raise CorruptDocumentError(f"Corrupt or invalid PDF document '{resolved_path.name}': {err}")

        raise UnsupportedFileTypeError(f"Unhandled extension: {extension}")

