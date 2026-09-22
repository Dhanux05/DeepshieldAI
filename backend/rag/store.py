"""
ChromaDB access for the RAG knowledge base.

A single persistent collection (`deepshield_knowledge`) holds every chunk
from every file in `backend/knowledge-sources/`. Cosine similarity
(`hnsw:space: cosine`) is used instead of Chroma's default L2 distance
because MiniLM's embeddings are trained and evaluated for cosine similarity —
using L2 against them would rank passages by a metric the model was never
optimised for.
"""

import threading
from pathlib import Path
from typing import Any

import chromadb

COLLECTION_NAME = "deepshield_knowledge"

# backend/storage/chroma — sibling to backend/uploads/, both are runtime
# state that lives outside the repo (see .gitignore's "backend/storage/**").
PERSIST_DIR = Path(__file__).resolve().parent.parent / "storage" / "chroma"

_client: Any = None
_lock = threading.Lock()


def get_client() -> Any:
    """Thread-safe singleton PersistentClient, mirroring embeddings.get_embedding_model."""
    global _client

    if _client is None:
        with _lock:
            if _client is None:
                PERSIST_DIR.mkdir(parents=True, exist_ok=True)
                _client = chromadb.PersistentClient(path=str(PERSIST_DIR))

    return _client


def get_collection() -> Any:
    """
    Return the knowledge-base collection, creating it on first use.

    get_or_create_collection is idempotent — safe to call on every request
    instead of caching the Collection object, since Chroma's own client
    already caches the underlying index.
    """
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
