from fastapi import APIRouter, Depends, HTTPException

from app.schemas.rag import (
    RagQueryRequest,
    RagQueryResponse,
    RagSyncResponse,
)
from app.services.rag_service import RagService

router = APIRouter()


def get_rag_service() -> RagService:
    return RagService()


@router.post("/query", response_model=RagQueryResponse)
def query_knowledge_base(
    data: RagQueryRequest,
    service: RagService = Depends(get_rag_service),
):
    try:
        return service.query(data.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Raised by rag.embeddings.get_embedding_model() when
        # sentence-transformers couldn't be imported on this machine (see
        # that module's docstring) — a 503, not a crash, matches how
        # /api/predictions already reports an unavailable detector.
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/sync", response_model=RagSyncResponse)
def sync_knowledge_base(
    service: RagService = Depends(get_rag_service),
):
    try:
        return service.sync()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
