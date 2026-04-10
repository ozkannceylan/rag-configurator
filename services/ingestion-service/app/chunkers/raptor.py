"""RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval."""

import hashlib
import logging
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.chunkers.base import BaseChunker, Chunk, ChunkingConfig

logger = logging.getLogger(__name__)


SUMMARIZE_CLUSTER_PROMPT = """Summarize the following group of related text passages into a single, concise paragraph that preserves the key information.

Passages:
{passages}

Summary:"""


class RAPTORChunker(BaseChunker):
    """
    Recursive Abstractive Processing for Tree-Organized Retrieval.

    Builds a hierarchical tree of chunks:
    - Level 0: Leaf chunks from the original text.
    - Level 1+: Summary chunks created by clustering and summarizing lower levels.

    Each chunk stores ``tree_level`` and ``parent_chunk_id`` in its metadata
    so the retrieval layer can traverse the tree.

    Requires an ``llm_generate`` async callable and an ``embed_texts`` async
    callable to be set before calling ``chunk_async``.  The synchronous
    ``chunk`` method produces only the leaf level (level 0) so it stays
    compatible with the ``BaseChunker`` interface.
    """

    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        max_tree_levels: int = 3,
        cluster_size: int = 5,
        llm_generate: Optional[Callable[..., Any]] = None,
        embed_texts: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Initialize RAPTOR chunker.

        Args:
            config: Base chunking configuration.
            max_tree_levels: Maximum number of summary levels to build.
            cluster_size: Target number of chunks per cluster.
            llm_generate: Async callable(prompt: str) -> str for summarization.
            embed_texts: Async callable(texts: List[str]) -> List[List[float]]
                         for similarity-based clustering.
        """
        super().__init__(config)
        self.max_tree_levels = max_tree_levels
        self.cluster_size = cluster_size
        self.llm_generate = llm_generate
        self.embed_texts = embed_texts

    # ------------------------------------------------------------------
    # Synchronous interface (BaseChunker contract) -- leaf level only
    # ------------------------------------------------------------------

    def chunk(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split text into leaf-level chunks.

        This synchronous method produces only level-0 chunks.
        Use ``chunk_async`` to build the full RAPTOR tree.
        """
        cfg = config or self.config
        if not text:
            return []

        text = self._preprocess_text(text)
        base_metadata = dict(metadata) if metadata else {}
        base_metadata["tree_level"] = 0
        base_metadata["parent_chunk_id"] = None

        # Simple recursive splitting for leaf chunks
        chunks = self._split_into_leaf_chunks(text, cfg, base_metadata)
        return self._filter_chunks(chunks)

    # ------------------------------------------------------------------
    # Async interface -- builds full RAPTOR tree
    # ------------------------------------------------------------------

    async def chunk_async(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Build the full RAPTOR tree asynchronously.

        Returns all chunks across all tree levels.
        """
        if not self.llm_generate:
            logger.warning("No LLM callable set; returning leaf chunks only")
            return self.chunk(text, config, metadata)

        cfg = config or self.config
        if not text:
            return []

        text = self._preprocess_text(text)
        base_metadata = dict(metadata) if metadata else {}

        # Step 1: Create leaf chunks (level 0)
        leaf_chunks = self._split_into_leaf_chunks(
            text,
            cfg,
            {**base_metadata, "tree_level": 0, "parent_chunk_id": None},
        )
        leaf_chunks = self._filter_chunks(leaf_chunks)

        all_chunks: List[Chunk] = list(leaf_chunks)
        current_level_chunks = leaf_chunks

        # Steps 2-4: Iteratively cluster and summarize
        for level in range(1, self.max_tree_levels + 1):
            if len(current_level_chunks) <= 1:
                break

            parent_chunks = await self._build_next_level(
                current_level_chunks, level, base_metadata
            )
            if not parent_chunks:
                break

            all_chunks.extend(parent_chunks)
            current_level_chunks = parent_chunks

        logger.info(
            "RAPTOR tree built: %d total chunks across %d levels",
            len(all_chunks),
            (max(c.metadata.get("tree_level", 0) for c in all_chunks) + 1)
            if all_chunks
            else 0,
        )

        return all_chunks

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _split_into_leaf_chunks(
        self,
        text: str,
        config: ChunkingConfig,
        base_metadata: Dict[str, Any],
    ) -> List[Chunk]:
        """Split text into leaf-level chunks using recursive character splitting."""
        separators = ["\n\n", "\n", ". ", " "]
        segments = self._recursive_split(text, separators, config.chunk_size)

        chunks: List[Chunk] = []
        position = 0

        for i, segment in enumerate(segments):
            start = text.find(segment, position)
            if start == -1:
                start = position
            end = start + len(segment)

            chunk = self._create_chunk(
                content=segment.strip(),
                index=i,
                start_char=start,
                end_char=end,
                base_metadata=base_metadata,
            )
            chunks.append(chunk)
            position = end

        return chunks

    def _recursive_split(
        self, text: str, separators: List[str], max_size: int
    ) -> List[str]:
        """Recursively split text on separators until under max_size."""
        if len(text) <= max_size:
            return [text] if text.strip() else []

        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                segments: List[str] = []
                current = ""
                for part in parts:
                    candidate = current + sep + part if current else part
                    if len(candidate) <= max_size:
                        current = candidate
                    else:
                        if current:
                            segments.append(current)
                        current = part
                if current:
                    segments.append(current)
                return segments

        # Last resort: hard-split
        return [text[i : i + max_size] for i in range(0, len(text), max_size)]

    async def _build_next_level(
        self,
        chunks: List[Chunk],
        level: int,
        base_metadata: Dict[str, Any],
    ) -> List[Chunk]:
        """Cluster current-level chunks and summarize each cluster."""
        clusters = await self._cluster_chunks(chunks)
        parent_chunks: List[Chunk] = []

        for cluster_idx, cluster in enumerate(clusters):
            if not cluster:
                continue

            # Summarize the cluster
            passages = "\n\n---\n\n".join(c.content for c in cluster)
            prompt = SUMMARIZE_CLUSTER_PROMPT.replace("{passages}", passages[:8000])

            try:
                summary = await self.llm_generate(prompt)
                summary = summary.strip()
            except Exception as e:
                logger.warning("Summarization failed for cluster %d: %s", cluster_idx, e)
                continue

            child_hashes = [c.content_hash for c in cluster]
            parent_id = hashlib.md5(
                "|".join(child_hashes).encode()
            ).hexdigest()

            meta = {
                **base_metadata,
                "tree_level": level,
                "parent_chunk_id": None,
                "child_chunk_hashes": child_hashes,
            }

            parent_chunk = Chunk(
                content=summary,
                metadata=meta,
                chunk_index=cluster_idx,
                start_char=0,
                end_char=len(summary),
            )
            parent_chunks.append(parent_chunk)

            # Link children -> parent
            for child in cluster:
                child.metadata["parent_chunk_id"] = parent_id

        return parent_chunks

    async def _cluster_chunks(
        self, chunks: List[Chunk]
    ) -> List[List[Chunk]]:
        """
        Cluster chunks by embedding similarity (k-means style) or simple
        sequential grouping if embeddings are unavailable.
        """
        if self.embed_texts and len(chunks) > self.cluster_size:
            return await self._cluster_by_similarity(chunks)
        return self._cluster_sequential(chunks)

    def _cluster_sequential(self, chunks: List[Chunk]) -> List[List[Chunk]]:
        """Simple sequential grouping as fallback."""
        clusters: List[List[Chunk]] = []
        for i in range(0, len(chunks), self.cluster_size):
            clusters.append(chunks[i : i + self.cluster_size])
        return clusters

    async def _cluster_by_similarity(
        self, chunks: List[Chunk]
    ) -> List[List[Chunk]]:
        """Cluster chunks using embeddings and simple k-means."""
        texts = [c.content for c in chunks]

        try:
            embeddings = await self.embed_texts(texts)
        except Exception as e:
            logger.warning("Embedding failed, falling back to sequential: %s", e)
            return self._cluster_sequential(chunks)

        n_clusters = max(1, len(chunks) // self.cluster_size)
        assignments = self._simple_kmeans(embeddings, n_clusters)

        clusters: Dict[int, List[Chunk]] = {}
        for idx, cluster_id in enumerate(assignments):
            clusters.setdefault(cluster_id, []).append(chunks[idx])

        return list(clusters.values())

    @staticmethod
    def _simple_kmeans(
        vectors: List[List[float]], k: int, max_iter: int = 20
    ) -> List[int]:
        """Minimal k-means implementation without numpy dependency."""
        n = len(vectors)
        if n == 0 or k <= 0:
            return []
        if k >= n:
            return list(range(n))

        dim = len(vectors[0])

        # Initialize centroids with first k vectors
        centroids = [list(vectors[i]) for i in range(k)]
        assignments = [0] * n

        for _ in range(max_iter):
            # Assign
            new_assignments = []
            for vec in vectors:
                best = 0
                best_dist = float("inf")
                for ci, centroid in enumerate(centroids):
                    dist = sum((a - b) ** 2 for a, b in zip(vec, centroid))
                    if dist < best_dist:
                        best_dist = dist
                        best = ci
                new_assignments.append(best)

            if new_assignments == assignments:
                break
            assignments = new_assignments

            # Update centroids
            for ci in range(k):
                members = [vectors[j] for j in range(n) if assignments[j] == ci]
                if members:
                    centroids[ci] = [
                        sum(m[d] for m in members) / len(members) for d in range(dim)
                    ]

        return assignments
