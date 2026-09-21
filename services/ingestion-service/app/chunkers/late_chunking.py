"""Late Chunking: embed full document first, then split preserving token positions."""

import logging
import re
from typing import Any

from app.chunkers.base import BaseChunker, Chunk, ChunkingConfig

logger = logging.getLogger(__name__)


class LateChunker(BaseChunker):
    """
    Late Chunking: embed full document, then split preserving per-token embeddings.

    Instead of the traditional chunk-then-embed pipeline, Late Chunking
    splits the text into spans at sentence boundaries and records token
    position information so the embedder step can:
    1. Embed the full document through a long-context model.
    2. Pool per-span embeddings from the full-document token embeddings.

    Chunks produced by this chunker carry ``requires_late_embedding: True``
    in their metadata along with ``span_start_token`` and ``span_end_token``
    positions (estimated from character offsets).
    """

    # Regex for sentence boundary detection
    _SENTENCE_RE = re.compile(
        r"(?<=[.!?])\s+(?=[A-Z])"  # Split after .!? followed by uppercase
        r"|(?<=\n)\n+"  # Or on paragraph breaks
    )

    def chunk(
        self,
        text: str,
        config: ChunkingConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """
        Split text into sentence-boundary spans for late embedding.

        Each chunk is annotated with position info so that the embedder
        can later extract the correct slice from the full-document
        embedding.

        Args:
            text: Full document text.
            config: Optional chunking configuration.
            metadata: Optional base metadata.

        Returns:
            List of Chunk objects with late-embedding metadata.
        """
        cfg = config or self.config
        if not text:
            return []

        text = self._preprocess_text(text)
        base_metadata = dict(metadata) if metadata else {}

        # Split into sentences / spans
        spans = self._split_into_spans(text, cfg.chunk_size)

        chunks: list[Chunk] = []
        char_offset = 0

        for i, span in enumerate(spans):
            span_text = span.strip()
            if not span_text:
                char_offset += len(span)
                continue

            start_char = text.find(span_text, char_offset)
            if start_char == -1:
                start_char = char_offset
            end_char = start_char + len(span_text)

            # Approximate token positions (rough: ~4 chars per token)
            start_token = start_char // 4
            end_token = end_char // 4

            span_metadata = {
                **base_metadata,
                "requires_late_embedding": True,
                "span_start_char": start_char,
                "span_end_char": end_char,
                "span_start_token": start_token,
                "span_end_token": end_token,
                "full_document_length": len(text),
            }

            chunk = self._create_chunk(
                content=span_text,
                index=i,
                start_char=start_char,
                end_char=end_char,
                base_metadata=span_metadata,
            )
            chunks.append(chunk)
            char_offset = end_char

        chunks = self._filter_chunks(chunks)

        logger.info(
            "Late chunking produced %d spans from %d chars", len(chunks), len(text)
        )
        return chunks

    def _split_into_spans(self, text: str, max_span_size: int) -> list[str]:
        """Split text at sentence boundaries, respecting max span size."""
        # First split on sentences
        raw_spans = self._SENTENCE_RE.split(text)

        if not raw_spans:
            return [text] if text.strip() else []

        # Merge small spans, split large ones
        merged: list[str] = []
        current = ""

        for span in raw_spans:
            if not span.strip():
                continue

            if len(current) + len(span) <= max_span_size:
                current = (current + " " + span).strip() if current else span
            else:
                if current:
                    merged.append(current)
                # If this single span exceeds max, hard-split it
                if len(span) > max_span_size:
                    for sub in self._hard_split(span, max_span_size):
                        merged.append(sub)
                    current = ""
                else:
                    current = span

        if current:
            merged.append(current)

        return merged

    @staticmethod
    def _hard_split(text: str, max_size: int) -> list[str]:
        """Split text at word boundaries when it exceeds max size."""
        words = text.split()
        parts: list[str] = []
        current: list[str] = []
        length = 0

        for word in words:
            if length + len(word) + 1 > max_size and current:
                parts.append(" ".join(current))
                current = [word]
                length = len(word)
            else:
                current.append(word)
                length += len(word) + 1

        if current:
            parts.append(" ".join(current))

        return parts
