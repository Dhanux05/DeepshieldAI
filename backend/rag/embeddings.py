"""
Sentence-embedding model access for the RAG knowledge base.

The model (`all-MiniLM-L6-v2`, ~80MB) is loaded once per process and reused
for every chunk and every query — this is the same "load heavy things
exactly once" convention as `app.ml.registry`, applied here to a model that
lives outside that registry because it embeds text for retrieval, not
predictions for a detector.

`sentence-transformers` (and its scikit-learn dependency) is imported
defensively here. On some machines a security policy — Windows Smart App
Control, or an IT-managed Application Control / WDAC policy on a corporate
laptop — blocks one of scikit-learn's compiled extension modules
(`sklearn.metrics._pairwise_distances_reduction`) from loading, which
otherwise raises an ImportError the moment this module is imported. Because
`app.main` imports the whole `rag` package at module level (see its own
comment on why: `/api/rag/query` should be ready the instant the API starts
serving), an ImportError here would previously take down authentication,
document upload, and every ML detector along with it — none of which have
anything to do with RAG. Deferring the failure to first *use* (inside
`get_embedding_model`, as a `RuntimeError`) instead lets the rest of the API
boot normally and matches the same "unavailable, not fatal" convention
`app.ml.registry` already uses for a detector whose weight files are
missing: `/api/rag/*` reports itself unavailable via a 503 (see
`app/api/routes/rag.py`) instead of crashing the whole process.
"""

from __future__ import annotations

import threading

try:
    from sentence_transformers import SentenceTransformer

    _IMPORT_ERROR: Exception | None = None
except ImportError as exc:  # pragma: no cover - platform-dependent
    SentenceTransformer = None
    _IMPORT_ERROR = exc

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None
_lock = threading.Lock()


def get_embedding_model() -> SentenceTransformer:
    """
    Thread-safe singleton accessor.

    Double-checked locking: the fast path (model already loaded) never pays
    the lock, and two requests racing at startup can't load the model twice.

    Raises RuntimeError (not ImportError) if sentence-transformers could not
    be imported on this machine — see the module docstring above for why
    that distinction matters and the common Windows cause.
    """
    global _model

    if _IMPORT_ERROR is not None:
        raise RuntimeError(
            "RAG embedding backend unavailable: sentence-transformers could "
            "not be imported on this machine. On Windows this is commonly a "
            "security policy (Smart App Control, or an IT-managed "
            "Application Control / WDAC policy on a managed device) blocking "
            "one of scikit-learn's compiled extensions from loading. "
            f"Original import error: {_IMPORT_ERROR!r}"
        ) from _IMPORT_ERROR

    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of strings into MiniLM's 384-dimensional vector space.

    Used both when indexing chunks (many texts, one call) and when embedding
    a single incoming question (a one-element list) — batching through the
    same function keeps the two code paths identical.
    """
    if not texts:
        return []

    model = get_embedding_model()
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return vectors.tolist()
