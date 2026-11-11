"""Policy RAG API endpoints for document ingestion, semantic search, and grounded Q&A."""

from datetime import date
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.policy_rag import (
    PolicyAskRequest,
    PolicyAskResponse,
    PolicyDocumentDetailResponse,
    PolicyIngestRequest,
    PolicyIngestResponse,
    PolicySearchRequest,
    PolicySearchResponse,
)
from app.services.policy_rag.document_extractor import (
    DocumentNotFoundError,
    DocumentSizeLimitExceededError,
    EmptyDocumentError,
    PathTraversalError,
    UnsupportedFileTypeError,
)
from app.services.policy_rag.policy_rag_service import (
    PolicyIngestionError,
    PolicyNotFoundError,
    PolicyRAGService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/policies", tags=["Policy RAG"])


def get_policy_rag_service(db: Session = Depends(get_db)) -> PolicyRAGService:
    """Dependency provider for PolicyRAGService instance."""
    return PolicyRAGService(session=db)


@router.post(
    "/ingest",
    response_model=PolicyIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a policy document",
    description="Validate, extract, chunk, embed, and store a policy document atomically.",
)
def ingest_policy_document(
    request: PolicyIngestRequest,
    service: PolicyRAGService = Depends(get_policy_rag_service),
) -> PolicyIngestResponse:
    """Ingest a policy document into the vector store."""
    try:
        return service.ingest_document(request)
    except (DocumentNotFoundError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (PathTraversalError, UnsupportedFileTypeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (DocumentSizeLimitExceededError, EmptyDocumentError, ValueError, PolicyIngestionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error ingesting policy '%s': %s", request.title, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during policy ingestion.",
        ) from exc


@router.post(
    "/search",
    response_model=PolicySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search active policy chunks",
    description="Retrieve ranked policy chunks matching a query, filtered by as-of date and document metadata. Does not require LLM.",
)
def search_policies(
    request: PolicySearchRequest,
    service: PolicyRAGService = Depends(get_policy_rag_service),
) -> PolicySearchResponse:
    """Perform compliance-filtered semantic similarity search."""
    try:
        results = service.search_policies(
            query=request.query,
            as_of_date=request.as_of_date,
            document_type=request.document_type,
            document_id=request.document_id,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )
        return PolicySearchResponse(
            query=request.query,
            as_of_date=request.as_of_date,
            results=results,
            total_results=len(results),
        )
    except Exception as exc:
        logger.exception("Unexpected error during policy search for '%s': %s", request.query, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during policy search.",
        ) from exc


@router.post(
    "/ask",
    response_model=PolicyAskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a policy compliance question",
    description="Generate a grounded compliance answer supported by citations. Supports graceful degradation if LLM is offline.",
)
def ask_policy_question(
    request: PolicyAskRequest,
    service: PolicyRAGService = Depends(get_policy_rag_service),
) -> PolicyAskResponse:
    """Evaluate a policy question and generate a grounded, cited answer."""
    try:
        return service.ask_question(
            query=request.query,
            as_of_date=request.as_of_date,
            document_type=request.document_type,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )
    except Exception as exc:
        logger.exception("Unexpected error answering policy question '%s': %s", request.query, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred answering the policy question.",
        ) from exc


@router.get(
    "/{document_id}",
    response_model=PolicyDocumentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get policy document metadata and chunk summaries",
    description="Retrieve document metadata and chunk summaries without exposing internal embeddings or sensitive filesystem paths.",
)
def get_policy_document_details(
    document_id: str,
    service: PolicyRAGService = Depends(get_policy_rag_service),
) -> PolicyDocumentDetailResponse:
    """Retrieve policy document metadata and safe chunk previews."""
    try:
        return service.get_document_details(document_id=document_id)
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error retrieving policy document '%s': %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred retrieving the policy document.",
        ) from exc
