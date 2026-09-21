"""Community summarization using LLM for GraphRAG."""

import logging
from collections.abc import Callable
from typing import Any

from app.graph.models import Community, CommunitySummary

logger = logging.getLogger(__name__)


SUMMARIZE_PROMPT = """You are summarizing a community of related entities found in a knowledge graph.

Community entities:
{entities}

Relationships between entities:
{relations}

Write a 2-3 sentence summary that captures the key theme and relationships in this community. Be factual and concise.

Summary:"""


class CommunitySummarizer:
    """Generate LLM summaries for detected communities."""

    async def summarize_communities(
        self,
        communities: list[Community],
        llm_generate: Callable[..., Any],
        config_id: str,
        db: Any | None = None,
    ) -> list[CommunitySummary]:
        """
        Generate summaries for each community using an LLM.

        Args:
            communities: Communities to summarize.
            llm_generate: Async callable(prompt: str) -> str that calls the LLM.
            config_id: Pipeline configuration ID.
            db: Optional MongoDB database for persisting summaries.

        Returns:
            List of community summaries.
        """
        summaries: list[CommunitySummary] = []

        for community in communities:
            if not community.entities:
                continue

            try:
                summary_text = await self._summarize_single(community, llm_generate)
                entity_names = [e.name for e in community.entities]

                cs = CommunitySummary(
                    community_id=community.id,
                    config_id=config_id,
                    summary=summary_text,
                    entities=entity_names,
                    level=community.level,
                )
                summaries.append(cs)

            except Exception as e:
                logger.warning("Failed to summarize community %s: %s", community.id, e)

        # Persist to MongoDB if database is provided
        if db is not None and summaries:
            await self._store_summaries(db, summaries)

        return summaries

    async def _summarize_single(
        self,
        community: Community,
        llm_generate: Callable[..., Any],
    ) -> str:
        """Generate summary for a single community."""
        # Format entities
        entity_lines = []
        for e in community.entities:
            desc = f" - {e.description}" if e.description else ""
            entity_lines.append(f"- {e.name} ({e.type}){desc}")
        entities_text = "\n".join(entity_lines) if entity_lines else "No entities."

        # Format relations
        relation_lines = []
        for r in community.relations:
            desc = f" ({r.description})" if r.description else ""
            relation_lines.append(f"- {r.source} --[{r.type}]--> {r.target}{desc}")
        relations_text = (
            "\n".join(relation_lines) if relation_lines else "No relationships."
        )

        prompt = SUMMARIZE_PROMPT.replace("{entities}", entities_text).replace(
            "{relations}", relations_text
        )

        summary = await llm_generate(prompt)
        return summary.strip()

    @staticmethod
    async def _store_summaries(
        db: Any,
        summaries: list[CommunitySummary],
    ) -> None:
        """Persist community summaries to MongoDB."""
        collection = db["community_summaries"]
        docs = [s.to_dict() for s in summaries]
        if docs:
            await collection.insert_many(docs)
            logger.info("Stored %d community summaries", len(docs))
