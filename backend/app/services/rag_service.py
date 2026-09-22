"""
Service layer for the RAG knowledge base.

Thin by design: `rag.retriever` and `rag.ingest` already contain the real
logic (embedding, ChromaDB access, chunking). This class exists only so the
API route layer depends on `app.services.*` the same way every other route
in this codebase does (see bot_analysis_service.py, knowledge_base_service.py)
instead of importing the `rag` package directly from the route module.
"""

from rag.ingest import sync_knowledge_base
from rag.retriever import query_knowledge_base


class RagService:
    def query(self, question: str) -> dict:
        question = question.strip()
        if not question:
            raise ValueError("Question must not be empty.")

        results = query_knowledge_base(question)
        return {"question": question, "results": results}

    def sync(self) -> dict:
        return sync_knowledge_base()
