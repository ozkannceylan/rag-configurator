"""Main Celery task for document ingestion pipeline."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from celery import states
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.celery_app import celery_app
from app.core.settings import settings
from app.tasks.utils import (
    ProgressTracker,
    compute_file_hash,
    get_file_metadata,
    get_folder_path,
    get_processor_type,
    is_supported_file,
    scan_directory,
)

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Orchestrates the full ingestion pipeline.

    Pipeline steps:
    1. Load config from MongoDB
    2. Update status → "processing"
    3. Scan data source for files
    4. For each file:
       a. Get processor by file type
       b. Process → extract text
       c. Chunk text
       d. Generate embeddings
       e. Store in vector store
       f. If graph enabled: extract entities
       g. Update progress
    5. If graph enabled: build graph edges
    6. Update status → "completed"
    7. Store final stats
    """

    def __init__(
        self,
        config_id: str,
        user_id: str,
        ingestion_id: str,
        celery_task: Any = None,
    ):
        """
        Initialize ingestion pipeline.

        Args:
            config_id: RAG pipeline configuration ID
            user_id: User who initiated the ingestion
            ingestion_id: Ingestion job ID
            celery_task: Celery task instance for progress updates
        """
        self.config_id = config_id
        self.user_id = user_id
        self.ingestion_id = ingestion_id
        self.celery_task = celery_task

        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.config: Optional[Dict[str, Any]] = None
        self.tracker: Optional[ProgressTracker] = None

        # Components (lazy loaded)
        self._processor = None
        self._chunker = None
        self._embedder = None
        self._vector_store = None
        self._graph_builder = None

    async def initialize(self) -> None:
        """Initialize database connection and load config."""
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_database]

        # Load configuration
        self.config = await self._load_config()
        if not self.config:
            raise ValueError(f"Configuration not found: {self.config_id}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._embedder:
            await self._embedder.close()
        if self._graph_builder:
            await self._graph_builder.close()
        if self.client:
            self.client.close()

    async def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration from MongoDB."""
        configs = self.db["configs"]
        config = await configs.find_one({"_id": self.config_id})
        if not config:
            # Try with string ID
            config = await configs.find_one({"id": self.config_id})
        return config

    async def _update_ingestion_status(
        self,
        status: str,
        error: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update ingestion job status in MongoDB."""
        from app.storage.vector_store import VectorStore
        from app.storage.models import IngestionStatus

        store = VectorStore(self.db)

        status_enum = IngestionStatus(status)
        kwargs: Dict[str, Any] = {}

        if error:
            kwargs["error_message"] = error

        await store.update_ingestion_status(
            self.ingestion_id,
            status_enum,
            **kwargs,
        )

        if stats:
            await store.update_ingestion_progress(
                self.ingestion_id,
                processed_files=stats.get("processed_files"),
                failed_files=stats.get("failed_files"),
                total_chunks=stats.get("total_chunks"),
            )

    async def _get_processor(self, file_path: str):
        """Get the appropriate processor for a file."""
        from app.processors.factory import get_processor
        from app.processors.base import DocumentProcessingConfig

        processor_type = get_processor_type(file_path)
        if not processor_type:
            return None

        # Get processing config from pipeline config
        processing_config = self.config.get("processing", {})

        config = DocumentProcessingConfig(
            extract_tables=processing_config.get("extract_tables", True),
            extract_images=processing_config.get("extract_images", False),
            ocr_enabled=processing_config.get("ocr_enabled", True),
        )

        return get_processor(file_path, config)

    async def _get_chunker(self):
        """Get the text chunker based on config."""
        from app.chunkers.factory import get_chunker, ChunkingStrategy
        from app.chunkers.base import ChunkingConfig

        chunking_config = self.config.get("chunking", {})

        strategy_name = chunking_config.get("strategy", "recursive")
        try:
            strategy = ChunkingStrategy(strategy_name)
        except ValueError:
            strategy = ChunkingStrategy.RECURSIVE

        config = ChunkingConfig(
            chunk_size=chunking_config.get("chunk_size", settings.chunk_size),
            chunk_overlap=chunking_config.get("chunk_overlap", settings.chunk_overlap),
            separators=chunking_config.get("separators"),
        )

        return get_chunker(strategy, config)

    async def _get_embedder(self):
        """Get the embedding provider based on config."""
        if self._embedder:
            return self._embedder

        from app.embedders.factory import get_embedder, EmbeddingProvider

        embedding_config = self.config.get("embedding", {})

        provider_name = embedding_config.get("provider", settings.embedding_provider)
        try:
            provider = EmbeddingProvider(provider_name)
        except ValueError:
            provider = EmbeddingProvider.OPENAI

        model = embedding_config.get("model", settings.embedding_model)

        # Get API keys from config or settings
        api_key = embedding_config.get("api_key") or settings.openai_api_key

        self._embedder = get_embedder(
            provider=provider,
            model=model,
            api_key=api_key,
        )
        return self._embedder

    async def _get_vector_store(self):
        """Get the vector store."""
        if self._vector_store:
            return self._vector_store

        from app.storage.vector_store import VectorStore

        self._vector_store = VectorStore(self.db)
        return self._vector_store

    async def _get_graph_builder(self):
        """Get the graph builder if graph extraction is enabled."""
        if self._graph_builder:
            return self._graph_builder

        graph_config = self.config.get("graph", {})
        if not graph_config.get("enabled", False):
            return None

        from app.graph.builder import GraphBuilder, GraphBuildConfig
        from app.graph.extractor import ExtractionConfig
        from app.storage.graph_store import GraphStore

        extraction_config = ExtractionConfig(
            llm_provider=graph_config.get("llm_provider", "ollama"),
            llm_model=graph_config.get("llm_model", "llama3.2"),
            entity_types=graph_config.get("entity_types", []),
            relation_types=graph_config.get("relation_types", []),
            auto_extract=graph_config.get("auto_extract", True),
        )

        build_config = GraphBuildConfig(
            extraction_config=extraction_config,
            embed_entities=graph_config.get("embed_entities", False),
        )

        graph_store = GraphStore(self.db)
        self._graph_builder = GraphBuilder(graph_store, build_config)
        return self._graph_builder

    async def _scan_data_source(self) -> List[str]:
        """Scan data source for files to process."""
        data_source = self.config.get("data_source", {})
        source_type = data_source.get("type", "local")

        if source_type == "local":
            path = data_source.get("path", "")
            recursive = data_source.get("recursive", True)
            include_extensions = data_source.get("include_extensions")
            exclude_patterns = data_source.get("exclude_patterns", [])

            files = scan_directory(
                path,
                recursive=recursive,
                include_extensions=include_extensions,
                exclude_patterns=exclude_patterns,
            )
            return files

        elif source_type == "s3":
            # TODO: Implement S3 scanning
            logger.warning("S3 data source not yet implemented")
            return []

        elif source_type == "url":
            # URL sources are passed directly
            urls = data_source.get("urls", [])
            return urls

        else:
            logger.warning(f"Unknown data source type: {source_type}")
            return []

    async def _process_file(
        self,
        file_path: str,
        base_path: str,
    ) -> Dict[str, Any]:
        """
        Process a single file through the pipeline.

        Args:
            file_path: Path to the file
            base_path: Base path for relative path calculation

        Returns:
            Processing result dict
        """
        result = {
            "file_path": file_path,
            "success": False,
            "chunks_created": 0,
            "embeddings_created": 0,
            "error": None,
        }

        try:
            # Check if file is supported
            if not is_supported_file(file_path):
                result["error"] = "Unsupported file type"
                return result

            # Get file metadata
            file_meta = get_file_metadata(file_path)
            content_hash = compute_file_hash(file_path)

            # Check for duplicate content
            vector_store = await self._get_vector_store()
            if await vector_store.document_exists(self.config_id, content_hash):
                logger.info(f"Skipping duplicate file: {file_path}")
                result["success"] = True
                result["skipped"] = True
                return result

            # Get processor and process file
            processor = await self._get_processor(file_path)
            if not processor:
                result["error"] = "No processor available for file type"
                return result

            self.tracker.set_step(f"Processing: {file_meta['file_name']}")

            # Process the document
            processed = await processor.process(Path(file_path))

            if not processed.content:
                result["error"] = "No content extracted"
                return result

            # Store document record
            from app.storage.models import DocumentRecord

            doc_record = DocumentRecord(
                config_id=self.config_id,
                ingestion_id=self.ingestion_id,
                user_id=self.user_id,
                file_path=file_path,
                file_name=file_meta["file_name"],
                file_type=file_meta["file_type"],
                file_size_bytes=file_meta.get("file_size_bytes", 0),
                content_hash=content_hash,
                processor_name=processor.__class__.__name__,
                metadata={
                    "pages": processed.pages,
                    "sections": len(processed.sections),
                    "tables": len(processed.tables),
                },
            )

            document_id = await vector_store.store_document(doc_record)

            # Chunk the content
            self.tracker.set_step(f"Chunking: {file_meta['file_name']}")

            chunker = await self._get_chunker()
            from app.chunkers.base import ChunkingConfig

            chunk_config = self.config.get("chunking", {})
            chunking_config = ChunkingConfig(
                chunk_size=chunk_config.get("chunk_size", settings.chunk_size),
                chunk_overlap=chunk_config.get("chunk_overlap", settings.chunk_overlap),
            )

            chunks = chunker.chunk(
                processed.content,
                chunking_config,
                metadata={
                    "document_id": document_id,
                    "file_name": file_meta["file_name"],
                    "file_path": file_path,
                },
            )

            if not chunks:
                result["error"] = "No chunks created"
                return result

            # Generate embeddings
            self.tracker.set_step(f"Embedding: {file_meta['file_name']}")

            embedder = await self._get_embedder()
            chunk_texts = [c.content for c in chunks]

            embedding_result = await embedder.embed(chunk_texts)

            # Create chunk records with embeddings
            from app.storage.models import ChunkRecord

            folder_path = get_folder_path(file_path, base_path)

            chunk_records = []
            for i, chunk in enumerate(chunks):
                embedding = (
                    embedding_result.embeddings[i]
                    if i < len(embedding_result.embeddings)
                    else []
                )

                chunk_record = ChunkRecord(
                    config_id=self.config_id,
                    document_id=document_id,
                    ingestion_id=self.ingestion_id,
                    user_id=self.user_id,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    embedding=embedding,
                    embedding_model=embedding_result.model,
                    embedding_dimensions=embedding_result.dimensions,
                    chunk_index=chunk.chunk_index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    folder_path=folder_path,
                    metadata=chunk.metadata,
                )
                chunk_records.append(chunk_record)

            # Store chunks
            chunk_ids = await vector_store.store_chunks(chunk_records)

            result["chunks_created"] = len(chunk_ids)
            result["embeddings_created"] = len(embedding_result.embeddings)

            # Graph extraction if enabled
            graph_builder = await self._get_graph_builder()
            if graph_builder:
                self.tracker.set_step(f"Graph extraction: {file_meta['file_name']}")

                graph_chunks = [
                    {"content": c.content, "chunk_id": chunk_ids[i]}
                    for i, c in enumerate(chunks)
                    if i < len(chunk_ids)
                ]

                graph_result = await graph_builder.build_from_chunks(
                    graph_chunks,
                    self.config_id,
                    document_id,
                )

                self.tracker.add_graph_stats(
                    graph_result.nodes_created,
                    graph_result.edges_created,
                )

            # Update document with chunk count
            await self.db["documents"].update_one(
                {"_id": document_id},
                {"$set": {"chunk_count": len(chunk_ids)}},
            )

            result["success"] = True

        except Exception as e:
            logger.exception(f"Error processing file {file_path}: {e}")
            result["error"] = str(e)

        return result

    async def run(self) -> Dict[str, Any]:
        """
        Run the complete ingestion pipeline.

        Returns:
            Dict with final results and statistics
        """
        try:
            await self.initialize()

            # Update status to processing
            await self._update_ingestion_status("running")

            # Scan for files
            data_source = self.config.get("data_source", {})
            base_path = data_source.get("path", "")

            files = await self._scan_data_source()

            if not files:
                logger.warning(f"No files found for config {self.config_id}")
                await self._update_ingestion_status("completed")
                return {
                    "config_id": self.config_id,
                    "status": "completed",
                    "message": "No files found",
                    "stats": {"total_files": 0},
                }

            # Initialize progress tracker
            self.tracker = ProgressTracker(
                total_files=len(files),
                ingestion_id=self.ingestion_id,
                celery_task=self.celery_task,
            )

            self.tracker.set_step("Scanning files")

            # Update total files in ingestion record
            vector_store = await self._get_vector_store()
            await self.db["ingestions"].update_one(
                {"_id": self.ingestion_id},
                {"$set": {"total_files": len(files)}},
            )

            # Process each file
            for file_path in files:
                try:
                    result = await self._process_file(file_path, base_path)

                    if result["success"]:
                        self.tracker.file_processed(
                            file_path,
                            chunks_created=result.get("chunks_created", 0),
                            embeddings_created=result.get("embeddings_created", 0),
                        )
                    else:
                        self.tracker.file_failed(
                            file_path,
                            result.get("error", "Unknown error"),
                        )

                    # Update progress in database
                    await vector_store.increment_ingestion_progress(
                        self.ingestion_id,
                        processed_files=1 if result["success"] else 0,
                        failed_files=0 if result["success"] else 1,
                        total_chunks=result.get("chunks_created", 0),
                    )

                except Exception as e:
                    logger.exception(f"Error processing {file_path}: {e}")
                    self.tracker.file_failed(file_path, str(e))

            # Get final statistics
            final_stats = self.tracker.get_final_stats()

            # Update ingestion status to completed
            await self._update_ingestion_status("completed", stats=final_stats)

            # Store errors if any
            if self.tracker.errors:
                await self.db["ingestions"].update_one(
                    {"_id": self.ingestion_id},
                    {"$set": {"errors": self.tracker.errors}},
                )

            # Update config statistics
            await self._update_config_stats(final_stats)

            return {
                "config_id": self.config_id,
                "ingestion_id": self.ingestion_id,
                "status": "completed",
                "stats": final_stats,
            }

        except Exception as e:
            logger.exception(f"Ingestion pipeline failed: {e}")

            # Update status to failed
            await self._update_ingestion_status("failed", error=str(e))

            return {
                "config_id": self.config_id,
                "ingestion_id": self.ingestion_id,
                "status": "failed",
                "error": str(e),
            }

        finally:
            await self.cleanup()

    async def _update_config_stats(self, stats: Dict[str, Any]) -> None:
        """Update configuration with final statistics."""
        try:
            await self.db["configs"].update_one(
                {"_id": self.config_id},
                {
                    "$set": {
                        "last_ingestion_at": datetime.utcnow(),
                        "stats.total_documents": stats.get("processed_files", 0),
                        "stats.total_chunks": stats.get("total_chunks", 0),
                        "stats.graph_nodes": stats.get("graph_nodes", 0),
                        "stats.graph_edges": stats.get("graph_edges", 0),
                    }
                },
            )
        except Exception as e:
            logger.error(f"Failed to update config stats: {e}")


def run_async(coro):
    """Run an async coroutine in a synchronous context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="app.tasks.ingestion_task.run_ingestion",
    max_retries=3,
    default_retry_delay=60,
)
def run_ingestion(
    self,
    config_id: str,
    user_id: str,
    ingestion_id: str,
) -> Dict[str, Any]:
    """
    Main Celery task for running the ingestion pipeline.

    Args:
        config_id: RAG pipeline configuration ID
        user_id: User who initiated the ingestion
        ingestion_id: Ingestion job ID

    Returns:
        Dict with ingestion results and statistics
    """
    logger.info(
        f"Starting ingestion task: config={config_id}, user={user_id}, ingestion={ingestion_id}"
    )

    try:
        pipeline = IngestionPipeline(
            config_id=config_id,
            user_id=user_id,
            ingestion_id=ingestion_id,
            celery_task=self,
        )

        result = run_async(pipeline.run())

        logger.info(f"Ingestion completed: {result}")
        return result

    except Exception as e:
        logger.exception(f"Ingestion task failed: {e}")

        # Update state to failed
        self.update_state(
            state=states.FAILURE,
            meta={
                "config_id": config_id,
                "ingestion_id": ingestion_id,
                "error": str(e),
            },
        )

        raise


@celery_app.task(
    bind=True,
    name="app.tasks.ingestion_task.cancel_ingestion",
)
def cancel_ingestion(self, ingestion_id: str) -> Dict[str, Any]:
    """
    Cancel a running ingestion job.

    Args:
        ingestion_id: Ingestion job ID to cancel

    Returns:
        Dict with cancellation status
    """
    logger.info(f"Cancelling ingestion: {ingestion_id}")

    async def do_cancel():
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_database]

        try:
            # Get ingestion record
            ingestion = await db["ingestions"].find_one({"_id": ingestion_id})
            if not ingestion:
                return {"success": False, "error": "Ingestion not found"}

            # Check if already completed
            if ingestion.get("status") in ("completed", "failed", "cancelled"):
                return {
                    "success": False,
                    "error": f"Ingestion already {ingestion['status']}",
                }

            # Update status
            await db["ingestions"].update_one(
                {"_id": ingestion_id},
                {
                    "$set": {
                        "status": "cancelled",
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            # Revoke Celery task if exists
            task_id = ingestion.get("celery_task_id")
            if task_id:
                celery_app.control.revoke(task_id, terminate=True)

            return {"success": True, "message": "Ingestion cancelled"}

        finally:
            client.close()

    return run_async(do_cancel())


@celery_app.task(
    bind=True,
    name="app.tasks.ingestion_task.get_ingestion_status",
)
def get_ingestion_status(self, ingestion_id: str) -> Dict[str, Any]:
    """
    Get the current status of an ingestion job.

    Args:
        ingestion_id: Ingestion job ID

    Returns:
        Dict with ingestion status and progress
    """
    async def do_get_status():
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_database]

        try:
            ingestion = await db["ingestions"].find_one({"_id": ingestion_id})
            if not ingestion:
                return {"found": False, "error": "Ingestion not found"}

            return {
                "found": True,
                "ingestion_id": str(ingestion["_id"]),
                "config_id": ingestion.get("config_id"),
                "status": ingestion.get("status"),
                "progress": (
                    (ingestion.get("processed_files", 0) / ingestion.get("total_files", 1)) * 100
                    if ingestion.get("total_files", 0) > 0
                    else 0
                ),
                "total_files": ingestion.get("total_files", 0),
                "processed_files": ingestion.get("processed_files", 0),
                "failed_files": ingestion.get("failed_files", 0),
                "total_chunks": ingestion.get("total_chunks", 0),
                "started_at": ingestion.get("started_at"),
                "completed_at": ingestion.get("completed_at"),
                "errors": ingestion.get("errors", []),
            }

        finally:
            client.close()

    return run_async(do_get_status())
