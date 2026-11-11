"""Deterministic, heading-aware text chunker with configurable size and overlap."""

from dataclasses import dataclass
import re
from typing import List, Optional


@dataclass(frozen=True)
class Chunk:
    """Represents a discrete text chunk produced from a document."""

    chunk_index: int
    section_title: Optional[str]
    content: str
    token_count: int


class TextChunker:
    """Splits document text into overlapping chunks while preserving section boundaries."""

    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        if chunk_overlap < 0:
            raise ValueError(f"chunk_overlap cannot be negative, got {chunk_overlap}")
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap must be less than chunk_size (overlap={chunk_overlap}, size={chunk_size})"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, title: Optional[str] = None) -> List[Chunk]:
        """Split document text into structured, overlapping chunks.

        Args:
            text: Raw or extracted document text.
            title: Optional default document or section title.

        Returns:
            List of Chunk objects with deterministic index and estimated token count.
        """
        if not text or not text.strip():
            return []

        # Split into logical lines to track headings
        lines = text.splitlines()
        sections: List[tuple[Optional[str], str]] = []
        current_heading = title
        current_body_lines: List[str] = []

        for line in lines:
            heading_match = self.HEADING_PATTERN.match(line.strip())
            if heading_match:
                # Save previous section if it has content
                if current_body_lines:
                    body_text = "\n".join(current_body_lines).strip()
                    if body_text:
                        sections.append((current_heading, body_text))
                    current_body_lines = []
                current_heading = heading_match.group(2).strip()
            else:
                current_body_lines.append(line)

        # Flush any trailing section
        if current_body_lines:
            body_text = "\n".join(current_body_lines).strip()
            if body_text:
                sections.append((current_heading, body_text))

        # If no markdown headings were detected, treat the entire text as one section
        if not sections:
            sections = [(title, text.strip())]

        # Chunk each section
        all_chunks: List[Chunk] = []
        chunk_counter = 0

        for sec_title, sec_text in sections:
            sec_chunks = self._chunk_section_text(sec_text)
            for chunk_content in sec_chunks:
                clean_content = chunk_content.strip()
                if not clean_content:
                    continue

                token_estimate = max(1, len(clean_content.split()))
                all_chunks.append(
                    Chunk(
                        chunk_index=chunk_counter,
                        section_title=sec_title,
                        content=clean_content,
                        token_count=token_estimate,
                    )
                )
                chunk_counter += 1

        return all_chunks

    def _chunk_section_text(self, text: str) -> List[str]:
        """Split a single section's text into chunks honoring chunk_size and chunk_overlap."""
        if len(text) <= self.chunk_size:
            return [text]

        # Break text into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        units: List[str] = []

        for p in paragraphs:
            if len(p) <= self.chunk_size:
                units.append(p)
            else:
                # Break long paragraph into sentences
                sentences = self.SENTENCE_SPLIT_PATTERN.split(p)
                for s in sentences:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    if len(s_clean) <= self.chunk_size:
                        units.append(s_clean)
                    else:
                        # Break oversized sentence by words
                        words = s_clean.split()
                        curr_word_block: List[str] = []
                        curr_len = 0
                        for w in words:
                            w_len = len(w) + (1 if curr_word_block else 0)
                            if curr_len + w_len > self.chunk_size and curr_word_block:
                                units.append(" ".join(curr_word_block))
                                curr_word_block = [w]
                                curr_len = len(w)
                            else:
                                curr_word_block.append(w)
                                curr_len += w_len
                        if curr_word_block:
                            units.append(" ".join(curr_word_block))

        # Assemble units into overlapping chunks
        result_chunks: List[str] = []
        current_chunk_str = ""

        for unit in units:
            if not current_chunk_str:
                current_chunk_str = unit
            else:
                candidate = current_chunk_str + "\n\n" + unit
                if len(candidate) <= self.chunk_size:
                    current_chunk_str = candidate
                else:
                    result_chunks.append(current_chunk_str)
                    # Prepare overlap from end of current_chunk_str
                    overlap_text = self._get_overlap_suffix(current_chunk_str, self.chunk_overlap)
                    if overlap_text:
                        current_chunk_str = overlap_text + "\n\n" + unit
                    else:
                        current_chunk_str = unit

        if current_chunk_str and current_chunk_str.strip():
            result_chunks.append(current_chunk_str)

        return result_chunks

    def _get_overlap_suffix(self, text: str, overlap_chars: int) -> str:
        """Extract a clean word-bounded suffix of up to overlap_chars characters."""
        if overlap_chars <= 0 or not text:
            return ""
        if len(text) <= overlap_chars:
            return text

        suffix = text[-overlap_chars:].strip()
        # Ensure we don't start midway through a word if there's a space
        first_space = suffix.find(" ")
        if first_space != -1 and first_space < len(suffix) // 2:
            suffix = suffix[first_space + 1:].strip()
        return suffix

