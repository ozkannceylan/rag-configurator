"""Community detection for knowledge graphs using Leiden algorithm."""

import json
import logging
import re
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.graph.models import Community, Entity, Relation

logger = logging.getLogger(__name__)


# Entity/Relation extraction prompt
EXTRACTION_PROMPT = """Extract entities and relationships from the following text.

Return a JSON object with two arrays:
- "entities": each with "name", "type" (e.g., Person, Organization, Location, Concept, Technology), and "description"
- "relations": each with "source" (entity name), "target" (entity name), "type" (e.g., WORKS_FOR, LOCATED_IN, RELATED_TO), and "description"

Only extract clearly stated facts. Be concise.

Text:
{text}

JSON:"""


class CommunityDetector:
    """Detect communities in knowledge graph using Leiden algorithm."""

    def __init__(self, resolution: float = 1.0) -> None:
        """
        Initialize community detector.

        Args:
            resolution: Resolution parameter for Leiden algorithm.
                        Higher values produce more communities.
        """
        self.resolution = resolution
        self._has_leiden = self._check_leiden()

    @staticmethod
    def _check_leiden() -> bool:
        """Check if leidenalg is available."""
        try:
            import igraph  # noqa: F401
            import leidenalg  # noqa: F401

            return True
        except ImportError:
            logger.info(
                "leidenalg/igraph not available; "
                "falling back to connected-components community detection"
            )
            return False

    async def extract_entities_relations(
        self,
        chunks: List[Dict[str, Any]],
        llm_generate: Any,
    ) -> Tuple[List[Entity], List[Relation]]:
        """
        Extract entities and relations from text chunks using an LLM.

        Args:
            chunks: List of chunk dicts with 'content' and optionally 'chunk_id'.
            llm_generate: Async callable(prompt: str) -> str that calls the LLM.

        Returns:
            Tuple of (entities, relations).
        """
        entity_map: Dict[str, Entity] = {}
        relations: List[Relation] = []

        for chunk in chunks:
            content = chunk.get("content", "")
            chunk_id = chunk.get("chunk_id", chunk.get("_id", ""))
            if not content.strip():
                continue

            prompt = EXTRACTION_PROMPT.replace("{text}", content[:4000])

            try:
                raw = await llm_generate(prompt)
                parsed = self._parse_extraction(raw)
            except Exception as e:
                logger.warning("Entity extraction failed for chunk %s: %s", chunk_id, e)
                continue

            # Merge entities
            for ent_data in parsed.get("entities", []):
                name = ent_data.get("name", "").strip()
                if not name:
                    continue
                key = name.lower()
                if key in entity_map:
                    existing = entity_map[key]
                    if chunk_id and chunk_id not in existing.chunk_ids:
                        existing.chunk_ids.append(str(chunk_id))
                else:
                    entity_map[key] = Entity(
                        name=name,
                        type=ent_data.get("type", "Unknown"),
                        description=ent_data.get("description", ""),
                        chunk_ids=[str(chunk_id)] if chunk_id else [],
                    )

            # Collect relations
            for rel_data in parsed.get("relations", []):
                source = rel_data.get("source", "").strip()
                target = rel_data.get("target", "").strip()
                if not source or not target:
                    continue
                relations.append(
                    Relation(
                        source=source,
                        target=target,
                        type=rel_data.get("type", "RELATED_TO"),
                        description=rel_data.get("description", ""),
                        chunk_ids=[str(chunk_id)] if chunk_id else [],
                    )
                )

        return list(entity_map.values()), relations

    async def detect_communities(
        self,
        entities: List[Entity],
        relations: List[Relation],
    ) -> List[Community]:
        """
        Detect communities in the knowledge graph.

        Uses Leiden algorithm when available, otherwise falls back to
        simple connected-components grouping.

        Args:
            entities: List of entities (graph nodes).
            relations: List of relations (graph edges).

        Returns:
            List of detected communities.
        """
        if not entities:
            return []

        if self._has_leiden:
            return self._detect_leiden(entities, relations)
        return self._detect_connected_components(entities, relations)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_leiden(
        self,
        entities: List[Entity],
        relations: List[Relation],
    ) -> List[Community]:
        """Community detection via Leiden algorithm (igraph + leidenalg)."""
        import igraph as ig
        import leidenalg

        # Build name -> index mapping
        name_to_idx: Dict[str, int] = {}
        for i, entity in enumerate(entities):
            name_to_idx[entity.name.lower()] = i

        # Build edge list
        edges: List[Tuple[int, int]] = []
        edge_relations: Dict[Tuple[int, int], List[Relation]] = defaultdict(list)
        for rel in relations:
            src_idx = name_to_idx.get(rel.source.lower())
            tgt_idx = name_to_idx.get(rel.target.lower())
            if src_idx is not None and tgt_idx is not None and src_idx != tgt_idx:
                edge = (src_idx, tgt_idx)
                edges.append(edge)
                edge_relations[edge].append(rel)

        # Create igraph graph
        g = ig.Graph(n=len(entities), edges=edges, directed=False)

        # Run Leiden
        partition = leidenalg.find_partition(
            g,
            leidenalg.ModularityVertexPartition,
            resolution_parameter=self.resolution,
        )

        # Build communities from partition
        communities: List[Community] = []
        for comm_idx, member_indices in enumerate(partition):
            comm_entities = [entities[i] for i in member_indices]
            # Collect relations within this community
            member_set = set(member_indices)
            comm_relations = []
            for (src, tgt), rels in edge_relations.items():
                if src in member_set and tgt in member_set:
                    comm_relations.extend(rels)

            communities.append(
                Community(
                    id=f"community-{comm_idx}",
                    entities=comm_entities,
                    relations=comm_relations,
                    level=0,
                )
            )

        return communities

    def _detect_connected_components(
        self,
        entities: List[Entity],
        relations: List[Relation],
    ) -> List[Community]:
        """Fallback: group entities by connected components using union-find."""
        name_to_entity: Dict[str, Entity] = {}
        for entity in entities:
            name_to_entity[entity.name.lower()] = entity

        # Union-Find
        parent: Dict[str, str] = {e.name.lower(): e.name.lower() for e in entities}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for rel in relations:
            src = rel.source.lower()
            tgt = rel.target.lower()
            if src in parent and tgt in parent:
                union(src, tgt)

        # Group by root
        groups: Dict[str, List[str]] = defaultdict(list)
        for name in parent:
            groups[find(name)].append(name)

        # Build communities
        communities: List[Community] = []
        for comm_idx, (_, members) in enumerate(groups.items()):
            comm_entities = [name_to_entity[m] for m in members if m in name_to_entity]
            member_set = set(members)
            comm_relations = [
                r
                for r in relations
                if r.source.lower() in member_set and r.target.lower() in member_set
            ]
            communities.append(
                Community(
                    id=f"community-{comm_idx}",
                    entities=comm_entities,
                    relations=comm_relations,
                    level=0,
                )
            )

        return communities

    @staticmethod
    def _parse_extraction(raw_text: str) -> Dict[str, Any]:
        """Parse LLM extraction output as JSON, with fallback handling."""
        # Try to extract JSON from the response
        # Look for JSON block in markdown code fences
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_text, re.DOTALL)
        if json_match:
            raw_text = json_match.group(1)

        # Try direct parse
        try:
            return json.loads(raw_text.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in text
        brace_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse extraction output as JSON")
        return {"entities": [], "relations": []}
