"""LLM-based entity and relationship extraction."""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Configuration for entity extraction."""

    # LLM settings
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2"
    llm_base_url: str = "http://localhost:11434"
    openai_api_key: Optional[str] = None

    # Extraction settings
    entity_types: List[str] = field(default_factory=list)
    relation_types: List[str] = field(default_factory=list)
    auto_extract: bool = True  # Let LLM determine types if lists are empty

    # Processing
    max_entities_per_chunk: int = 50
    min_confidence: float = 0.5
    temperature: float = 0.1

    # Timeout
    timeout_seconds: float = 60.0


@dataclass
class ExtractedEntity:
    """An extracted entity from text."""

    name: str
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_text: str = ""
    start_char: int = 0
    end_char: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "properties": self.properties,
            "confidence": self.confidence,
            "source_text": self.source_text,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }


@dataclass
class ExtractedRelation:
    """An extracted relationship between entities."""

    source_entity: str
    target_entity: str
    relation_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relation_type": self.relation_type,
            "properties": self.properties,
            "confidence": self.confidence,
            "source_text": self.source_text,
        }


@dataclass
class ExtractionResult:
    """Result of entity extraction."""

    entities: List[ExtractedEntity] = field(default_factory=list)
    relations: List[ExtractedRelation] = field(default_factory=list)
    raw_response: str = ""
    tokens_used: int = 0


class EntityExtractor:
    """
    Extract entities and relationships from text using LLM.

    Supports:
    - Schema-constrained extraction with predefined types
    - Auto-extract mode where LLM determines types
    - Multiple LLM providers (Ollama, OpenAI)
    """

    EXTRACTION_PROMPT_TEMPLATE = """Extract entities and relationships from the following text.

{schema_instructions}

Output your response as valid JSON with this exact structure:
{{
    "entities": [
        {{
            "name": "entity name",
            "type": "entity type",
            "properties": {{}},
            "confidence": 0.0-1.0
        }}
    ],
    "relations": [
        {{
            "source": "source entity name",
            "target": "target entity name",
            "type": "relationship type",
            "properties": {{}},
            "confidence": 0.0-1.0
        }}
    ]
}}

Text to analyze:
---
{text}
---

JSON Response:"""

    SCHEMA_CONSTRAINED_INSTRUCTIONS = """Entity types to extract: {entity_types}
Relationship types to extract: {relation_types}

Only extract entities and relationships of the specified types."""

    AUTO_EXTRACT_INSTRUCTIONS = """Identify all significant entities (people, organizations, locations, concepts, events, products, etc.) and their relationships.
Use descriptive type names in lowercase with underscores (e.g., "person", "organization", "works_for", "located_in")."""

    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize entity extractor.

        Args:
            config: Extraction configuration
        """
        self.config = config or ExtractionConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds)
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_prompt(self, text: str) -> str:
        """Build extraction prompt."""
        if self.config.auto_extract or (
            not self.config.entity_types and not self.config.relation_types
        ):
            schema_instructions = self.AUTO_EXTRACT_INSTRUCTIONS
        else:
            schema_instructions = self.SCHEMA_CONSTRAINED_INSTRUCTIONS.format(
                entity_types=", ".join(self.config.entity_types) or "any",
                relation_types=", ".join(self.config.relation_types) or "any",
            )

        return self.EXTRACTION_PROMPT_TEMPLATE.format(
            schema_instructions=schema_instructions,
            text=text,
        )

    async def _call_ollama(self, prompt: str) -> Tuple[str, int]:
        """Call Ollama API for completion."""
        client = await self._get_client()

        url = f"{self.config.llm_base_url}/api/generate"
        payload = {
            "model": self.config.llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
            },
        }

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            return data.get("response", ""), data.get("eval_count", 0)
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise

    async def _call_openai(self, prompt: str) -> Tuple[str, int]:
        """Call OpenAI API for completion."""
        client = await self._get_client()

        if not self.config.openai_api_key:
            raise ValueError("OpenAI API key required for OpenAI provider")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.llm_model,
            "messages": [
                {"role": "system", "content": "You are an entity extraction assistant. Always respond with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.config.temperature,
        }

        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)

            return content, tokens
        except httpx.HTTPError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def _call_llm(self, prompt: str) -> Tuple[str, int]:
        """Call the configured LLM provider."""
        if self.config.llm_provider == "ollama":
            return await self._call_ollama(prompt)
        elif self.config.llm_provider == "openai":
            return await self._call_openai(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")

    def _parse_response(self, response: str) -> Tuple[List[ExtractedEntity], List[ExtractedRelation]]:
        """Parse LLM response into entities and relations."""
        entities: List[ExtractedEntity] = []
        relations: List[ExtractedRelation] = []

        # Try to extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            logger.warning("No JSON found in LLM response")
            return entities, relations

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return entities, relations

        # Parse entities
        for entity_data in data.get("entities", []):
            try:
                confidence = float(entity_data.get("confidence", 1.0))
                if confidence < self.config.min_confidence:
                    continue

                entity = ExtractedEntity(
                    name=str(entity_data.get("name", "")),
                    entity_type=str(entity_data.get("type", "unknown")),
                    properties=entity_data.get("properties", {}),
                    confidence=confidence,
                )

                if entity.name:
                    entities.append(entity)
            except (KeyError, TypeError, ValueError) as e:
                logger.debug(f"Skipping malformed entity: {e}")
                continue

        # Parse relations
        for rel_data in data.get("relations", []):
            try:
                confidence = float(rel_data.get("confidence", 1.0))
                if confidence < self.config.min_confidence:
                    continue

                relation = ExtractedRelation(
                    source_entity=str(rel_data.get("source", "")),
                    target_entity=str(rel_data.get("target", "")),
                    relation_type=str(rel_data.get("type", "related_to")),
                    properties=rel_data.get("properties", {}),
                    confidence=confidence,
                )

                if relation.source_entity and relation.target_entity:
                    relations.append(relation)
            except (KeyError, TypeError, ValueError) as e:
                logger.debug(f"Skipping malformed relation: {e}")
                continue

        # Limit entities per chunk
        if len(entities) > self.config.max_entities_per_chunk:
            entities = sorted(entities, key=lambda e: e.confidence, reverse=True)
            entities = entities[: self.config.max_entities_per_chunk]

        return entities, relations

    async def extract(self, text: str) -> ExtractionResult:
        """
        Extract entities and relationships from text.

        Args:
            text: Text to extract from

        Returns:
            ExtractionResult with entities and relations
        """
        if not text or not text.strip():
            return ExtractionResult()

        prompt = self._build_prompt(text)

        try:
            response, tokens = await self._call_llm(prompt)
            entities, relations = self._parse_response(response)

            return ExtractionResult(
                entities=entities,
                relations=relations,
                raw_response=response,
                tokens_used=tokens,
            )
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return ExtractionResult()

    async def extract_batch(
        self, texts: List[str], chunk_ids: Optional[List[str]] = None
    ) -> List[ExtractionResult]:
        """
        Extract entities from multiple texts.

        Args:
            texts: List of texts to extract from
            chunk_ids: Optional chunk IDs for tracking

        Returns:
            List of extraction results
        """
        results = []
        for i, text in enumerate(texts):
            result = await self.extract(text)

            # Add chunk reference if provided
            if chunk_ids and i < len(chunk_ids):
                for entity in result.entities:
                    entity.properties["source_chunk_id"] = chunk_ids[i]
                for relation in result.relations:
                    relation.properties["source_chunk_id"] = chunk_ids[i]

            results.append(result)

        return results
