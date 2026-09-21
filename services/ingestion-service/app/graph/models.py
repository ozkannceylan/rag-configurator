"""Data models for GraphRAG community detection and summarization."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Entity:
    """An entity extracted from document chunks."""

    name: str
    type: str
    description: str = ""
    chunk_ids: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "chunk_ids": self.chunk_ids,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            type=data["type"],
            description=data.get("description", ""),
            chunk_ids=data.get("chunk_ids", []),
            properties=data.get("properties", {}),
        )


@dataclass
class Relation:
    """A relationship between two entities."""

    source: str
    target: str
    type: str
    description: str = ""
    chunk_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "description": self.description,
            "chunk_ids": self.chunk_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Relation":
        """Create from dictionary."""
        return cls(
            source=data["source"],
            target=data["target"],
            type=data["type"],
            description=data.get("description", ""),
            chunk_ids=data.get("chunk_ids", []),
        )


@dataclass
class Community:
    """A group of related entities detected via community detection."""

    id: str
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    level: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "level": self.level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Community":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            entities=[Entity.from_dict(e) for e in data.get("entities", [])],
            relations=[Relation.from_dict(r) for r in data.get("relations", [])],
            level=data.get("level", 0),
        )


@dataclass
class CommunitySummary:
    """LLM-generated summary for a detected community."""

    community_id: str
    config_id: str
    summary: str
    entities: list[str] = field(default_factory=list)
    level: int = 0
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "community_id": self.community_id,
            "config_id": self.config_id,
            "summary": self.summary,
            "entities": self.entities,
            "level": self.level,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommunitySummary":
        """Create from dictionary."""
        return cls(
            community_id=data["community_id"],
            config_id=data["config_id"],
            summary=data["summary"],
            entities=data.get("entities", []),
            level=data.get("level", 0),
            created_at=data.get("created_at"),
        )
