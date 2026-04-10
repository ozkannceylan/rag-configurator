"""API endpoints for RAG evaluation."""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.core.auth import get_authenticated_user_id
from app.db.mongodb import mongodb
from app.db.repositories.evaluation_repo import EvaluationRepository
from app.evaluation.models import EvaluationRun
from app.evaluation.ragas_eval import AVAILABLE_METRICS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class EvaluateRequest(BaseModel):
    """Request body for running an evaluation."""

    config_id: str = Field(..., description="RAG pipeline configuration ID")
    query: str = Field(..., description="The user query")
    answer: Optional[str] = Field(
        None, description="The generated answer (will be generated if omitted)"
    )
    contexts: Optional[List[str]] = Field(
        None, description="Retrieved context chunks (will be retrieved if omitted)"
    )
    ground_truth: Optional[str] = Field(None, description="Expected correct answer")
    metrics: Optional[List[str]] = Field(
        None,
        description="Metrics to compute. Defaults to all RAGAS metrics.",
    )
    evaluator_type: str = Field(
        default="ragas",
        description="Evaluator to use: 'ragas' or 'judge'",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/evaluate")
async def evaluate(request: Request, body: EvaluateRequest):
    """Run evaluation on a query/answer pair.

    If ``answer`` or ``contexts`` are not provided, this endpoint will
    use the configured RAG pipeline to generate them first.
    """
    user_id = get_authenticated_user_id(request)
    db = mongodb.get_database()

    # Resolve answer / contexts from the pipeline if not provided
    answer = body.answer or ""
    contexts = body.contexts or []

    if not body.answer or not body.contexts:
        try:
            generated = await _generate_answer_and_contexts(
                db, body.config_id, body.query, user_id
            )
            if not body.answer:
                answer = generated["answer"]
            if not body.contexts:
                contexts = generated["contexts"]
        except Exception as exc:
            logger.warning("Failed to generate answer/contexts for evaluation: %s", exc)
            if not body.answer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not generate answer: {exc}. Provide answer and contexts explicitly.",
                )

    # Build evaluator
    metrics = body.metrics or list(AVAILABLE_METRICS)
    evaluator = _build_evaluator(
        evaluator_type=body.evaluator_type,
        metrics=metrics,
    )

    # Run evaluation
    try:
        result = await evaluator.evaluate(
            query=body.query,
            answer=answer,
            contexts=contexts,
            ground_truth=body.ground_truth,
        )
    except Exception as exc:
        logger.exception("Evaluation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {exc}",
        )

    # Persist
    run = EvaluationRun(
        id=str(uuid.uuid4()),
        config_id=body.config_id,
        user_id=user_id,
        query=body.query,
        answer=answer,
        contexts=contexts,
        ground_truth=body.ground_truth,
        results=result,
    )
    repo = EvaluationRepository(db)
    await repo.create_evaluation(run)

    return {"success": True, "data": result.model_dump()}


@router.get("/{config_id}")
async def get_evaluation_history(
    request: Request,
    config_id: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
):
    """Get evaluation history for a configuration."""
    user_id = get_authenticated_user_id(request)
    db = mongodb.get_database()

    repo = EvaluationRepository(db)
    runs = await repo.get_evaluations_by_config(config_id, skip=skip, limit=limit)
    total = await repo.count_by_config(config_id)

    return {
        "success": True,
        "data": [run.model_dump() for run in runs],
        "meta": {"total": total, "skip": skip, "limit": limit},
    }


@router.get("/{config_id}/summary")
async def get_evaluation_summary(request: Request, config_id: str):
    """Get aggregated evaluation metrics for a configuration."""
    user_id = get_authenticated_user_id(request)
    db = mongodb.get_database()

    repo = EvaluationRepository(db)
    summary = await repo.get_evaluation_summary(config_id)

    return {"success": True, "data": summary.model_dump()}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_evaluator(evaluator_type: str, metrics: List[str]):
    """Instantiate the requested evaluator backed by the default LLM."""
    from app.core.settings import settings
    from app.llm.base import LLMConfig
    from app.llm.factory import LLMProvider, get_llm

    provider_str = settings.default_llm_provider
    try:
        provider = LLMProvider(provider_str.lower())
    except ValueError:
        provider = LLMProvider.OPENAI

    config = LLMConfig(
        model=settings.default_llm_model,
        temperature=0.0,
        max_tokens=1024,
        api_key=settings.openai_api_key if provider == LLMProvider.OPENAI else settings.anthropic_api_key,
        base_url=settings.ollama_base_url if provider == LLMProvider.OLLAMA else None,
    )
    llm = get_llm(provider=provider, config=config)

    if evaluator_type == "judge":
        from app.evaluation.judge import JudgeEvaluator

        return JudgeEvaluator(llm=llm)
    else:
        from app.evaluation.ragas_eval import RagasEvaluator

        return RagasEvaluator(llm=llm, metrics=metrics)


async def _generate_answer_and_contexts(db, config_id: str, query: str, user_id: str):
    """Use the RAG pipeline to generate an answer and retrieve contexts."""
    from app.core.auth import require_config_access
    from app.api.v1.stream import build_pipeline_config
    from app.llm.factory import LLMProvider, get_llm
    from app.llm.base import LLMConfig
    from app.retrieval.factory import get_retriever_from_config
    from app.prompts.manager import PromptManager
    from app.api.v1.query import get_agent

    config_doc = await require_config_access(db, config_id, user_id)
    pipeline_config = build_pipeline_config(config_doc)

    # Retriever
    retriever = get_retriever_from_config(db=db, pipeline_config=pipeline_config)

    # LLM
    llm_cfg = pipeline_config.get("llm", {})
    provider_str = llm_cfg.get("provider", "openai")
    try:
        provider = LLMProvider(provider_str.lower())
    except ValueError:
        provider = LLMProvider.OPENAI

    config = LLMConfig(
        model=llm_cfg.get("model", "gpt-4o-mini"),
        temperature=llm_cfg.get("temperature", 0.7),
        max_tokens=llm_cfg.get("max_tokens", 2048),
        api_key=llm_cfg.get("api_key"),
        base_url=llm_cfg.get("base_url"),
    )
    llm = get_llm(provider=provider, config=config)

    prompt_manager = PromptManager()
    agent_config = pipeline_config.get("agent", {})
    agent_type = agent_config.get("type", "naive")
    agent = get_agent(
        agent_type=agent_type,
        retriever=retriever,
        llm=llm,
        prompt_manager=prompt_manager,
        config=agent_config,
    )

    response = await agent.run(query=query, config_id=config_id)
    contexts = [chunk.content for chunk in response.sources]
    return {"answer": response.answer, "contexts": contexts}
